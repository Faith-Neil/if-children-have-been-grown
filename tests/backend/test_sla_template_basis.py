# 为什么有这个文件：通过真实服务模板接口核对旧弹窗的版本保护和变量数组冲突。
# 它解决什么问题：避免30分钟旧表单覆盖别人核对的90分钟，或用旧数组恢复已删除的指标。

from copy import deepcopy
from uuid import uuid4

import pytest

from test_reference_flow import client, login


TEMPLATE_PATH = "/api/v1/sla/templates"


def read_templates(client, actor):
    response = client.get(TEMPLATE_PATH, headers=actor)
    assert response.status_code == 200, response.text
    listing = response.json()
    assert response.headers["etag"] == f'"{listing["revision"]}"'
    return listing


def write_headers(actor, read_revision):
    return {**actor, "If-Match": str(read_revision), "Idempotency-Key": str(uuid4())}


def variable(key, minutes):
    return {"var_key": key, "label": key + "合成故障响应时限", "group": "response",
            "value_type": "integer", "default_value": minutes, "unit": "minute",
            "compare_direction": "lower_better", "best_committable_value": 15}


def create_template(client, actor, *, with_second=False):
    payload = {"name": "公司SLA旧弹窗合成验收", "edition": "standard", "service_hours": "h7x24",
               "version_no": "1.0", "body_text": "一级故障响应时限{{P1.response}}分钟。",
               "status": "confirmed", "reason": "初次核对合成30分钟服务模板。",
               "variables": [variable("P1.response", 30)]}
    if with_second:
        payload["variables"].append(variable("P2.response", 60))
    revision = read_templates(client, actor)["revision"]
    response = client.post(TEMPLATE_PATH, headers=write_headers(actor, revision), json=payload)
    assert response.status_code == 200, response.text
    return response.json()["item"], payload


def test_stale_30_minute_form_is_rejected_and_explicit_review_preserves_90_minutes(client):
    first, second = login(client, "alpha-manager"), login(client, "alpha-outsider-manager")
    created, old_form = create_template(client, first)
    path = TEMPLATE_PATH + "/" + created["id"]

    # 关联一个真实项目，旧模板写入失败时连项目状态也不能留下副作用。
    project_path = "/api/v1/projects/alpha-project"
    project = client.get(project_path + "/workspace", headers=first)
    assert project.status_code == 200, project.text
    selected = client.post(project_path + "/sla/template",
                           headers=write_headers(first, project.json()["revision"]),
                           json={"template_id": created["id"]})
    assert selected.status_code == 200, selected.text

    old_listing = read_templates(client, first)
    changed_form = deepcopy(old_form)
    changed_form["variables"][0]["default_value"] = 90
    changed_form["reason"] = "另一人已逐项核对最新90分钟默认值。"
    changed = client.patch(path, headers=write_headers(second, old_listing["revision"]), json=changed_form)
    assert changed.status_code == 200, changed.text
    before = client.app.state.service.repository.read()
    rejected = client.patch(path, headers=write_headers(first, old_listing["revision"]), json=old_form)
    assert rejected.status_code == 409, rejected.text
    assert rejected.json()["code"] == "VERSION_CONFLICT"
    assert client.app.state.service.repository.read() == before

    reread = read_templates(client, first)
    newest = next(item for item in reread["items"] if item["id"] == created["id"])
    assert newest["variables"][0]["default_value"] == 90
    assert rejected.json()["details"]["current_revision"] == reread["revision"]
    # 请求从真实新版本构造；没有把旧30分钟表单直接换个新版本号重新提交。
    reviewed_payload = {key: deepcopy(newest[key]) for key in old_form}
    reviewed_payload["body_text"] += " 本次已核对新的服务标准。"
    reviewed_payload["reason"] = "重新读取后确认保留90分钟，仅补充承诺函说明。"
    accepted = client.patch(path, headers=write_headers(first, reread["revision"]), json=reviewed_payload)
    assert accepted.status_code == 200, accepted.text
    result = accepted.json()
    assert result["revision"] == reread["revision"] + 1
    assert result["item"]["revision"] == newest["revision"] + 1
    assert result["item"]["variables"] == newest["variables"]
    assert result["item"]["variables"][0]["default_value"] == 90
    assert result["item"]["body_text"] == reviewed_payload["body_text"]
    assert result["item"]["reason"] == reviewed_payload["reason"]
    assert result["item"]["status"] == "confirmed"
    assert next(item for item in read_templates(client, first)["items"] if item["id"] == created["id"]) == result["item"]


@pytest.mark.parametrize("change", ["values", "added_variable", "removed_variable"])
def test_old_complete_variable_array_cannot_overwrite_new_values_additions_or_removals(client, change):
    first, second = login(client, "alpha-manager"), login(client, "alpha-outsider-manager")
    created, old_form = create_template(client, first, with_second=True)
    path = TEMPLATE_PATH + "/" + created["id"]
    old_listing = read_templates(client, first)
    changed_form = deepcopy(old_form)
    changed_form["reason"] = "另一位协作者已核对本次指标调整。"
    if change == "values":
        changed_form["variables"][0]["default_value"] = 90
        changed_form["variables"][1]["default_value"] = 120
    elif change == "added_variable":
        changed_form["variables"].append(variable("P3.response", 45))
    else:
        changed_form["variables"] = [changed_form["variables"][0]]
    changed = client.patch(path, headers=write_headers(second, old_listing["revision"]), json=changed_form)
    assert changed.status_code == 200, changed.text
    current = read_templates(client, first)
    before = client.app.state.service.repository.read()
    rejected = client.patch(path, headers=write_headers(first, old_listing["revision"]), json=old_form)
    assert rejected.status_code == 409, rejected.text
    assert rejected.json()["code"] == "VERSION_CONFLICT"
    assert client.app.state.service.repository.read() == before
    assert read_templates(client, first) == current
    saved = next(item for item in current["items"] if item["id"] == created["id"])
    assert saved["variables"] == changed.json()["item"]["variables"]
    assert saved["variables"] != old_form["variables"]
    if change == "removed_variable":
        assert "P2.response" not in {item["var_key"] for item in saved["variables"]}
    elif change == "added_variable":
        assert "P3.response" in {item["var_key"] for item in saved["variables"]}
    else:
        assert [item["default_value"] for item in saved["variables"]] == [90, 120]


@pytest.mark.parametrize("account,status,code", [
    ("beta-manager", 404, "NOT_FOUND"),
    ("alpha-viewer", 403, "SLA_MANAGER_REQUIRED"),
])
def test_company_or_viewer_scope_rejects_template_mutation_without_changing_state(client, account, status, code):
    owner = login(client, "alpha-manager")
    created, old_form = create_template(client, owner)
    actor = login(client, account)
    listing = read_templates(client, actor)
    visible = created["id"] in {item["id"] for item in listing["items"]}
    assert visible is (account == "alpha-viewer")
    before = client.app.state.service.repository.read()
    rejected = client.patch(TEMPLATE_PATH + "/" + created["id"],
                            headers=write_headers(actor, listing["revision"]), json=old_form)
    assert rejected.status_code == status, rejected.text
    assert rejected.json()["code"] == code
    assert client.app.state.service.repository.read() == before
