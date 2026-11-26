"""项目只读成员逐个调用 /api/v1 项目写接口，后端都要拒绝（ISSUE-053 / TV-M0-T20）。"""

import re
import uuid

import pytest
from fastapi.testclient import TestClient

from icg_demo.main import create_app

PROJECT = "alpha-project"
CHAPTER = "alpha-tech"
# 只读计算、不落库的 POST
READ_ONLY_POSTS = {
    "/api/v1/projects/{project_id}/compliance-rules/evaluate",
    "/api/v1/projects/{project_id}/chapters/{chapter_id}/variables",
    "/api/v1/projects/{project_id}/matrix/match",
}
# 资源不存在时先报 404，各自另有只读用例
NEEDS_RESOURCE = {
    "/api/v1/projects/{project_id}/technical-sections/rewrite": "test_technical_assistant.py::test_readonly_member_cannot_rewrite",
    "/api/v1/projects/{project_id}/chapters/{chapter_id}/paragraph-locks/{paragraph_key}": "test_readonly_member_cannot_unlock_own_lock",
}
BODIES = {
    "/api/v1/projects/{project_id}/files": {"filename": "a.txt", "content_base64": "eA=="},
    "/api/v1/projects/{project_id}/status": {"action": "submit", "reason": "合成"},
    "/api/v1/projects/{project_id}/parse/conflicts/{conflict_id}/decision": {"action": "not_conflict", "reason": "合成理由"},
    "/api/v1/projects/{project_id}/volumes/{volume_id}/cross-review/confirm": {"decision": "approved", "note": "合成"},
    "/api/v1/projects/{project_id}/chapters/{chapter_id}/selection-rewrites":
        {"base_revision": 1, "count": 3, "selected_text": "x", "instruction": "x", "start": 0, "end": 1},
    "/api/v1/projects/{project_id}/chapters/{chapter_id}/selection-rewrites/stream":
        {"base_revision": 1, "count": 3, "selected_text": "x", "instruction": "x", "start": 0, "end": 1},
}


@pytest.fixture
def client():
    with TestClient(create_app()) as actual:
        yield actual


def login(client, account):
    response = client.post("/api/v1/auth/login", json={"username": account, "password": "X_2026"})
    assert response.status_code == 200, response.text
    return {"Authorization": "Bearer " + response.json()["access_token"]}


def _fill(spec, schema, depth=0):
    while "$ref" in schema:
        schema = spec["components"]["schemas"][schema["$ref"].split("/")[-1]]
    if "anyOf" in schema:
        return _fill(spec, next((x for x in schema["anyOf"] if x.get("type") != "null"), schema["anyOf"][0]), depth)
    if "allOf" in schema:
        return _fill(spec, schema["allOf"][0], depth)
    if "enum" in schema:
        return schema["enum"][0]
    if schema.get("default") is not None:
        return schema["default"]
    kind = schema.get("type")
    if kind == "object" or "properties" in schema:
        if depth >= 4:
            return {}
        return {key: _fill(spec, value, depth + 1) for key, value in (schema.get("properties") or {}).items()
                if depth == 0 or key in schema.get("required", [])}
    if kind == "array":
        return [_fill(spec, schema["items"], depth + 1)] if schema.get("minItems") and "items" in schema else []
    if kind == "integer":
        return max(1, schema.get("minimum", 1))
    if kind == "number":
        return 1
    if kind == "boolean":
        return True
    return "技术" * max(1, schema.get("minLength") or 1)


def test_readonly_member_is_rejected_on_every_project_write(client):
    headers = login(client, "alpha-viewer")
    spec = client.app.openapi()
    checked, leaked = 0, []
    for path, operations in spec["paths"].items():
        if not path.startswith("/api/v1") or "{project_id}" not in path:
            continue
        if path in READ_ONLY_POSTS or path in NEEDS_RESOURCE:
            continue
        for method in sorted({name.upper() for name in operations} & {"POST", "PUT", "PATCH", "DELETE"}):
            url = path.replace("{project_id}", PROJECT).replace("{chapter_id}", CHAPTER).replace("{volume_id}", "technical")
            url = re.sub(r"\{[^}]+\}", "x", url)
            request = {"headers": {**headers, "If-Match": "1", "Idempotency-Key": str(uuid.uuid4())}}
            if path.endswith("/files/raw"):
                request.update(content=b"x", params={"filename": "a.txt"})
            else:
                body = (operations[method.lower()].get("requestBody") or {}).get("content", {}).get("application/json")
                request["json"] = BODIES.get(path) or (_fill(spec, body["schema"]) if body else {})
            response = client.request(method, url, **request)
            checked += 1
            if response.status_code != 403:
                leaked.append(f"{method} {path} -> {response.status_code} {response.text[:120]}")
    assert checked >= 60
    assert leaked == []


def test_readonly_member_cannot_unlock_own_lock(client):
    editor = login(client, "alpha-editor")
    data = client.get(f"/api/chapters/{CHAPTER}", headers=editor).json()
    lease = client.post(f"/api/chapters/{CHAPTER}/lock", headers=editor, json={"takeover_reason": None}).json()["lease_token"]
    body = "# 运维服务\n\n本项目提供七乘二十四小时驻场运维。"
    client.post(f"/api/chapters/{CHAPTER}/versions", headers=editor,
                json={"lease_token": lease, "base_revision": data["revision"], "content": body, "idempotency_key": "ro-lock-1"})
    data = client.get(f"/api/chapters/{CHAPTER}", headers=editor).json()
    key = next(p["key"] for p in data["paragraphs"] if data["content"].splitlines()[p["line_start"]].startswith("本项目"))
    path = f"/api/v1/projects/{PROJECT}/chapters/{CHAPTER}/paragraph-locks"
    locked = client.post(path, headers=editor, json={"paragraph_key": key, "base_revision": data["revision"], "reason": "客户确认原文"})
    assert locked.status_code == 200, locked.text
    client.app.state.service.repository.transaction(
        lambda st: st.project_teams[PROJECT]["members"]["alpha-editor"].__setitem__("project_role", "readonly"))
    released = client.delete(f"{path}/{key}", headers=editor)
    assert released.status_code == 403, released.text
