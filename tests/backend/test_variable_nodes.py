# 为什么有这个文件：验证编辑台变量节点（APP-M2-T164）。
# 它解决什么问题：变量按当前已确认取值显示，敏感号码显示掩码；不存在、未确认、格式残缺的变量标失效并指明数据源；
# 提交与回退时后台拒绝新写入的失效变量，原正文已有、之后才失效的变量不挡提交；只读接口不改正文。

import pytest
from fastapi.testclient import TestClient

from icg_demo.main import create_app

CHAPTER = "alpha-tech"


@pytest.fixture
def client():
    with TestClient(create_app()) as actual:
        yield actual


def login(client, account="alpha-editor"):
    response = client.post("/api/v1/auth/login", json={"username": account, "password": "X_2026"})
    assert response.status_code == 200, response.text
    return {"Authorization": "Bearer " + response.json()["access_token"]}


def seed(client, editor):
    data = client.get(f"/api/chapters/{CHAPTER}", headers=editor).json()
    project_id = data["project_id"]
    from icg.domain.workflow_orchestrator import _blank_workflow

    def write(state):
        workflow = state.workflows.setdefault(project_id, _blank_workflow())
        workflow.setdefault("facts", {}).update({
            "f-term": {"id": "f-term", "key": "服务期限", "value": "12个月", "status": "confirmed", "reason": "", "source": None},
            "f-pending": {"id": "f-pending", "key": "驻场人数", "value": "2", "status": "pending", "reason": "", "source": None},
            "f-card": {"id": "f-card", "key": "联系人身份证号", "value": "310115198801012345", "status": "confirmed",
                       "reason": "", "source": None},
        })
    client.app.state.service.repository.transaction(write)
    return project_id


def fingerprint(client, editor, project_id):
    return client.get(f"/api/v1/projects/{project_id}/workspace", headers=editor).json()["input_fingerprint"]


def commit(client, editor, lease, content, key, project_id):
    revision = client.get(f"/api/chapters/{CHAPTER}", headers=editor).json()["revision"]
    return client.post(f"/api/chapters/{CHAPTER}/versions", headers=editor, json={
        "lease_token": lease, "base_revision": revision, "content": content, "idempotency_key": "test-variable-nodes-" + key,
        "input_fingerprint": fingerprint(client, editor, project_id)})


def test_nodes_show_confirmed_value_mask_and_invalid_reason(client):
    editor = login(client)
    project_id = seed(client, editor)
    body = "服务期 {{fact:f-term}}。\n驻场 {{fact:f-pending}} 人。\n联系人 {{fact:f-card}}。\n未知 {{fact:nope}}，残缺 {{fact:f-te"
    response = client.post(f"/api/v1/projects/{project_id}/chapters/{CHAPTER}/variables", headers=editor, json={"content": body})
    assert response.status_code == 200, response.text
    items = response.json()["variables"]
    by_ref = {item["ref"]: item for item in items}
    assert by_ref["f-term"]["status"] == "valid" and by_ref["f-term"]["display"] == "12个月" and by_ref["f-term"]["line"] == 0
    assert by_ref["f-term"]["label"] == "服务期限" and by_ref["f-term"]["source"] == "facts"
    assert by_ref["f-pending"]["status"] == "invalid" and by_ref["f-pending"]["code"] == "FACT_VARIABLE_INVALID"
    assert by_ref["f-pending"]["display"] == ""
    card = by_ref["f-card"]
    assert card["masked"] and "310115198801012345" not in card["display"] and card["display"].startswith("310")
    assert by_ref["nope"]["status"] == "unknown"
    broken = [item for item in items if item["ref"] == ""]
    assert len(broken) == 1 and broken[0]["status"] == "unknown" and broken[0]["line"] == 3
    assert response.json()["invalid"] == 3
    assert [item["start"] for item in items] == sorted(item["start"] for item in items)

    committed = client.post(f"/api/v1/projects/{project_id}/chapters/{CHAPTER}/variables", headers=editor, json={})
    assert committed.status_code == 200 and committed.json()["revision"] >= 1

    viewer = login(client, "alpha-viewer")
    assert client.post(f"/api/v1/projects/{project_id}/chapters/{CHAPTER}/variables", headers=viewer, json={"content": body}).status_code == 200
    outsider = login(client, "beta-editor")
    assert client.post(f"/api/v1/projects/{project_id}/chapters/{CHAPTER}/variables", headers=outsider, json={"content": body}).status_code in (403, 404)


def test_commit_rejects_new_invalid_variables_but_keeps_existing_ones(client):
    editor = login(client)
    project_id = seed(client, editor)
    lease = client.post(f"/api/chapters/{CHAPTER}/lock", headers=editor, json={"takeover_reason": None}).json()["lease_token"]
    ok = commit(client, editor, lease, "服务期 {{fact:f-term}}。", "var-1", project_id)
    assert ok.status_code == 200, ok.text

    for index, (bad, code) in enumerate((("{{fact:nope}}", "FACT_VARIABLE_INVALID"), ("{{fact:f-pending}}", "FACT_VARIABLE_INVALID"),
                      ("{{fact:f-te", "FACT_VARIABLE_INVALID"), ("{{sla:missing}}", "SLA_VARIABLE_UNKNOWN"))):
        refused = commit(client, editor, lease, "服务期 {{fact:f-term}}。\n新增 " + bad, f"var-bad-{index}", project_id)
        assert refused.status_code == 409 and refused.json()["code"] == code, refused.text
        assert refused.json()["details"]["variables"][0]["status"] in ("unknown", "invalid")
    assert client.get(f"/api/chapters/{CHAPTER}", headers=editor).json()["content"] == "服务期 {{fact:f-term}}。"

    # 已在正文里的变量之后失效（事实被改回待确认）：改别的段落仍能提交
    client.app.state.service.repository.transaction(
        lambda state: state.workflows[project_id]["facts"]["f-term"].__setitem__("status", "pending"))
    again = commit(client, editor, lease, "服务期 {{fact:f-term}}。\n巡检每月一次。", "var-2", project_id)
    assert again.status_code == 200, again.text
    # 但再新写一处同样的失效变量仍被拒绝
    twice = commit(client, editor, lease, "服务期 {{fact:f-term}}。\n巡检每月一次。\n又写 {{fact:f-term}}", "var-3", project_id)
    assert twice.status_code == 409 and twice.json()["code"] == "FACT_VARIABLE_INVALID"


def test_rollback_refuses_to_bring_back_invalid_variables(client):
    editor = login(client)
    project_id = seed(client, editor)
    lease = client.post(f"/api/chapters/{CHAPTER}/lock", headers=editor, json={"takeover_reason": None}).json()["lease_token"]
    assert commit(client, editor, lease, "服务期 {{fact:f-term}}。", "rb-1", project_id).status_code == 200
    assert commit(client, editor, lease, "服务期另行约定。", "rb-2", project_id).status_code == 200
    client.app.state.service.repository.transaction(
        lambda state: state.workflows[project_id]["facts"].pop("f-term"))
    history = client.get(f"/api/chapters/{CHAPTER}/versions", headers=editor).json()["versions"]
    target = next(v["revision"] for v in history if v["content"] == "服务期 {{fact:f-term}}。")
    current = client.get(f"/api/chapters/{CHAPTER}", headers=editor).json()["revision"]
    response = client.post(f"/api/v1/projects/{project_id}/chapters/{CHAPTER}/rollback", headers=editor, json={
        "lease_token": lease, "base_revision": current, "target_revision": target,
        "input_fingerprint": fingerprint(client, editor, project_id)})
    assert response.status_code == 409 and response.json()["code"] == "FACT_VARIABLE_INVALID", response.text
