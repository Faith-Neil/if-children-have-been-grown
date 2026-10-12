# 为什么有这个文件：核对大纲与生成入口的草案形状。
# 它解决什么问题：避免把尚未实现的 operationId、202 任务或幂等头写成已经接到运行时。

import json
import re

from test_error_idempotency import (
    DEPRECATED_OPERATIONS, DEPRECATION_NOTE, DRAFT_STATUS, SPEC, implemented_contract)

CAMEL = re.compile(r"^[a-z][A-Za-z0-9]*$")
OPERATIONS = {
    "/api/v1/projects/{project_id}/outline/plan": ("get", "getOutlinePlan"),
    "/api/v1/projects/{project_id}/outline/plan/confirm": ("post", "confirmOutlinePlan"),
    "/api/v1/projects/{project_id}/generation/start": ("post", "startGeneration"),
    "/api/v1/jobs/{job_id}": ("get", "getJob"),
    "/api/v1/jobs/{job_id}/events": ("get", "streamJobEvents"),
    "/api/v1/jobs/{job_id}/cancel": ("post", "cancelJob"),
}
WRITES = {"confirmOutlinePlan", "startGeneration", "cancelJob"}
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
    "MODEL_UNAVAILABLE",
    "NOT_FOUND",
}
EVENT_FIELDS = {
    "seq",
    "id",
    "occurred_at",
    "type",
    "provider",
    "model",
    "is_real_model",
    "is_local",
    "duration_ms",
    "error_code",
    "payload",
}
EVENT_TYPES = [
    "job.model_call",
    "job.status_changed",
    "job.progress",
    "job.completed",
    "job.failed",
    "job.cancelled",
]
GET_EXCLUDED = {"413", "423", "428", "502"}


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
    assert found == {
        "getOutlinePlan", "confirmOutlinePlan", "startGeneration",
        "getJob", "streamJobEvents", "cancelJob",
    }
    implemented = implemented_contract(spec)
    assert spec["x-contract-drafts"]["status"] == DRAFT_STATUS
    assert spec["x-contract-drafts"]["implemented"] is False
    assert "x-contract-drafts" not in implemented
    for path in OPERATIONS:
        assert path not in implemented["paths"]
    assert "/api/v1/jobs/{id}" not in spec["paths"]
    for name in ("OutlinePlan", "JobStatus", "JobEvent", "ScoringRow"):
        assert name not in implemented["components"]["schemas"]
    for path in DEPRECATED_OPERATIONS:
        assert path in implemented["paths"]
        assert "deprecated" not in implemented["paths"][path]["post"]


def test_errors_are_listed_per_operation_and_reuse_the_frozen_body():
    spec = load_spec()
    enum = spec["components"]["schemas"]["V1Error"]["properties"]["code"]["enum"]
    assert set(CITED_CODES) <= set(enum)
    assert spec["components"]["schemas"]["V1Error"]["required"] == ["code", "message", "details", "traceId"]
    for path in OPERATIONS:
        body = operation(spec, path)
        for response in body["responses"].values():
            content = response.get("content", {}).get("application/json", {})
            ref = content.get("schema", {}).get("$ref", "")
            if ref.endswith("/V1Error"):
                assert response["headers"]["X-Request-ID"]["$ref"].endswith("/X-Request-ID")
            assert not ref.endswith("/ErrorResponse")
        if OPERATIONS[path][0] == "get":
            assert GET_EXCLUDED.isdisjoint(body["responses"])
    assert "409" not in operation(spec, "/api/v1/jobs/{job_id}")["responses"]
    assert "409" not in operation(spec, "/api/v1/jobs/{job_id}/events")["responses"]
    start = operation(spec, "/api/v1/projects/{project_id}/generation/start")
    assert "502" in start["responses"]
    assert "503" in start["responses"]
    secret = start["responses"]["503"]["description"]
    assert "SECRET_KEY_UNAVAILABLE" in secret
    assert "不是瞬时故障" in secret and "不要自动重试" in secret and "MODEL_UNAVAILABLE" in secret
    assert "ISSUE-024" in start["description"]
    assert "SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL" in start["description"]
    assert "SECRET_KEY_UNAVAILABLE" not in enum
    assert "SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL" not in enum
    assert "SECRET_KEY_UNAVAILABLE" not in spec["components"]["x-error-status"]["statuses"]["503"]
    assert "SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL" not in spec["components"]["x-error-status"]["statuses"]["403"]
    assert "423" in start["responses"]
    assert "423" in operation(spec, "/api/v1/projects/{project_id}/outline/plan/confirm")["responses"]
    assert "502" not in operation(spec, "/api/v1/projects/{project_id}/outline/plan/confirm")["responses"]
    assert "502" not in operation(spec, "/api/v1/jobs/{job_id}/cancel")["responses"]
    assert "403" not in operation(spec, "/api/v1/jobs/{job_id}")["responses"]
    assert "403" not in operation(spec, "/api/v1/jobs/{job_id}/events")["responses"]


def test_job_status_is_separate_and_events_can_be_streamed():
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
    assert "/api/v1/jobs/{job_id}" in accepted["headers"]["Location"]["description"]
    assert "同一个 job id" in start["description"] and "202" in start["description"]
    assert "已确认大纲计划的 revision" in start["description"]
    assert accepted["content"]["application/json"]["schema"]["$ref"].endswith("/JobStatus")

    job = operation(spec, "/api/v1/jobs/{job_id}")
    assert job["parameters"][0]["name"] == "job_id"
    assert "404 NOT_FOUND" in job["description"] and "本公司" in job["description"]
    assert job["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith("/JobStatus")
    status = spec["components"]["schemas"]["JobStatus"]
    assert "allOf" not in status
    assert status["properties"]["status"]["enum"] == ["queued", "running", "completed", "failed", "cancelled"]
    assert status["x-aligned-with"] == "BE-M0-T06"
    reused = spec["components"]["schemas"]["Job"]
    assert reused["properties"]["recoverable"]["const"] is False
    assert "x-contract-status" not in reused

    event_schema = spec["components"]["schemas"]["JobEvent"]
    event = event_schema["properties"]
    assert set(event) == EVENT_FIELDS
    assert event["type"]["enum"] == EVENT_TYPES
    assert "BE-M0-T06" in event_schema["description"]
    assert "from" in event["payload"]["description"] and "progress" in event["payload"]["description"]
    assert event_schema["required"] == ["seq", "id", "occurred_at", "type"]
    assert "<job_id>:<seq>" in event["id"]["description"]
    assert event["error_code"]["anyOf"] == [{"type": "string"}, {"type": "null"}]
    assert status["properties"]["recoverable"]["type"] == "boolean"
    assert "recoverable" in status["required"]

    stream = operation(spec, "/api/v1/jobs/{job_id}/events")
    assert "Last-Event-ID" in [parameter["name"] for parameter in stream["parameters"]]
    assert "text/event-stream" in stream["responses"]["200"]["content"]
    cancel = operation(spec, "/api/v1/jobs/{job_id}/cancel")
    assert cancel["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith("/JobStatus")
    assert "Location" not in cancel["responses"]["200"]["headers"]


def test_outline_confirm_uses_plan_revision_and_old_posts_are_deprecated():
    spec = load_spec()
    outline = operation(spec, "/api/v1/projects/{project_id}/outline/plan")
    assert outline["responses"]["200"]["headers"]["ETag"]["required"] is True
    assert "没有 fingerprint 字段" in outline["description"]
    confirm = operation(spec, "/api/v1/projects/{project_id}/outline/plan/confirm")
    assert "If-Match" in confirm["description"] and "整份大纲计划的 revision" in confirm["description"]
    assert "VERSION_CONFLICT" in confirm["description"] and "PLAN_STALE" in confirm["description"]
    assert "expected_revision" in confirm["description"]
    assert "没有 fingerprint 字段" in confirm["description"]
    assert "LOCK_HELD" in confirm["description"] and "LOCK_LOST" in confirm["description"]
    started = operation(spec, "/api/v1/projects/{project_id}/generation/start")
    assert "快照" in started["description"] and "不要自动重试" in started["description"]
    request = spec["components"]["schemas"]["ConfirmOutlinePlanRequest"]
    assert "company_id" not in request["properties"]
    assert "fingerprint" not in spec["components"]["schemas"]["OutlinePlan"]["properties"]
    assert "fingerprint" not in request["properties"]
    item = spec["components"]["schemas"]["SnippetPlanItem"]["properties"]["source_scope"]
    assert item["const"] == "whole_chapter"
    row = spec["components"]["schemas"]["ScoringRow"]["properties"]
    assert "point_headings" in row and "asterisk" in row and "disqualified" in row
    for path in DEPRECATED_OPERATIONS:
        body = spec["paths"][path]["post"]
        assert body["deprecated"] is True
        assert body["description"] == DEPRECATION_NOTE
        assert body.get("x-contract-status") != DRAFT_STATUS
