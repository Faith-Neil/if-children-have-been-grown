# 为什么有这个文件：证明已冻结的错误体、状态码和幂等规则与接口说明一致。
# 它解决什么问题：避免同一错误码对应多个 HTTP 状态，或失败、过期、超额回执被当成成功重放。

import ast
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from icg_demo.domain import DemoState, DomainError
from icg_demo.errors import ERROR_STATUS, RETRY_GUIDANCE, status_for
from icg_demo.idempotency import (
    IDEMPOTENCY_TTL_SECONDS, fingerprint, lookup, remember, validate_key)
from icg_demo.main import create_app
from test_library_basis import create_record, mutation_headers, read_library
from test_reference_flow import ProjectFlow, client, login

PACKAGE = Path(__file__).resolve().parents[2] / "backend" / "bid-core" / "icg_demo"
SPEC = Path(__file__).resolve().parents[2] / "spec" / "openapi" / "demo-v1.json"
DRAFT_STATUS = "draft, pending backend review"


def implemented_contract(document):
    """去掉尚未实现的草案路径和草案模型，剩下的应与运行中的接口一致。"""
    spec = json.loads(json.dumps(document))
    spec.pop("x-contract-drafts", None)
    for path, item in list(spec["paths"].items()):
        if isinstance(item, dict) and item.get("x-contract-status") == DRAFT_STATUS:
            del spec["paths"][path]
    schemas = spec["components"]["schemas"]
    for name, body in list(schemas.items()):
        if isinstance(body, dict) and body.get("x-contract-status") == DRAFT_STATUS:
            del schemas[name]
    return spec


def test_literal_domain_errors_use_the_single_frozen_status():
    mismatches = []
    for path in PACKAGE.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name) or node.func.id != "DomainError":
                continue
            if len(node.args) < 2 or not isinstance(node.args[1], ast.Constant) or not isinstance(node.args[1].value, str):
                continue
            code = node.args[1].value
            if not isinstance(node.args[0], ast.Constant) or not isinstance(node.args[0].value, int):
                mismatches.append(f"{path.name}:{node.lineno} {code} 缺少字面状态")
                continue
            status = node.args[0].value
            if code not in ERROR_STATUS or ERROR_STATUS[code] != status:
                mismatches.append(f"{path.name}:{node.lineno} {code} -> {status}")
    assert mismatches == []
    assert ERROR_STATUS["VOLUME_OWNER_REQUIRED"] == 403
    assert ERROR_STATUS["TWO_VOLUMES_REQUIRED"] == 422
    assert ERROR_STATUS["MODEL_UNAVAILABLE"] == 502
    assert len(ERROR_STATUS) == len(set(ERROR_STATUS))


def test_openapi_declares_v1_error_body_status_table_and_retry():
    schema = create_app().openapi()
    assert RETRY_GUIDANCE in schema["info"]["description"]
    table = schema["components"]["x-error-status"]["statuses"]
    assert table["403"] and "VOLUME_OWNER_REQUIRED" in table["403"]
    assert "VOLUME_OWNER_REQUIRED" not in table["409"]
    assert table["422"] and "TWO_VOLUMES_REQUIRED" in table["422"]
    assert "TWO_VOLUMES_REQUIRED" not in table["409"]
    assert table["502"] and "MODEL_UNAVAILABLE" in table["502"]
    assert schema["components"]["schemas"]["V1Error"]["properties"]["code"]["enum"] == sorted(ERROR_STATUS)
    idempotency = schema["components"]["x-idempotency"]
    assert idempotency["ttl_seconds"] == IDEMPOTENCY_TTL_SECONDS
    assert idempotency["max_receipts"] == 2048
    assert "失败不登记" in idempotency["failures"]
    for path, item in schema["paths"].items():
        if not path.startswith("/api/v1"):
            continue
        for operation in item.values():
            if not isinstance(operation, dict):
                continue
            for response in operation["responses"].values():
                content = response.get("content", {}).get("application/json", {})
                ref = content.get("schema", {}).get("$ref", "")
                assert not ref.endswith("/ErrorResponse")
                if ref.endswith("/V1Error"):
                    assert response["headers"]["X-Request-ID"]["$ref"].endswith("/X-Request-ID")
            if any(parameter.get("name") == "Idempotency-Key" for parameter in operation.get("parameters", [])):
                assert "Idempotent-Replayed" in next(iter(operation["responses"].values()))["headers"]
    assert implemented_contract(json.loads(SPEC.read_text(encoding="utf-8"))) == schema


def test_v1_model_unavailable_uses_unified_error_body():
    class Down:
        name = "down"
        is_real_model = False
        is_local = True

        def suggest(self, instruction, content):
            raise RuntimeError("synthetic model down")

    with TestClient(create_app(model_provider=Down())) as raw:
        flow = ProjectFlow(raw).ready()
        response = raw.post(
            flow.path + "/generate",
            headers={**flow.headers, "If-Match": str(flow.state()["revision"]), "Idempotency-Key": "model-down-01"},
            json={})
    assert response.status_code == 502, response.text
    body = response.json()
    assert set(body) == {"code", "message", "details", "traceId"}
    assert body["code"] == "MODEL_UNAVAILABLE"
    assert body["traceId"] == response.headers["X-Request-ID"]
    assert "error" not in body


def test_unknown_v1_route_returns_unified_404_with_trace_id(client):
    missing = client.get("/api/v1/does-not-exist")
    assert missing.status_code == 404
    assert missing.headers["content-type"].startswith("application/json")
    body = missing.json()
    assert set(body) == {"code", "message", "details", "traceId"}
    assert body["code"] == "NOT_FOUND"
    assert body["details"] == {}
    assert body["traceId"] == missing.headers["X-Request-ID"]
    assert len(body["traceId"]) == 32
    assert "error" not in body
    session = client.get("/api/v1/session")
    assert session.status_code == 401
    assert session.json()["code"] == "UNAUTHENTICATED"
    assert session.json()["traceId"] == session.headers["X-Request-ID"]
    for path in ("/api/v1/%2e%2e/%2e%2e/etc/passwd", "/workbench/%2e%2e/%2e%2e/etc/passwd"):
        escaped = client.get(path)
        assert escaped.status_code == 404
        assert escaped.headers["content-type"].startswith("application/json")
        assert "root:x:" not in escaped.text
    assert client.get("/api/v1/%2e%2e/%2e%2e/etc/passwd").json()["code"] == "NOT_FOUND"


def test_v1_error_body_matches_request_header_and_legacy_shape_stays(client):
    missing = client.get("/api/v1/session")
    assert missing.status_code == 401
    body = missing.json()
    assert set(body) == {"code", "message", "details", "traceId"}
    assert body["code"] == "UNAUTHENTICATED"
    assert body["details"] == {}
    assert body["traceId"] == missing.headers["X-Request-ID"]
    assert len(body["traceId"]) == 32
    legacy = client.get("/api/projects")
    assert set(legacy.json()) == {"error", "request_id"}
    assert legacy.json()["request_id"] == legacy.headers["X-Request-ID"]
    invalid = client.post("/api/v1/library", headers=login(client), json={"name": ""})
    assert invalid.status_code == 422
    assert invalid.json()["code"] == "VALIDATION_ERROR"
    assert "body.name" in invalid.json()["details"]["fields"]


def test_same_key_replays_success_and_changed_payload_conflicts_without_writing(client):
    actor = login(client)
    first, payload, headers = create_record(client, actor, "幂等重放合成资料")
    replay = client.post("/api/v1/library", headers=headers, json=payload)
    assert replay.status_code == 200, replay.text
    assert replay.json() == first
    assert replay.headers["Idempotent-Replayed"] == "true"
    assert "Idempotent-Replayed" not in client.post(
        "/api/v1/library", headers=mutation_headers(actor, read_library(client, actor)["revision"]),
        json={**payload, "name": "另一份合成资料"}).headers
    before = read_library(client, actor)
    conflict = client.post("/api/v1/library", headers=headers, json={**payload, "content": "同一标记不能换成另一段内容。"})
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "IDEMPOTENCY_CONFLICT"
    assert conflict.headers["X-Request-ID"] == conflict.json()["traceId"]
    assert "Idempotent-Replayed" not in conflict.headers
    assert read_library(client, actor) == before


def test_missing_or_invalid_key_is_428_and_failure_is_not_stored(client):
    actor = login(client)
    current = read_library(client, actor)
    missing = client.post("/api/v1/library", headers={**actor, "If-Match": str(current["revision"])},
                          json={"name": "缺少标记", "type": "qualification", "content": "合成内容。"})
    assert missing.status_code == 428
    assert missing.json()["code"] == "IDEMPOTENCY_KEY_REQUIRED"
    short = mutation_headers(actor, current["revision"], "short")
    assert client.post("/api/v1/library", headers=short,
                       json={"name": "过短标记", "type": "qualification", "content": "合成内容。"}).status_code == 428
    key = "retry-after-blank-content"
    failed = client.post("/api/v1/library", headers=mutation_headers(actor, current["revision"], key),
                         json={"name": "空白正文", "type": "qualification", "content": " "})
    assert failed.status_code == 422
    assert failed.json()["code"] == "EMPTY_LIBRARY_FIELD"
    recovered = client.post("/api/v1/library", headers=mutation_headers(actor, current["revision"], key),
                            json={"name": "空白正文", "type": "qualification", "content": "失败后用同一标记保存的合成内容。"})
    assert recovered.status_code == 200, recovered.text
    assert "Idempotent-Replayed" not in recovered.headers


def test_receipt_expires_after_24_hours_and_memory_is_bounded(monkeypatch):
    clock = {"now": 1_700_000_000.0}
    with TestClient(create_app(clock=lambda: clock["now"])) as client:
        actor = login(client)
        revision = read_library(client, actor)["revision"]
        key = "expires-after-one-day"
        payload = {"name": "24小时前的合成资料", "type": "qualification", "content": "首次内容。"}
        headers = mutation_headers(actor, revision, key)
        first = client.post("/api/v1/library", headers=headers, json=payload)
        assert first.status_code == 200, first.text
        bumped = client.post("/api/v1/library", headers=mutation_headers(actor, read_library(client, actor)["revision"]),
                             json={"name": "用来推进版本的另一份合成资料", "type": "qualification", "content": "另一内容。"})
        assert bumped.status_code == 200, bumped.text
        conflict = client.post("/api/v1/library", headers=mutation_headers(actor, read_library(client, actor)["revision"], key),
                               json=payload)
        assert conflict.status_code == 409
        assert conflict.json()["code"] == "IDEMPOTENCY_CONFLICT"
        clock["now"] += IDEMPOTENCY_TTL_SECONDS + 1
        renewed = client.post("/api/v1/library", headers=mutation_headers(actor, read_library(client, actor)["revision"], key),
                              json=payload)
        assert renewed.status_code == 200, renewed.text
        assert renewed.json()["item"]["id"] != first.json()["item"]["id"]
        assert "Idempotent-Replayed" not in renewed.headers

    import icg_demo.idempotency as idempotency
    monkeypatch.setattr(idempotency, "MAX_IDEMPOTENCY_RECEIPTS", 1)
    state = DemoState()
    now = 1_700_000_000.0
    remember(state, "project-a", "user-a", "key-old", "finger-old", {"revision": 1}, now)
    remember(state, "project-a", "user-a", "key-new", "finger-new", {"revision": 2}, now + 1)
    assert lookup(state, "project-a", "user-a", "key-old", "finger-old", now + 1) is None
    assert lookup(state, "project-a", "user-a", "key-new", "finger-new", now + 1) == {"revision": 2}
    with pytest.raises(DomainError) as conflict:
        lookup(state, "project-a", "user-a", "key-new", "other-finger", now + 1)
    assert conflict.value.status == 409 and conflict.value.code == "IDEMPOTENCY_CONFLICT"
    assert validate_key("550e8400-e29b-41d4-a716-446655440000")
    with pytest.raises(DomainError) as missing:
        validate_key("bad key")
    assert missing.value.status == status_for("IDEMPOTENCY_KEY_REQUIRED") == 428
    assert fingerprint("library.create", {"name": "甲"}, "1") != fingerprint("library.create", {"name": "乙"}, "1")
