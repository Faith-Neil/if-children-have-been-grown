# 为什么有这个文件：独立核对服务承诺的真实接口、风险确认和下载内容。
# 它解决什么问题：防止单位改错、旧模板或旧批准继续放行，以及旧接口绕过新门禁。

import base64
from io import BytesIO
from uuid import uuid4
from xml.etree import ElementTree
from zipfile import ZipFile

import pytest
from fastapi.testclient import TestClient

from icg_demo.adapters import MemoryRepository, seed_state
from icg_demo.domain import Account
from icg_demo.main import create_app


@pytest.fixture
def client():
    state = seed_state()
    from icg.domain.auth_service import hash_password
    digest, salt = hash_password("X_2026")
    state.accounts["beta-manager"] = Account("beta-manager", "乙公司项目经理（合成）", "beta", "manager",
                                             password_hash=digest, salt=salt)
    with TestClient(create_app(repository=MemoryRepository(state))) as actual:
        yield actual


def login(client, account="alpha-manager"):
    result = client.post("/api/v1/auth/login", json={"username": account, "password": "X_2026"})
    assert result.status_code == 200, result.text
    return {"Authorization": "Bearer " + result.json()["access_token"]}


class SlaFlow:
    def __init__(self, client, project_id="alpha-project", account="alpha-manager"):
        self.client = client
        self.headers = login(client, account)
        self.project_id = project_id
        self.path = "/api/v1/projects/" + project_id

    def state(self):
        result = self.client.get(self.path + "/workspace", headers=self.headers)
        assert result.status_code == 200, result.text
        return result.json()

    def write(self, route, payload, method="POST", expected=200, headers=None):
        response = self.client.request(method, self.path + route, json=payload,
                                       headers=headers or {**self.headers, "If-Match": str(self.state()["revision"]),
                                                           "Idempotency-Key": str(uuid4())})
        assert response.status_code == expected, response.text
        return response.json()

    def template(self, variable=None, body="一级故障响应时限为{{P1.response}}分钟。", expected=200):
        variable = {"var_key": "P1.response", "label": "一级故障响应时限", "group": "response",
                    "value_type": "decimal", "default_value": "30", "unit": "minute",
                    "compare_direction": "lower_better", "best_committable_value": "15", **(variable or {})}
        payload = {"name": "合成公司服务承诺", "version_no": "1.0", "service_hours": "h7x24",
                   "body_text": body, "status": "confirmed", "variables": [variable],
                   "reason": "本次逐项核对合成模板，仅用于测试，不代表真实公司的履约能力。"}
        revision = self.client.get("/api/v1/sla/templates", headers=self.headers).json()["revision"]
        response = self.client.post("/api/v1/sla/templates", json=payload,
                                    headers={**self.headers, "If-Match": str(revision), "Idempotency-Key": str(uuid4())})
        assert response.status_code == expected, response.text
        if expected != 200:
            return response.json()
        item = response.json()["item"]
        self.write("/sla/template", {"template_id": item["id"]})
        return item

    def patch_template(self, template_id, payload, expected=200, headers=None):
        actor = headers or self.headers
        revision = self.client.get("/api/v1/sla/templates", headers=actor).json()["revision"]
        response = self.client.patch("/api/v1/sla/templates/" + template_id, json=payload,
                                     headers={**actor, "If-Match": str(revision), "Idempotency-Key": str(uuid4())})
        assert response.status_code == expected, response.text
        return response.json()

    def source(self):
        self.write("/files", {"filename": "合成服务条款.txt", "content_base64": base64.b64encode(
            "技术要求：一级故障响应时限不得超过30分钟。".encode()).decode()})
        self.write("/parse", {})
        requirement = self.state()["requirements"][0]
        self.write("/requirements/" + requirement["id"], {"category": "sla", "status": "confirmed"}, "PATCH")
        return requirement

    def bind(self, value="30", unit="minute", required="30", tender_unit="minute"):
        requirement = self.source()
        self.write("/sla/values/P1.response", {"project_value": value, "project_unit": unit,
                   "requirement_id": requirement["id"], "tender_required_value": required,
                   "tender_unit": tender_unit, "reason": "逐项核对合成原文的响应时限。"}, "PATCH")
        return requirement

    def row(self, key="P1.response"):
        return next(row for row in self.state()["sla"]["rows"] if row["var_key"] == key)

    def confirm(self, key="P1.response"):
        return self.write("/facts/sla:" + key, {"status": "confirmed", "reason": "负责人逐项核对。"}, "PATCH")

    def commitment(self):
        return self.write("/sla/commitment", {})["commitment"]


def word_text(content):
    with ZipFile(BytesIO(content)) as package:
        document = ElementTree.fromstring(package.read("word/document.xml"))
    return "\n".join(node.text or "" for node in document.iter(
        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t")), document


@pytest.mark.parametrize("value,unit,expected", [
    ("30", "minute", "satisfied"), ("60", "minute", "not_satisfied"),
    ("10", "minute", "exceeds_capability"), (None, "minute", "missing"),
    ("1", "working_day", "manual"),
])
def test_real_matrix_five_judgments(client, value, unit, expected):
    flow = SlaFlow(client)
    flow.template()
    flow.bind(value=value, unit=unit)
    assert flow.row()["judgment"] == expected


def test_without_tender_and_unquantified_are_not_satisfied_labels(client):
    flow = SlaFlow(client)
    flow.template()
    assert flow.row()["judgment"] == "not_required"
    flow.bind(required=None)
    assert flow.row()["judgment"] == "unquantified"
    flow.write("/facts/sla:P1.response", {"status": "confirmed"}, "PATCH", expected=409)


def test_commitment_cover_includes_centered_project_name(client):
    flow = SlaFlow(client)
    flow.template()
    flow.bind()
    flow.confirm()
    downloaded = client.get(flow.commitment()["download_url"], headers=flow.headers)
    assert downloaded.status_code == 200, downloaded.text
    w = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    with ZipFile(BytesIO(downloaded.content)) as package:
        document = ElementTree.fromstring(package.read("word/document.xml"))
        styles = ElementTree.fromstring(package.read("word/styles.xml"))
    paragraph = next(item for item in document.iter(w + "p")
                     if (item.find(f"{w}pPr/{w}pStyle") is not None
                         and item.find(f"{w}pPr/{w}pStyle").get(w + "val") == "CoverProject"
                         and "".join(node.text or "" for node in item.iter(w + "t")) == "甲公司合成投标项目"))
    defined = next(item for item in styles.iter(w + "style") if item.get(w + "styleId") == "CoverProject")
    fonts = paragraph.find(f".//{w}rFonts")
    assert fonts.get(w + "ascii") == "黑体"
    assert fonts.get(w + "hAnsi") == "黑体"
    assert fonts.get(w + "eastAsia") == "黑体"
    assert paragraph.find(f".//{w}sz").get(w + "val") == "32"
    assert defined.find(f".//{w}jc").get(w + "val") == "center"


def test_hours_render_as_template_minutes_in_actual_word(client):
    flow = SlaFlow(client)
    flow.template()
    flow.bind(value="0.5", unit="hour")
    assert flow.row()["judgment"] == "satisfied"
    flow.confirm()
    export = flow.commitment()
    downloaded = client.get(export["download_url"], headers=flow.headers)
    assert downloaded.status_code == 200, downloaded.text
    text, xml = word_text(downloaded.content)
    assert "一级故障响应时限为30分钟。" in text
    assert "0.5分钟" not in text
    assert "0.5 小时" in text
    assert list(xml.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tbl"))
    assert "{{" not in text


def test_unknown_or_incomplete_variable_blocks_check(client):
    flow = SlaFlow(client)
    flow.template()
    flow.bind()
    flow.confirm()
    lease = client.post("/api/chapters/alpha-tech/lock", headers=flow.headers, json={}).json()
    for text in ("未知变量{{sla:NoSuchValue}}。", "响应时限{{ sla:P1.response 分钟。"):
        chapter = client.get("/api/chapters/alpha-tech", headers=flow.headers).json()
        result = client.post("/api/chapters/alpha-tech/versions", headers=flow.headers, json={
            "lease_token": lease["lease_token"], "input_fingerprint": flow.state()["input_fingerprint"], "base_revision": chapter["revision"],
            "content": text, "idempotency_key": str(uuid4())})
        # 提交时后台先拒绝新写入的失效变量（APP-M2-T164）
        assert result.status_code == 409 and result.json()["code"] == "SLA_VARIABLE_UNKNOWN", result.text
        # 检查仍是第二道关：正文里已有的失效变量（例如之前写入、后来失效）照样拦截
        client.app.state.service.repository.transaction(
            lambda state, text=text: setattr(state.chapters["alpha-tech"], "content", text))
        check = flow.write("/checks", {"volume": "all"})["check"]
        assert any(issue["code"] == "SLA_VARIABLE_UNKNOWN" for issue in check["issues"])


def test_manual_unit_review_cannot_create_wrong_template_unit_word(client):
    flow = SlaFlow(client)
    flow.template()
    flow.bind(value="1", unit="working_day", required="1", tender_unit="calendar_day")
    flow.write("/sla/values/P1.response/review", {"reason": "负责人记录两种日历口径需要人工核对。"})
    flow.confirm()
    result = flow.write("/sla/commitment", {}, expected=409)
    assert result["code"] == "SLA_COMMITMENT_BLOCKED"
    assert any(issue["code"] == "SLA_VARIABLE_UNIT_UNRESOLVED" for issue in result["details"]["issues"])


@pytest.mark.parametrize("account", ["alpha-editor", "alpha-viewer"])
def test_manager_only_mutations_and_risk_confirmation(client, account):
    flow = SlaFlow(client)
    template = flow.template()
    flow.bind(value="10")
    actor = login(client, account)
    flow.write("/sla/template", {"template_id": template["id"]}, expected=403,
               headers={**actor, "If-Match": str(flow.state()["revision"]), "Idempotency-Key": str(uuid4())})
    flow.write("/sla/values/P1.response/review", {"reason": "无管理权不能批准"}, expected=403,
               headers={**actor, "If-Match": str(flow.state()["revision"]), "Idempotency-Key": str(uuid4())})
    flow.write("/facts/sla:P1.response", {"status": "confirmed"}, "PATCH", expected=403,
               headers={**actor, "If-Match": str(flow.state()["revision"]), "Idempotency-Key": str(uuid4())})
    revision = client.get("/api/v1/sla/templates", headers=actor).json()["revision"]
    response = client.post("/api/v1/sla/templates", headers={**actor, "If-Match": str(revision),
                           "Idempotency-Key": str(uuid4())}, json={
        "name": "无管理权", "body_text": "{{P1.response}}", "variables": template["variables"]})
    assert response.status_code == 403


def test_templates_and_project_values_are_company_isolated(client):
    alpha = SlaFlow(client)
    template = alpha.template()
    beta = SlaFlow(client, "beta-project", "beta-manager")
    items = client.get("/api/v1/sla/templates", headers=beta.headers).json()["items"]
    assert template["id"] not in {item["id"] for item in items}
    beta.write("/sla/template", {"template_id": template["id"]}, expected=404)
    beta.patch_template(template["id"], {"name": "跨公司修改"}, expected=404)
    response = client.get(alpha.path + "/workspace", headers=beta.headers)
    assert response.status_code == 404


def test_risk_cannot_waive_unsatisfied_and_changes_remove_approval(client):
    flow = SlaFlow(client)
    flow.template()
    flow.bind(value="60")
    flow.write("/sla/values/P1.response/review", {"reason": "不足不能批准"}, expected=409)
    flow.write("/sla/values/P1.response", {"project_value": "10"}, "PATCH")
    flow.write("/facts/sla:P1.response", {"status": "confirmed"}, "PATCH", expected=409)
    flow.write("/sla/values/P1.response/review", {"reason": "   "}, expected=422)
    flow.write("/sla/values/P1.response/review", {"reason": "已核对合成履约依据。"})
    flow.confirm()
    assert flow.row()["review"]["actor_id"] == "alpha-manager"
    export = flow.commitment()
    flow.write("/sla/values/P1.response", {"project_value": "11"}, "PATCH")
    row = flow.row()
    assert row["review"] is None and row["fact_status"] == "needs_review"
    assert client.get(export["download_url"], headers=flow.headers).status_code == 409


def test_fact_is_reference_only_and_requires_risk_review(client):
    flow = SlaFlow(client)
    flow.template()
    flow.bind()
    result = flow.write("/facts/sla:P1.response", {"value": "20", "status": "confirmed"}, "PATCH", expected=409)
    assert result["code"] == "SLA_FACT_READ_ONLY"
    assert flow.row()["project_value"] == "30"
    flow.confirm()
    fact = next(fact for fact in flow.state()["facts"] if fact["id"] == "sla:P1.response")
    assert fact["source_type"] == "sla" and fact["value"] == "30" and fact["required"]
    flow.write("/sla/values/P1.response", {"project_value": "20"}, "PATCH")
    fact = next(fact for fact in flow.state()["facts"] if fact["id"] == "sla:P1.response")
    assert fact["value"] == "20" and fact["status"] == "needs_review"


def test_source_must_exist_and_changes_need_explicit_rebinding(client):
    flow = SlaFlow(client)
    flow.template()
    flow.write("/sla/values/P1.response", {"tender_required_value": "30", "reason": "无来源"}, "PATCH", expected=422)
    flow.write("/sla/values/P1.response", {"requirement_id": "another-project-source", "tender_required_value": "30",
               "reason": "错误来源"}, "PATCH", expected=409)
    requirement = flow.bind()
    flow.confirm()
    export = flow.commitment()
    flow.write("/requirements/" + requirement["id"], {"text": "技术要求：一级故障响应时限不得超过20分钟。"}, "PATCH")
    assert flow.row()["source_stale"] and flow.row()["fact_status"] == "needs_review"
    assert client.get(export["download_url"], headers=flow.headers).status_code == 409
    flow.write("/requirements/" + requirement["id"], {"status": "confirmed"}, "PATCH")
    assert flow.row()["source_stale"]
    flow.write("/sla/values/P1.response", {"requirement_id": requirement["id"], "tender_required_value": "20",
               "reason": "重新核对合成补遗的20分钟。"}, "PATCH")
    assert not flow.row()["source_stale"] and flow.row()["judgment"] == "not_satisfied"


def test_template_updates_invalidate_old_approval_and_download_keep_project_value(client):
    flow = SlaFlow(client)
    template = flow.template()
    flow.bind(value="10")
    flow.write("/sla/values/P1.response/review", {"reason": "合成风险确认"})
    flow.confirm()
    export = flow.commitment()
    old_project_revision = flow.state()["revision"]
    variables = [{**template["variables"][0], "best_committable_value": "20"}]
    updated = flow.patch_template(template["id"], {"variables": variables})["item"]
    assert updated["status"] == "pending"
    assert flow.state()["sla"]["template_stale"]
    assert flow.row()["review"] is None and flow.row()["fact_status"] == "needs_review"
    assert flow.row()["project_value"] == "10"
    assert flow.state()["revision"] > old_project_revision
    stale_project_write = client.patch(flow.path, headers={**flow.headers, "If-Match": str(old_project_revision),
                                       "Idempotency-Key": str(uuid4())}, json={"name": "旧输入不应覆盖项目"})
    assert stale_project_write.status_code == 409
    assert client.get(export["download_url"], headers=flow.headers).status_code == 409
    flow.write("/sla/template", {"template_id": template["id"]}, expected=409)
    flow.patch_template(template["id"], {"status": "confirmed", "reason": "负责人核对更新后的合成能力。"})
    flow.write("/sla/template", {"template_id": template["id"], "reason": "刷新公司能力"})
    assert not flow.state()["sla"]["template_stale"]
    assert flow.row()["project_value"] == "10" and flow.row()["best_committable_value"] == "20"
    assert flow.row()["fact_status"] == "needs_review" and flow.row()["review"] is None


def test_deleted_template_variable_cannot_silently_drop_project_value(client):
    flow = SlaFlow(client)
    template = flow.template()
    definition = {**template["variables"][0], "var_key": "P2.response", "label": "二级故障响应时限"}
    flow.patch_template(template["id"], {"variables": [definition], "body_text": "{{P2.response}}分钟", "status": "confirmed", "reason": "合成变更"})
    result = flow.write("/sla/template", {"template_id": template["id"]}, expected=409)
    assert result["code"] == "SLA_VARIABLE_REMOVED"
    assert flow.row()["var_key"] == "P1.response"


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-1", True, "nonsense"])
def test_invalid_numbers_rejected_without_changing_saved_value(client, value):
    flow = SlaFlow(client)
    flow.template()
    flow.write("/sla/values/P1.response", {"project_value": value}, "PATCH", expected=422)
    assert flow.row()["project_value"] == "30"


def test_template_unknown_variable_and_integer_type_constraints(client):
    flow = SlaFlow(client)
    result = flow.template(body="未知{{NoSuchValue}}分钟", expected=409)
    assert result["code"] == "SLA_TEMPLATE_VARIABLE_UNKNOWN"
    flow.template(variable={"value_type": "integer"})
    flow.write("/sla/values/P1.response", {"project_value": "1.5"}, "PATCH", expected=422)
    flow.write("/sla/values/P1.response", {"project_unit": "day"}, "PATCH", expected=422)


@pytest.mark.parametrize("direction,project,tender,capability,expected", [
    ("higher_better", "2", "4", "8", "not_satisfied"),
    ("higher_better", "4", "4", "8", "satisfied"),
    ("higher_better", "9", "4", "8", "exceeds_capability"),
    ("exact", "3", "4", "4", "not_satisfied"),
    ("exact", "4", "4", "4", "satisfied"),
])
def test_direction_uses_counts_and_exact_correctly(client, direction, project, tender, capability, expected):
    flow = SlaFlow(client)
    flow.template(variable={"unit": "person", "compare_direction": direction, "best_committable_value": capability}, body="承诺人数{{P1.response}}人。")
    flow.bind(value=project, unit="person", required=tender, tender_unit="person")
    assert flow.row()["judgment"] == expected


def test_project_write_replay_and_stale_version_guards(client):
    flow = SlaFlow(client)
    flow.template()
    headers = {**flow.headers, "If-Match": str(flow.state()["revision"]), "Idempotency-Key": str(uuid4())}
    payload = {"project_value": "20"}
    first = flow.write("/sla/values/P1.response", payload, "PATCH", headers=headers)
    second = flow.write("/sla/values/P1.response", payload, "PATCH", headers=headers)
    assert first == second
    assert flow.state()["revision"] == first["revision"]
    result = flow.write("/sla/values/P1.response", {"project_value": "21"}, "PATCH", expected=409, headers=headers)
    assert result["code"] == "IDEMPOTENCY_CONFLICT"
    result = flow.write("/sla/values/P1.response", payload, "PATCH", expected=409,
                        headers={**headers, "Idempotency-Key": str(uuid4())})
    assert result["code"] == "VERSION_CONFLICT"
    flow.write("/sla/values/P1.response", payload, "PATCH", expected=428, headers=flow.headers)


@pytest.mark.parametrize("selected", [False, True])
def test_legacy_check_export_download_cannot_bypass_sla(client, selected):
    flow = SlaFlow(client)
    oldcheck = client.post("/api/chapters/alpha-tech/checks", headers=flow.headers, json={})
    assert oldcheck.status_code == 200 and oldcheck.json()["passed"]
    oldexport = client.post("/api/chapters/alpha-tech/exports", headers=flow.headers,
                            json={"check_id": oldcheck.json()["id"]})
    assert oldexport.status_code == 200, oldexport.text
    if selected:
        flow.template()
    else:
        flow.source()
    newcheck = client.post("/api/chapters/alpha-tech/checks", headers=flow.headers, json={})
    assert newcheck.status_code == 409, newcheck.text
    result = client.post("/api/chapters/alpha-tech/exports", headers=flow.headers, json={"check_id": oldcheck.json()["id"]})
    assert result.status_code == 409, result.text
    assert client.get(oldexport.json()["download_url"], headers=flow.headers).status_code == 409


def test_legacy_word_cannot_leave_unknown_sla_variable(client):
    flow = SlaFlow(client)
    chapter = client.get("/api/chapters/alpha-tech", headers=flow.headers).json()
    lease = client.post("/api/chapters/alpha-tech/lock", headers=flow.headers, json={}).json()
    result = client.post("/api/chapters/alpha-tech/versions", headers=flow.headers, json={
        "lease_token": lease["lease_token"], "base_revision": chapter["revision"], "content": "响应{{sla:unknown}}分钟。",
        "idempotency_key": str(uuid4())})
    assert result.status_code == 409 and result.json()["code"] == "SLA_VARIABLE_UNKNOWN", result.text
    client.app.state.service.repository.transaction(
        lambda state: setattr(state.chapters["alpha-tech"], "content", "响应{{sla:unknown}}分钟。"))
    check = client.post("/api/chapters/alpha-tech/checks", headers=flow.headers, json={})
    assert check.status_code == 409, check.text


def test_apply_tender_never_silently_crosses_company_capability(client):
    flow = SlaFlow(client)
    flow.template()
    flow.bind(value="30", required="10")
    flow.write("/sla/apply-tender", {})
    assert flow.row()["project_value"] == "15"
    assert flow.row()["judgment"] == "not_satisfied"
    flow.write("/sla/values/P1.response/review", {"reason": "限值不能变成满足"}, expected=409)


def test_report_frequencies_are_not_equated_by_annual_total(client):
    flow = SlaFlow(client)
    flow.template(variable={"unit": "per_month", "compare_direction": "higher_better", "default_value": "1",
                            "best_committable_value": "2"}, body="每月巡检{{P1.response}}次。")
    flow.bind(value="1", unit="per_month", required="3", tender_unit="per_quarter")
    assert flow.row()["judgment"] == "manual"


def test_commitment_template_labelled_number_cannot_disagree_with_variable(client):
    flow = SlaFlow(client)
    flow.template(body="一级故障响应时限为5分钟。")
    flow.bind()
    flow.confirm()
    result = flow.write("/sla/commitment", {}, expected=409)
    assert result["code"] == "SLA_COMMITMENT_BLOCKED"
    assert any(issue["code"] == "SLA_TEXT_MISMATCH" for issue in result["details"]["issues"])


def test_same_unit_variable_is_resolved_in_actual_two_volume_word(client):
    flow = SlaFlow(client)
    flow.template()
    requirement = flow.bind(value="0.5", unit="hour")
    flow.confirm()
    flow.write("", {"tender_number": "SLA-SYNTH-001", "deadline": "2026-12-31T17:00:00+08:00"}, "PATCH")
    flow.write("/requirements/" + requirement["id"], {"chapter_id": "alpha-tech", "response": "按经核对承诺响应。"}, "PATCH")
    flow.write("/parse/confirm", {})
    chapters = flow.state()["chapters"]
    flow.write("/plan", {"chapters": [{k: chapter[k] for k in ("id", "title", "volume")} for chapter in chapters]})
    chapter = client.get("/api/chapters/alpha-tech", headers=flow.headers).json()
    lease = client.post("/api/chapters/alpha-tech/lock", headers=flow.headers, json={}).json()
    result = client.post("/api/chapters/alpha-tech/versions", headers=flow.headers, json={
        "lease_token": lease["lease_token"], "input_fingerprint": flow.state()["input_fingerprint"], "base_revision": chapter["revision"],
        "content": "一级故障响应时限为{{sla:P1.response}}分钟。", "idempotency_key": str(uuid4())})
    assert result.status_code == 200, result.text
    check = flow.write("/checks", {"volume": "all"})["check"]
    # 商务章节没有映射条款，R30 给警告；由项目负责人填理由放行后才能导出
    for issue in [i for i in check["issues"] if i["severity"] == "warning"]:
        assert issue["code"] == "SCOPE_CHAPTER_WITHOUT_CLAUSE", issue
        check = flow.write(f"/checks/{check['id']}/issues/{issue['id']}/release", {"reason": "商务章节为通用资质说明"})["check"]
    assert check["passed"], check["issues"]
    export = flow.write("/exports", {"check_id": check["id"], "kind": "internal"})["export"]
    assert {volume["volume"] for volume in export["volumes"]} == {"technical", "business"}
    for volume in export["volumes"]:
        downloaded = client.get(volume["download_url"], headers=flow.headers)
        assert downloaded.status_code == 200, downloaded.text
        text, _ = word_text(downloaded.content)
        assert "{{" not in text
        if volume["volume"] == "technical":
            assert "一级故障响应时限为30分钟。" in text and "0.5分钟" not in text
    flow.write("/sla/values/P1.response", {"project_value": "1", "project_unit": "hour"}, "PATCH")
    # 旧批次标“已过期”但保留下载当时的快照（PRD §5.9.1 规则 13，APP-M2-T202）
    stale = client.get(export["volumes"][0]["download_url"], headers=flow.headers)
    assert stale.status_code == 200 and stale.headers["X-ICG-Export-Status"] == "stale"


def test_unrequested_extra_promise_requires_manager_review_before_word(client):
    flow = SlaFlow(client)
    flow.template()
    assert flow.row()["judgment"] == "not_required"
    flow.write("/sla/commitment", {}, expected=409)
    flow.write("/facts/sla:P1.response", {"status": "confirmed"}, "PATCH", expected=409)
    flow.write("/sla/values/P1.response/review", {"reason": "负责人明确承担合成额外承诺，记录履约依据。"})
    flow.confirm()
    export = flow.commitment()
    assert client.get(export["download_url"], headers=flow.headers).status_code == 200


def test_template_create_replay_missing_and_stale_library_version(client):
    flow = SlaFlow(client)
    payload = {"name": "合成重复请求模板", "body_text": "{{P1.response}}分钟。", "variables": [{
        "var_key": "P1.response", "label": "一级故障响应时限", "group": "response", "value_type": "integer",
        "default_value": "30", "unit": "minute", "compare_direction": "lower_better", "best_committable_value": "15"}]}
    path = "/api/v1/sla/templates"
    revision = client.get(path, headers=flow.headers).json()["revision"]
    headers = {**flow.headers, "If-Match": str(revision), "Idempotency-Key": str(uuid4())}
    first = client.post(path, headers=headers, json=payload)
    second = client.post(path, headers=headers, json=payload)
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert len(client.get(path, headers=flow.headers).json()["items"]) == 1
    assert client.post(path, headers=headers, json={**payload, "name": "换内容"}).status_code == 409
    assert client.post(path, headers={**headers, "Idempotency-Key": str(uuid4())}, json=payload).status_code == 409
    assert client.post(path, headers=flow.headers, json=payload).status_code == 428


def test_template_token_cannot_use_conflicting_fixed_unit(client):
    flow = SlaFlow(client)
    flow.template(body="一级故障响应时限为{{P1.response}}小时。")
    flow.bind()
    flow.confirm()
    result = flow.write("/sla/commitment", {}, expected=409)
    assert result["code"] == "SLA_COMMITMENT_BLOCKED"
    assert any(issue["code"] == "SLA_VARIABLE_UNIT_MISMATCH" for issue in result["details"]["issues"])


def test_confirmed_template_creation_requires_this_request_reason(client):
    flow = SlaFlow(client)
    payload = {"name": "缺本次依据的合成模板", "body_text": "{{P1.response}}分钟。", "status": "confirmed",
               "variables": [{"var_key": "P1.response", "label": "一级故障响应时限", "group": "response",
                              "value_type": "integer", "default_value": "30", "unit": "minute",
                              "compare_direction": "lower_better", "best_committable_value": "15"}]}
    path = "/api/v1/sla/templates"
    before = client.get(path, headers=flow.headers).json()
    for reason in (None, "   "):
        request_payload = payload if reason is None else {**payload, "reason": reason}
        result = client.post(path, json=request_payload, headers={**flow.headers, "If-Match": str(before["revision"]),
                             "Idempotency-Key": str(uuid4())})
        assert result.status_code == 409, result.text
        assert result.json()["code"] == "REVIEW_REASON_REQUIRED"
        assert client.get(path, headers=flow.headers).json() == before


@pytest.mark.parametrize("initial_status", ["pending", "confirmed"])
def test_template_confirmation_cannot_reuse_saved_reason(client, initial_status):
    flow = SlaFlow(client)
    payload = {"name": "检查旧依据的合成模板", "body_text": "{{P1.response}}分钟。", "status": initial_status,
               "reason": "旧草稿或上一次确认的依据，不属于本次确认。", "variables": [{
                   "var_key": "P1.response", "label": "一级故障响应时限", "group": "response",
                   "value_type": "integer", "default_value": "30", "unit": "minute",
                   "compare_direction": "lower_better", "best_committable_value": "15"}]}
    path = "/api/v1/sla/templates"
    revision = client.get(path, headers=flow.headers).json()["revision"]
    created = client.post(path, json=payload, headers={**flow.headers, "If-Match": str(revision),
                          "Idempotency-Key": str(uuid4())})
    assert created.status_code == 200, created.text
    template = created.json()["item"]
    before = client.get(path, headers=flow.headers).json()
    for extra in ({}, {"reason": "   "}):
        result = flow.patch_template(template["id"], {"status": "confirmed", **extra}, expected=409)
        assert result["code"] == "REVIEW_REASON_REQUIRED"
        assert client.get(path, headers=flow.headers).json() == before
    confirmed = flow.patch_template(template["id"], {"status": "confirmed", "reason": "本次重新逐项核对的合成依据。"})["item"]
    assert confirmed["status"] == "confirmed"
    assert confirmed["reason"] == "本次重新逐项核对的合成依据。"
