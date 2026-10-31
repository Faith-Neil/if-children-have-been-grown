# 为什么有这个文件：验证项目状态流转、取消后只读、基本信息人工修改标记、合作方协议标记、拟派人员占用提示、
# 规则覆盖、分册格式与递交版完整值类别（PRD v1.8 §4.3、§5.1.3、§5.1.4；APP-M2-T097～T100）。
# 它解决什么问题：这些设置此前没有后台保存与读回；本文件逐项保存正例、权限反例、旧版本与失败用例。全部用合成数据。

from uuid import uuid4

from test_merge_checklist import _submission
from test_reference_flow import ProjectFlow, client, login  # noqa: F401


def _call(flow, method, path, body=None, expected=200, headers=None, version=None):
    version = flow.state()["revision"] if version is None else version
    resp = flow.client.request(method, flow.path + path, json=body,
                               headers=headers or {**flow.headers, "If-Match": str(version), "Idempotency-Key": str(uuid4())})
    assert resp.status_code == expected, resp.text
    return resp.json()


def _settings(flow):
    resp = flow.client.get(flow.path + "/settings", headers=flow.headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


def _as(flow, account):
    return {**login(flow.client, account), "If-Match": str(flow.state()["revision"]), "Idempotency-Key": str(uuid4())}


# ------------------------------------------------------------------ T097 状态

def test_cancel_makes_project_read_only_and_cannot_be_undone(client):
    flow = ProjectFlow(client)
    assert flow.state()["project_status"]["status"] == "draft"
    _call(flow, "POST", "/status", {"action": "cancel"}, expected=422)  # 取消须写原因
    done = _call(flow, "POST", "/status", {"action": "cancel", "reason": "招标条件不符，放弃投标"})
    assert done["status"]["status"] == "cancelled" and done["status"]["read_only"] is True
    state = flow.state()
    assert state["project_status"]["label"] == "已取消" and state["project_status"]["history"][0]["reason"] == "招标条件不符，放弃投标"
    blocked = _call(flow, "PATCH", "", {"name": "取消后改名"}, expected=409)
    assert blocked["code"] == "PROJECT_CANCELLED"
    assert flow.state()["project"]["name"] == "合成双册验收项目"  # 未被覆盖
    assert _call(flow, "POST", "/status", {"action": "open"}, expected=409)["code"] == "PROJECT_CANCELLED"
    audit = [e for e in client.app.state.service.repository.read().audit if e["action"] == "project.update:status"]
    assert audit and audit[-1]["details"]["action"] == "cancel"
    assert _settings(flow)["status"]["status"] == "cancelled"  # 读回仍可用


def test_status_flow_submit_open_result_follows_the_state_diagram(client):
    flow, _check, _export = _submission(client)
    assert _call(flow, "POST", "/status", {"action": "open"}, expected=409)["code"] == "INVALID_STATUS_TRANSITION"
    assert _call(flow, "POST", "/status", {"action": "cancel", "reason": "已导出后不能取消"}, expected=409)["code"] == "INVALID_STATUS_TRANSITION"
    assert _call(flow, "POST", "/status", {"action": "submit"})["status"]["status"] == "submitted"
    assert _call(flow, "POST", "/status", {"action": "result", "result": "won"}, expected=409)["code"] == "INVALID_STATUS_TRANSITION"
    assert _call(flow, "POST", "/status", {"action": "open"})["status"]["label"] == "已开标"
    _call(flow, "POST", "/status", {"action": "result"}, expected=422)  # 登记结果须选结果类型
    ended = _call(flow, "POST", "/status", {"action": "result", "result": "lost"})["status"]
    assert ended["status"] == "ended" and ended["result_label"] == "未中标" and not ended["read_only"]
    assert [h["to"] for h in ended["history"]] == ["submitted", "opened", "ended"]


def test_submit_needs_a_successful_submission_export_and_only_the_lead_changes_status(client):
    flow = ProjectFlow(client).ready()
    assert _call(flow, "POST", "/status", {"action": "submit"}, expected=409)["code"] == "INVALID_STATUS_TRANSITION"
    editor = _call(flow, "POST", "/status", {"action": "cancel", "reason": "编写人无权取消"}, expected=403, headers=_as(flow, "alpha-editor"))
    assert editor["code"] in ("PROJECT_LEAD_REQUIRED", "PROJECT_WRITER_REQUIRED")
    viewer = _call(flow, "POST", "/status", {"action": "cancel", "reason": "只读无权取消"}, expected=403, headers=_as(flow, "alpha-viewer"))
    assert viewer["code"] in ("FORBIDDEN", "PROJECT_WRITER_REQUIRED")
    assert flow.state()["project_status"]["registered"] is False


def test_stale_version_and_replay_for_status_change(client):
    flow = ProjectFlow(client)
    version = flow.state()["revision"]
    _call(flow, "PATCH", "", {"tender_number": "ST-001"}, version=version)
    stale = _call(flow, "POST", "/status", {"action": "cancel", "reason": "旧版本取消"}, expected=409, version=version)
    assert stale["code"] == "VERSION_CONFLICT"
    key = str(uuid4())
    headers = {**flow.headers, "If-Match": str(flow.state()["revision"]), "Idempotency-Key": key}
    first = _call(flow, "POST", "/status", {"action": "cancel", "reason": "重复请求只办一次"}, headers=headers)
    again = _call(flow, "POST", "/status", {"action": "cancel", "reason": "重复请求只办一次"}, headers=headers)
    assert again == first and len(flow.state()["project_status"]["history"]) == 1


# ------------------------------------------------------------------ T098 基本信息与合作方

def test_manual_edit_marks_only_changed_basic_fields(client):
    flow = ProjectFlow(client)
    assert _settings(flow)["manual_edits"] == {}
    _call(flow, "PATCH", "", {"basic_info": {"tenderee_name": "合成招标人", "client_address": "贵行"}})
    settings = _settings(flow)
    assert settings["basic_info"]["tenderee_name"] == "合成招标人" and settings["basic_info"]["agency_name"] == ""
    assert set(settings["manual_edits"]) == {"tenderee_name", "client_address"}
    assert settings["manual_edits"]["tenderee_name"]["by"] == "alpha-manager"
    _call(flow, "PATCH", "", {"basic_info": {"tenderee_name": "合成招标人"}, "name": "合成双册验收项目"})  # 内容没变不留新标记
    assert set(_settings(flow)["manual_edits"]) == {"tenderee_name", "client_address"}
    _call(flow, "PATCH", "", {"tender_number": "MAN-001"})
    assert "tender_number" in _settings(flow)["manual_edits"]
    _call(flow, "PATCH", "", {"basic_info": {"tenderee_name": "编写人改"}}, expected=403, headers=_as(flow, "alpha-editor"))
    assert _settings(flow)["basic_info"]["tenderee_name"] == "合成招标人"


def test_partner_without_agreement_is_flagged_and_listed_in_todos(client):
    flow = ProjectFlow(client)
    _call(flow, "PATCH", "", {"project_partners": [
        {"partner_entity_id": "partner-a", "agreement_attachment_id": "att-1", "relation_type": "consortium"},
        {"partner_entity_id": "partner-b", "agreement_attachment_id": "  ", "relation_type": "subcontract", "work_share": "运维分包"}]})
    settings = _settings(flow)
    rows = {p["partner_entity_id"]: p for p in settings["partners"]}
    assert rows["partner-a"]["agreement_ok"] is True and rows["partner-a"]["problem"] is None
    assert rows["partner-b"]["agreement_ok"] is False and "缺协议" in rows["partner-b"]["problem"]
    todo = [t for t in settings["todos"] if t["code"] == "PARTNER_AGREEMENT_MISSING"]
    assert len(todo) == 1 and "partner-b" in todo[0]["title"] and todo[0]["tab"] == "settings"
    dup = _call(flow, "PATCH", "", {"project_partners": [{"partner_entity_id": "x"}, {"partner_entity_id": "x"}]}, expected=422)
    assert "重复" in dup["message"]
    assert len(_settings(flow)["partners"]) == 2  # 校验失败不覆盖已有


# ------------------------------------------------------------------ T099 拟派人员占用、SLA、规则覆盖

def test_staff_occupancy_is_a_hint_and_released_after_open_or_cancel(client):
    first = ProjectFlow(client)
    _call(first, "PATCH", "", {"name": "甲项目占用在先"})
    person = first.library(name="合成工程师", type="personnel", content="学历：本科\n专业：计算机\n参加工作：2012-03\n证书：PMP")
    _call(first, "PUT", "/proposed-staff", {"staff": [{"person_id": person["id"], "role": "项目经理"}]})
    second = ProjectFlow(client)
    saved = _call(second, "PUT", "/proposed-staff", {"staff": [{"person_id": person["id"], "role": "技术负责人"}]})
    assert [(o["person_name"], o["other_project_name"]) for o in saved["occupancy"]] == [("合成工程师", "甲项目占用在先")]
    assert [s["person_id"] for s in saved["staff"]] == [person["id"]]  # 只提示，不锁定
    assert any(t["code"] == "STAFF_OCCUPIED" for t in _settings(second)["todos"])
    assert client.get(second.path + "/proposed-staff", headers=second.headers).json()["occupancy"]
    _call(first, "POST", "/status", {"action": "cancel", "reason": "放弃甲项目，释放人员"})
    assert _settings(second)["staff_occupancy"] == []


def test_settings_sla_is_none_without_template_and_hidden_from_other_companies(client):
    flow = ProjectFlow(client)
    assert _settings(flow)["sla"] is None
    assert client.get(flow.path + "/settings", headers=login(client, "beta-manager")).status_code in (403, 404)


def test_rule_overrides_validate_and_replace_as_a_whole(client):
    flow = ProjectFlow(client).reviewed()
    basis = flow.state()["requirements"][0]["id"]
    body = {"overrides": [{"rule_key": "proof_valid_days.纳税证明", "value": 90, "source_requirement_id": basis},
                          {"rule_key": "check_service_period", "value": True},
                          {"rule_key": "social_insurance_months", "value": 6}]}
    saved = _call(flow, "PUT", "/rule-overrides", body)
    assert {r["rule_key"]: r["value"] for r in saved["rule_overrides"]} == {
        "proof_valid_days.纳税证明": 90, "check_service_period": True, "social_insurance_months": 6}
    assert _settings(flow)["rule_overrides"][0]["source_requirement_id"] == basis
    for bad in ({"rule_key": "proof_valid_days.", "value": 30}, {"rule_key": "proof_valid_days.资质", "value": 0},
                {"rule_key": "check_service_period", "value": 1}, {"rule_key": "unknown_rule", "value": True},
                {"rule_key": "require_own_staff", "value": True, "source_requirement_id": "missing"},
                {"rule_key": "social_insurance_months", "value": 999}):
        _call(flow, "PUT", "/rule-overrides", {"overrides": [bad]}, expected=422)
    _call(flow, "PUT", "/rule-overrides", {"overrides": [body["overrides"][0], body["overrides"][0]]}, expected=422)
    assert len(_settings(flow)["rule_overrides"]) == 3  # 失败不改已存的
    _call(flow, "PUT", "/rule-overrides", body, expected=403, headers=_as(flow, "alpha-editor"))
    assert _call(flow, "PUT", "/rule-overrides", {"overrides": []})["rule_overrides"] == []


# ------------------------------------------------------------------ T100 分册与完整值

def _volume(volume="technical", **overrides):
    return {"volume": volume, "compile_mode": "system", "internal_deadline": None, "separate_seal": False,
            "page_numbering": "per_volume", "blind_bid": False, "cover_template": None, "submit_file_name": None, **overrides}


def test_volume_settings_save_read_back_and_warn_on_late_internal_deadline(client):
    flow = ProjectFlow(client)
    _call(flow, "PATCH", "", {"deadline": "2026-12-31T17:00:00+08:00"})
    saved = _call(flow, "PUT", "/volume-settings", {"volumes": [
        _volume("technical", internal_deadline="2026-12-30T17:00:00+08:00", blind_bid=True, cover_template="技术标封面"),
        _volume("business", compile_mode="external", separate_seal=True, page_numbering="continuous",
                internal_deadline="2027-01-02T09:00:00+08:00", submit_file_name="商务标正本")]})
    assert len(saved["warnings"]) == 1 and "商务" in saved["warnings"][0]  # 晚于投标截止只警告
    rows = {r["volume"]: r for r in _settings(flow)["volume_settings"]}
    assert rows["technical"]["blind_bid"] is True and rows["technical"]["cover_template"] == "技术标封面"
    assert rows["business"]["compile_mode"] == "external" and rows["business"]["page_numbering"] == "continuous"


def test_submit_file_name_rejects_writer_variable_and_writer_name(client):
    flow = ProjectFlow(client)
    var = _call(flow, "PUT", "/volume-settings", {"volumes": [_volume(submit_file_name="{编写人}_技术标")]}, expected=422)
    assert "编写人" in var["message"]
    name = _call(flow, "PUT", "/volume-settings", {"volumes": [_volume(submit_file_name="张三技术标")]}, expected=200)
    assert name["volume_settings"][0]["submit_file_name"] == "张三技术标"  # 非成员姓名不拦
    writer = client.app.state.service.repository.read().accounts["alpha-editor"].name
    leaked = _call(flow, "PUT", "/volume-settings", {"volumes": [_volume(submit_file_name=f"{writer}技术标")]}, expected=422)
    assert writer in leaked["message"]
    assert _settings(flow)["volume_settings"][0]["submit_file_name"] == "张三技术标"
    _call(flow, "PUT", "/volume-settings", {"volumes": [_volume(internal_deadline="明天")]}, expected=422)
    _call(flow, "PUT", "/volume-settings", {"volumes": [_volume(), _volume()]}, expected=422)
    _call(flow, "PUT", "/volume-settings", {"volumes": [_volume()]}, expected=403, headers=_as(flow, "alpha-editor"))


def test_volume_file_name_is_used_for_the_submission_export(client):
    flow = ProjectFlow(client).ready()
    _call(flow, "PUT", "/volume-settings", {"volumes": [_volume("technical", submit_file_name="技术标正本"),
                                                       _volume("business", submit_file_name="商务标正本")]})
    from icg.domain.export_naming import filenames
    state = client.app.state.service.repository.read()
    names, _rule = filenames(state, state.projects[flow.id], state.workflows[flow.id], "submission",
                             {"technical": "技术分册", "business": "商务分册"}, "20261231")
    assert names == {"technical": "技术标正本.docx", "business": "商务标正本.docx"}


def test_full_value_categories_need_basis_and_only_the_lead_can_confirm(client):
    flow = ProjectFlow(client).reviewed()
    basis = flow.state()["requirements"][0]["id"]
    _call(flow, "PUT", "/submit-full-value", {"categories": ["id_number"], "basis_requirement_ids": []}, expected=422)
    _call(flow, "PUT", "/submit-full-value", {"categories": ["id_number"], "basis_requirement_ids": ["nope"]}, expected=422)
    _call(flow, "PUT", "/submit-full-value", {"categories": ["passport"], "basis_requirement_ids": [basis]}, expected=422)
    denied = _call(flow, "PUT", "/submit-full-value", {"categories": ["phone"], "basis_requirement_ids": [basis]},
                   expected=403, headers=_as(flow, "alpha-editor"))
    assert denied["code"] in ("PROJECT_LEAD_REQUIRED", "PROJECT_WRITER_REQUIRED")
    assert _settings(flow)["submit_full_value"]["categories"] == []
    saved = _call(flow, "PUT", "/submit-full-value", {"categories": ["id_number", "phone", "id_number"], "basis_requirement_ids": [basis]})
    info = saved["submit_full_value"]
    assert info["categories"] == ["id_number", "phone"] and info["confirmed_by"] == "alpha-manager" and info["confirmed_at"]
    cleared = _call(flow, "PUT", "/submit-full-value", {"categories": [], "basis_requirement_ids": []})["submit_full_value"]
    assert cleared["categories"] == [] and cleared["confirmed_by"] is None


# ------------------------------------------------------------------ T097 概览待办

def test_overview_todos_cover_volume_owner_and_internal_deadline(client):
    flow = ProjectFlow(client)
    todos = {t["code"] for t in _settings(flow)["todos"]}
    assert "VOLUME_OWNER_MISSING" not in todos  # 负责人已指定
    _call(flow, "PUT", "/volume-settings", {"volumes": [_volume(internal_deadline="2020-01-01T09:00:00+08:00"), _volume("business")]})
    assert "VOLUME_DEADLINE_NEAR" in {t["code"] for t in _settings(flow)["todos"]}
    _call(flow, "POST", "/status", {"action": "cancel", "reason": "取消后不再列待办"})
    assert _settings(flow)["todos"] == []
