# 为什么有这个文件：核对大纲与生成入口的草案形状。
# 它解决什么问题：避免把尚未实现的 operationId、202 任务或幂等头写成已经接到运行时。

import json
import re
from pathlib import Path

from test_error_idempotency import DRAFT_STATUS, SPEC, implemented_contract

CAMEL = re.compile(r"^[a-z][A-Za-z0-9]*$")
OPERATIONS = {
    "/api/v1/projects/{project_id}/outline/plan": ("get", "getOutlinePlan"),
    "/api/v1/projects/{project_id}/outline/plan/confirm": ("post", "confirmOutlinePlan"),
    "/api/v1/projects/{project_id}/generation/start": ("post", "startGeneration"),
    "/api/v1/jobs/{id}": ("get", "getJob"),
}
WRITES = {"confirmOutlinePlan", "startGeneration"}
CITED_CODES = {
    "VALIDATION_ERROR",
    "PLAN_STALE",
    "PLAN_NOT_CONFIRMED",
    "VOLUME_OWNER_REQUIRED",
    "IDEMPOTENCY_KEY_REQUIRED",
    "IDEMPOTENCY_CONFLICT",
    "IF_MATCH_REQUIRED",
    "VERSION_CONFLICT",
    "PARSE_NOT_CONFIRMED",
    "INPUT_FINGERPRINT_STALE",
    "MODEL_UNAVAILABLE",
}
EVENT_FIELDS = {
    "type",
    "provider",
    "model",
    "is_real_model",
    "is_local",
    "duration_ms",
    "error_code",
}


def load_spec():
    return json.loads(SPEC.read_text(encoding="utf-8"))


def operation(spec, path):
    method, name = OPERATIONS[path]
    item = spec["paths"][path]
    assert item["x-contract-status"] == DRAFT_STATUS
    assert item["x-implemented"] is False
    assert item["x-aligned-with"] == "BE-M0-T06"
    body = item[method]
    assert body["operationId"] == name
    assert CAMEL.match(name)
    return body


def test_draft_operation_ids_are_camel_case_and_absent_from_the_running_contract():
    spec = load_spec()
    found = {operation(spec, path)["operationId"] for path in OPERATIONS}
    assert found == {"getOutlinePlan", "confirmOutlinePlan", "startGeneration", "getJob"}
    implemented = implemented_contract(spec)
    assert spec["x-contract-drafts"]["status"] == DRAFT_STATUS
    assert spec["x-contract-drafts"]["implemented"] is False
    assert "x-contract-drafts" not in implemented
    for path in OPERATIONS:
        assert path not in implemented["paths"]
    for name in ("OutlinePlan", "JobStatus", "JobEvent", "ScoringRow"):
        assert name not in implemented["components"]["schemas"]


def test_errors_reuse_the_frozen_body_and_do_not_add_codes():
    spec = load_spec()
    enum = spec["components"]["schemas"]["V1Error"]["properties"]["code"]["enum"]
    assert set(CITED_CODES) <= set(enum)
    required = spec["components"]["schemas"]["V1Error"]["required"]
    assert required == ["code", "message", "details", "traceId"]
    for path in OPERATIONS:
        body = operation(spec, path)
        for response in body["responses"].values():
            content = response.get("content", {}).get("application/json", {})
            ref = content.get("schema", {}).get("$ref", "")
            if ref.endswith("/V1Error"):
                assert response["headers"]["X-Request-ID"]["$ref"].endswith("/X-Request-ID")
            assert not ref.endswith("/ErrorResponse")


def test_writes_declare_idempotency_and_start_generation_is_a_job():
    spec = load_spec()
    for path, (method, name) in OPERATIONS.items():
        body = operation(spec, path)
        names = [parameter["name"] for parameter in body.get("parameters", [])]
        if name in WRITES:
            assert "Idempotency-Key" in names
            assert "428" in body["description"] and "IDEMPOTENCY_KEY_REQUIRED" in body["description"]
            assert "409" in body["description"] and "IDEMPOTENCY_CONFLICT" in body["description"]
            assert "Idempotent-Replayed" in next(iter(body["responses"].values()))["headers"]
        else:
            assert "Idempotency-Key" not in names

    start = operation(spec, "/api/v1/projects/{project_id}/generation/start")
    assert "200" not in start["responses"]
    accepted = start["responses"]["202"]
    assert accepted["headers"]["Location"]["required"] is True
    assert "/api/v1/jobs/{id}" in accepted["headers"]["Location"]["description"]
    assert accepted["content"]["application/json"]["schema"]["$ref"].endswith("/JobStatus")

    job = operation(spec, "/api/v1/jobs/{id}")
    assert job["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith("/JobStatus")
    status = spec["components"]["schemas"]["JobStatus"]
    assert status["x-aligned-with"] == "BE-M0-T06"
    assert {"$ref": "#/components/schemas/Job"} in status["allOf"]
    reused = spec["components"]["schemas"]["Job"]
    assert reused["properties"]["recoverable"]["const"] is False
    assert "x-contract-status" not in reused
    event = spec["components"]["schemas"]["JobEvent"]["properties"]
    assert set(event) == EVENT_FIELDS
    assert event["type"]["const"] == "job.model_call"
    assert event["error_code"]["anyOf"] == [{"type": "string"}, {"type": "null"}]


def test_outline_confirm_stays_per_chapter_and_whole_chapter():
    spec = load_spec()
    confirm = operation(spec, "/api/v1/projects/{project_id}/outline/plan/confirm")
    assert "VALIDATION_ERROR" in confirm["description"]
    assert "PLAN_STALE" in confirm["description"]
    request = spec["components"]["schemas"]["ConfirmOutlinePlanRequest"]
    assert "company_id" not in request["properties"]
    item = spec["components"]["schemas"]["SnippetPlanItem"]["properties"]["source_scope"]
    assert item["const"] == "whole_chapter"
    row = spec["components"]["schemas"]["ScoringRow"]["properties"]
    assert "point_headings" in row and "asterisk" in row and "disqualified" in row
