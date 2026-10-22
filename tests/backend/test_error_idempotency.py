# 为什么有这个文件：证明已冻结的错误体、状态码和幂等规则与接口说明一致。
# 它解决什么问题：避免同一错误码对应多个 HTTP 状态，或失败、过期、超额回执被当成成功重放。

import ast
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from icg_demo.domain import DemoState, DomainError
from icg_demo.errors import ERROR_STATUS, RETRY_GUIDANCE, status_for
from icg_demo.frozen_error_codes import FROZEN_NAMES
from icg_demo.idempotency import (
    IDEMPOTENCY_TTL_SECONDS, fingerprint, lookup, remember, validate_key)
from icg_demo.main import create_app
from test_library_basis import create_record, mutation_headers, read_library
from test_reference_flow import ProjectFlow, client, login

PACKAGE = Path(__file__).resolve().parents[2] / "backend" / "bid-core" / "icg_demo"
SPEC = Path(__file__).resolve().parents[2] / "spec" / "openapi" / "demo-v1.json"
FROZEN_STATUS = "frozen"
WRITES_WITHOUT_IDEMPOTENCY_KEY = "没有 Idempotency-Key 的写入不自动重试。"
DEPRECATION_NOTE = "已废弃。新旧入口并存。前端改用 getOutlinePlan、confirmOutlinePlan 与 startGeneration 之后，由后续 Issue 删除本操作。运行时尚未标出 deprecated。"
DEPRECATED_OPERATIONS = (
    "/api/v1/projects/{project_id}/plan",
    "/api/v1/projects/{project_id}/generate",
    "/api/v1/projects/{project_id}/chapters/{chapter_id}/plan/confirm",
)


def implemented_contract(document):
    """去掉契约已冻结但运行时尚未实现的路径和模型，剩下的应与运行中的接口一致。"""
    spec = json.loads(json.dumps(document))
    spec.pop("x-contract-drafts", None)
    for path, item in list(spec["paths"].items()):
        if isinstance(item, dict) and item.get("x-contract-status") == FROZEN_STATUS:
            del spec["paths"][path]
    for path in DEPRECATED_OPERATIONS:
        operation = spec["paths"][path]["post"]
        operation.pop("deprecated", None)
        if operation.get("description") == DEPRECATION_NOTE:
            operation.pop("description", None)
    schemas = spec["components"]["schemas"]
    for name, body in list(schemas.items()):
        if isinstance(body, dict) and body.get("x-contract-status") == FROZEN_STATUS:
            del schemas[name]
    for item in spec["paths"].values():
        if not isinstance(item, dict):
            continue
        for operation in item.values():
            if isinstance(operation, dict):
                operation.pop("x-issue-033", None)
    idempotency = spec.get("components", {}).get("x-idempotency")
    if isinstance(idempotency, dict) and isinstance(idempotency.get("retry"), str):
        idempotency["retry"] = idempotency["retry"].removesuffix(WRITES_WITHOUT_IDEMPOTENCY_KEY)
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
    assert set(ERROR_STATUS) == FROZEN_NAMES


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
    assert set(schema["components"]["schemas"]["V1Error"]["properties"]["code"]["enum"]) == FROZEN_NAMES
    stored = json.loads(SPEC.read_text(encoding="utf-8"))
    assert set(stored["components"]["schemas"]["V1Error"]["properties"]["code"]["enum"]) == FROZEN_NAMES
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
    raw = json.loads(SPEC.read_text(encoding="utf-8"))
    assert raw["components"]["x-idempotency"]["retry"] == RETRY_GUIDANCE + WRITES_WITHOUT_IDEMPOTENCY_KEY
    assert implemented_contract(raw) == schema


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
    assert set(legacy.json()) == {"code", "message", "details", "traceId"}
    assert legacy.json()["traceId"] == legacy.headers["X-Request-ID"]
    assert legacy.json()["code"] == "UNAUTHENTICATED"
    assert "error" not in legacy.json()
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


def test_uncapped_receipts_keep_more_than_2048():
    state = DemoState(cap_receipts=False)
    now = 1_700_000_000.0
    for index in range(2049):
        remember(state, "library:alpha", "alpha-editor", f"capkey{index:05d}", "f" * 64, {"n": index}, now)
    assert len(state.workflow_receipts) == 2049


def test_case_insensitive_api_prefix_returns_json_404(client):
    """QA 200a105 E2E-D5: /API, /Api/v1/... 等大小写变体必须返回 JSON 404，不返回页面壳。"""
    for route in ("/API", "/Api/v1/session", "/api/v1/nonexistent", "/API/projects"):
        response = client.get(route)
        assert response.status_code == 404, f"{route} did not return 404"
        assert response.headers["content-type"].startswith("application/json")
        body = response.json()
        assert set(body) == {"code", "message", "details", "traceId"}
        assert body["code"] == "NOT_FOUND"
        assert body["traceId"] == response.headers["X-Request-ID"]
        assert len(body["traceId"]) == 32
        assert "error" not in body


def test_legacy_endpoints_support_idempotency_key_replay(client):
    """验证旧 /api 端点挂载 Idempotency-Key 后同键同指纹重放与冲突保护。"""
    actor = login(client)

    # 1. POST /api/projects 幂等
    headers = {**actor, "Idempotency-Key": "proj-legacy-key-01"}
    p1 = client.post("/api/projects", headers=headers, json={"name": "旧接口幂等项目"})
    assert p1.status_code == 200, p1.text
    assert "Idempotent-Replayed" not in p1.headers
    # 同键同指纹重放
    p2 = client.post("/api/projects", headers=headers, json={"name": "旧接口幂等项目"})
    assert p2.status_code == 200
    assert p2.headers.get("Idempotent-Replayed") == "true"
    assert p1.json() == p2.json()
    # 同键不同指纹冲突
    p3 = client.post("/api/projects", headers=headers, json={"name": "冲突名称"})
    assert p3.status_code == 409
    assert p3.json()["code"] == "IDEMPOTENCY_CONFLICT"

    # 2. 章节锁与草稿旧端点幂等
    flow = ProjectFlow(client).ready()
    ch_id = flow.state()["chapters"][0]["id"]
    flow_headers = flow.headers

    # POST /api/chapters/{id}/lock
    h_lock = {**flow_headers, "Idempotency-Key": "lock-legacy-key-01"}
    l1 = client.post(f"/api/chapters/{ch_id}/lock", headers=h_lock, json={})
    assert l1.status_code == 200
    assert "Idempotent-Replayed" not in l1.headers
    assert "lease_token" in l1.json()
    assert "acquired_at" in l1.json()
    assert "heartbeat_at" in l1.json()
    l2 = client.post(f"/api/chapters/{ch_id}/lock", headers=h_lock, json={})
    assert l2.status_code == 200
    assert l2.headers.get("Idempotent-Replayed") == "true"
    assert l1.json() == l2.json()

    # POST /api/chapters/{id}/lock/renew
    token = l1.json()["lease_token"]
    h_renew = {**flow_headers, "Idempotency-Key": "renew-legacy-key-01"}
    rn1 = client.post(f"/api/chapters/{ch_id}/lock/renew", headers=h_renew, json={"lease_token": token})
    assert rn1.status_code == 200
    rn2 = client.post(f"/api/chapters/{ch_id}/lock/renew", headers=h_renew, json={"lease_token": token})
    assert rn2.status_code == 200
    assert rn2.headers.get("Idempotent-Replayed") == "true"
    assert rn1.json() == rn2.json()

    # PUT /api/chapters/{id}/draft
    ch = next(c for c in flow.state()["chapters"] if c["id"] == ch_id)
    fp = flow.state()["input_fingerprint"]
    h_draft = {**flow_headers, "Idempotency-Key": "draft-legacy-key-01"}
    d1 = client.put(f"/api/chapters/{ch_id}/draft", headers=h_draft,
                    json={"lease_token": token, "base_revision": ch["revision"], "sequence": 1,
                          "content": "旧草稿幂等内容", "input_fingerprint": fp})
    assert d1.status_code == 200
    d2 = client.put(f"/api/chapters/{ch_id}/draft", headers=h_draft,
                    json={"lease_token": token, "base_revision": ch["revision"], "sequence": 1,
                          "content": "旧草稿幂等内容", "input_fingerprint": fp})
    assert d2.status_code == 200
    assert d2.headers.get("Idempotent-Replayed") == "true"
    assert d1.json() == d2.json()

    # DELETE /api/chapters/{id}/draft
    h_disc = {**flow_headers, "Idempotency-Key": "disc-legacy-key-01"}
    dc1 = client.request("DELETE", f"/api/chapters/{ch_id}/draft", headers=h_disc, json={"sequence": 1})
    assert dc1.status_code == 200
    dc2 = client.request("DELETE", f"/api/chapters/{ch_id}/draft", headers=h_disc, json={"sequence": 1})
    assert dc2.status_code == 200
    assert dc2.headers.get("Idempotent-Replayed") == "true"
    assert dc1.json() == dc2.json()

    # POST /api/chapters/{id}/lock/release
    h_rel = {**flow_headers, "Idempotency-Key": "rel-legacy-key-01"}
    rl1 = client.post(f"/api/chapters/{ch_id}/lock/release", headers=h_rel, json={"lease_token": token})
    assert rl1.status_code == 200
    rl2 = client.post(f"/api/chapters/{ch_id}/lock/release", headers=h_rel, json={"lease_token": token})
    assert rl2.status_code == 200
    assert rl2.headers.get("Idempotent-Replayed") == "true"
    assert rl1.json() == rl2.json()


def test_chapter_lease_alignment_fields_and_persistence():
    """BE-M0-T17: 验证 chapter_lease 对齐字典 edit_lock 字段定义与持久化完整性。"""
    from icg_demo.domain import Chapter, DemoState, Lease
    lease = Lease(
        token="lease-test-token",
        user_id="user-01",
        session_token="session-test-token",
        expires_at=1700000120.0,
        acquired_at=1700000000.0,
        heartbeat_at=1700000010.0,
        lock_reason="编写技术章节",
        taken_over_from_user_id="user-00",
        takeover_reason="前任请假",
        released_at=None,
        release_reason=None,
        company_id="company-alpha",
        record_version=1,
    )
    assert lease.session_token == "session-test-token"
    assert lease.owner_id == "user-01"
    assert lease.user_id == "user-01"
    assert lease.acquired_at == 1700000000.0
    assert lease.heartbeat_at == 1700000010.0
    assert lease.lock_reason == "编写技术章节"
    assert lease.taken_over_from_user_id == "user-00"
    assert lease.takeover_reason == "前任请假"
    assert lease.company_id == "company-alpha"
    assert lease.record_version == 1

    state = DemoState()
    state.chapters["chap-1"] = Chapter(
        id="chap-1",
        project_id="proj-1",
        volume="default",
        title="第一章",
        content="",
        lock=lease,
    )
    from icg_demo.database import _lease_snapshot
    snapshot = _lease_snapshot(state)
    assert "chap-1" in snapshot
    entry = snapshot["chap-1"]
    assert entry[0] == "lease-test-token"
    assert entry[1] == "user-01"
    assert entry[4] == 1700000000.0
    assert entry[5] == 1700000010.0
    assert entry[6] == "编写技术章节"
    assert entry[7] == "user-00"
    assert entry[8] == "前任请假"
    assert entry[11] == "company-alpha"
    assert entry[12] == 1
