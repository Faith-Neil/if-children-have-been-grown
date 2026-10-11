# 为什么有这个文件：独立验证章节模型实际收到的事实、证据、变量和来源快照。
# 它解决什么问题：防止只增加提示词却漏传真实项目值，或让旧候选、坏变量和越权资料继续写入。

from copy import deepcopy
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from icg_demo.adapters import MemoryRepository, seed_state
from icg_demo.main import create_app
from test_reference_flow import ProjectFlow, login, word_text
from test_sla import SlaFlow


CONTEXT_TENDER = (
    "合成招标文件：写作输入验收\n招标编号：SYNTH-CONTEXT\n"
    "投标截止时间：2026-12-31T17:00:00+08:00\n服务期限：12个月\n"
    "服务地点：未选择的可选地点MARKER\n"
    "★技术要求：一级故障响应时限不得超过30分钟。\f"
    "商务要求：提供有效企业资质证明。"
)


class CapturingProvider:
    name = "context-regression-spy"
    is_real_model = False
    is_local = True

    def __init__(self):
        self.calls = []
        self.result = "合成章节候选，仅用于验证输入与人工核对。"
        self.on_call = None

    def suggest(self, instruction, content):
        self.calls.append((instruction, content))
        if self.on_call:
            self.on_call()
        return self.result


@pytest.fixture
def context_client():
    provider = CapturingProvider()
    repository = MemoryRepository(seed_state())
    with TestClient(create_app(repository=repository, model_provider=provider)) as client:
        yield client, provider, repository


def prepare_context(client, repository, *, sla=False):
    """通过真实解析、证据挂接和经理确认准备本章；必备标记作为合成数据预置。"""
    flow = ProjectFlow(client, account="alpha-manager").reviewed(CONTEXT_TENDER)
    chapters = flow.state()["chapters"]
    evidence = flow.library(name="当前公司资质上下文MARKER", content="仅本项目计划证据内容MARKER。")
    for row in flow.state()["requirements"]:
        chapter = next(item for item in chapters if item["volume"] == row["volume"])
        flow.write("/requirements/" + row["id"], {
            "chapter_id": chapter["id"], "response": "经人工核对，按本项目要求响应。",
            "evidence_ids": [evidence["id"]],
        }, "PATCH")
    selected = next(item for item in flow.state()["facts"] if item["key"] == "服务期限")
    required = next(item for item in flow.state()["facts"] if item["key"] == "招标编号")
    omitted = next(item for item in flow.state()["facts"] if item["key"] == "服务地点")

    def mark_required(state):
        state.workflows[flow.id]["facts"][required["id"]]["required"] = True
        state.projects[flow.id].revision += 1
    repository.transaction(mark_required)

    sla_flow = None
    if sla:
        sla_flow = SlaFlow(client, project_id=flow.id)
        sla_flow.template()
        requirement = next(row for row in flow.state()["requirements"] if row["volume"] == "technical")
        flow.write("/requirements/" + requirement["id"], {"category": "sla"}, "PATCH")
        sla_flow.write("/sla/values/P1.response", {
            "project_value": "20", "project_unit": "minute", "requirement_id": requirement["id"],
            "tender_required_value": "30", "tender_unit": "minute", "reason": "对照合成响应时限确认20分钟。",
        }, "PATCH")
        sla_flow.confirm()
    flow.write("/parse/confirm", {})
    plan = {"chapters": [{"id": chapter["id"], "title": chapter["title"], "volume": chapter["volume"],
                           "fact_ids": [selected["id"]] if chapter["volume"] == "technical" else [],
                           "writing_points": "写明实际措施，逐项回应本章要求。",
                           "target_length": 550} for chapter in chapters]}
    flow.confirm_plan(plan)
    technical = next(chapter for chapter in flow.state()["chapters"] if chapter["volume"] == "technical")
    return {"flow": flow, "chapter": technical, "plan": plan, "selected": selected,
            "required": required, "omitted": omitted, "evidence": evidence, "sla": sla_flow}


def preview(client, setup):
    flow, chapter = setup["flow"], setup["chapter"]
    response = client.get(flow.path + f"/chapters/{chapter['id']}/writing-input", headers=flow.headers)
    assert response.status_code == 200, response.text
    return response.json()


def generate(setup, expected=200):
    return setup["flow"].write("/generate", {"chapter_ids": [setup["chapter"]["id"]]}, expected=expected)


def suggest(client, setup, instruction="请改善本章表达并保留所有事实变量。"):
    return client.post(f"/api/chapters/{setup['chapter']['id']}/suggestions", headers=setup["flow"].headers,
                       json={"instruction": instruction})


def patch_library(client, flow, evidence_id, payload):
    listing = client.get("/api/v1/library", headers=flow.headers).json()
    response = client.patch("/api/v1/library/" + evidence_id, json=payload, headers={
        **flow.headers, "If-Match": str(listing["revision"]), "Idempotency-Key": str(uuid4())})
    assert response.status_code == 200, response.text
    return response.json()


def test_provider_receives_selected_optional_all_required_and_actual_sla(context_client):
    client, provider, repository = context_client
    setup = prepare_context(client, repository, sla=True)
    before = preview(client, setup)
    assert before["ready"] is True and before["source_scope"] == "whole_chapter"
    snapshot = before["input_snapshot"]
    facts = {item["id"]: item for item in snapshot["facts"]}
    expected = {fact["id"] for fact in setup["flow"].state()["facts"] if fact["required"]}
    expected.add(setup["selected"]["id"])
    assert set(facts) == expected
    assert setup["omitted"]["id"] not in facts
    sla_fact = facts["sla:P1.response"]
    assert sla_fact["value"] == "20" and sla_fact["unit"] == "minute"
    assert sla_fact["variable"] == "{{sla:P1.response}}" and sla_fact["source_type"] == "sla"
    assert snapshot["plan"]["fact_ids"] == [setup["selected"]["id"]]
    assert snapshot["plan"]["target_length"] == 550
    assert snapshot["plan"]["confirmed_by"] == "alpha-manager"
    assert snapshot["plan"]["confirmed_at"]
    assert any(item["id"] == setup["omitted"]["id"] and item["reason"] for item in snapshot["omitted_inputs"])
    result = generate(setup)
    candidate = result["chapters"][0]["candidate"]
    assert candidate["source_scope"] == "whole_chapter"
    assert candidate["input_snapshot"]["facts"] == snapshot["facts"]
    assert candidate["input_snapshot"]["plan"] == snapshot["plan"]
    assert len(provider.calls) == 1
    instruction, content = provider.calls[0]
    assert "{{sla:P1.response}}" in content and "20" in content
    assert "{{fact:" + setup["selected"]["id"] + "}}" in content
    assert setup["required"]["value"] in content
    assert setup["omitted"]["value"] not in content
    assert setup["evidence"]["content"] in content
    assert setup["evidence"]["id"] in content
    assert "变量" in instruction
    assert setup["flow"].state()["chapters"][0]["content"] == setup["chapter"]["content"]


def test_suggestion_uses_same_real_context_without_writing_body(context_client):
    client, provider, repository = context_client
    setup = prepare_context(client, repository, sla=True)
    expected = preview(client, setup)["input_snapshot"]
    response = suggest(client, setup)
    assert response.status_code == 200, response.text
    actual = response.json()
    assert actual["source_scope"] == "whole_chapter"
    for field in ("facts", "evidence", "requirements", "plan", "official_content"):
        assert actual["input_snapshot"][field] == expected[field]
    assert actual["input_fingerprint"] == setup["flow"].state()["input_fingerprint"]
    assert setup["omitted"]["value"] not in provider.calls[0][1]
    assert setup["flow"].state()["chapters"][0]["content"] == setup["chapter"]["content"]


def test_editor_cannot_confirm_plan_and_readonly_preview_is_nonmutating(context_client):
    client, provider, repository = context_client
    setup = prepare_context(client, repository)
    flow = setup["flow"]
    before = repository.read()
    editor = login(client, "alpha-editor")
    response = client.post(flow.path + "/plan", json=setup["plan"], headers={
        **editor, "If-Match": str(flow.state()["revision"]), "Idempotency-Key": str(uuid4())})
    assert response.status_code == 403, response.text
    viewer = login(client, "alpha-viewer")
    result = client.get(flow.path + f"/chapters/{setup['chapter']['id']}/writing-input", headers=viewer)
    assert result.status_code == 200, result.text
    assert repository.read().projects[flow.id] == before.projects[flow.id]
    assert provider.calls == []


@pytest.mark.parametrize("account", ["alpha-manager", "beta-manager"])
def test_other_projects_fact_cannot_be_selected(context_client, account):
    client, provider, repository = context_client
    setup = prepare_context(client, repository)
    other = ProjectFlow(client, account=account).reviewed(CONTEXT_TENDER)
    foreign_fact = next(item for item in other.state()["facts"] if item["key"] == "服务期限")
    plan = deepcopy(setup["plan"])
    plan["chapters"][0]["fact_ids"] = [foreign_fact["id"]]
    result = setup["flow"].confirm_plan(plan, expected=409)
    assert result["code"] == "FACT_NOT_FOUND"
    assert provider.calls == []


@pytest.mark.parametrize("required", [False, True])
def test_selected_or_required_pending_fact_blocks_confirmation_and_generation(context_client, required):
    client, provider, repository = context_client
    setup = prepare_context(client, repository)
    flow = setup["flow"]
    fact_id = setup["required" if required else "selected"]["id"]

    def pending_imported_fact(state):
        state.workflows[flow.id]["facts"][fact_id]["status"] = "pending"
        state.projects[flow.id].revision += 1
    repository.transaction(pending_imported_fact)
    actual = preview(client, setup)
    assert actual["ready"] is False
    assert any(item["code"] == "FACT_NOT_READY" and item["fact_id"] == fact_id for item in actual["issues"])
    assert flow.confirm_plan(setup["plan"], expected=409)["code"] == "FACT_NOT_READY"
    assert generate(setup, expected=409)["code"] in ("PLAN_STALE", "FACT_NOT_READY", "GENERATION_CONTEXT_INVALID")
    assert provider.calls == []


def test_duplicate_fact_selection_is_rejected_instead_of_silently_repeated(context_client):
    client, provider, repository = context_client
    setup = prepare_context(client, repository)
    plan = deepcopy(setup["plan"])
    plan["chapters"][0]["fact_ids"] = [setup["selected"]["id"], setup["selected"]["id"]]
    assert setup["flow"].confirm_plan(plan, expected=422)["code"] == "DUPLICATE_FACT"
    assert provider.calls == []


def test_preview_and_generation_reject_foreign_project_chapter(context_client):
    client, provider, repository = context_client
    setup = prepare_context(client, repository)
    other = ProjectFlow(client, account="alpha-manager")
    foreign_chapter = other.state()["chapters"][0]
    response = client.get(setup["flow"].path + f"/chapters/{foreign_chapter['id']}/writing-input",
                          headers=setup["flow"].headers)
    assert response.status_code == 404, response.text
    result = setup["flow"].write("/generate", {"chapter_ids": [foreign_chapter["id"]]}, expected=404)
    assert result["code"] == "NOT_FOUND" and provider.calls == []


@pytest.mark.parametrize("change", ["response", "mapping", "evidence"])
def test_matrix_plan_changes_require_reconfirmation_and_preserve_body(context_client, change):
    client, provider, repository = context_client
    setup = prepare_context(client, repository)
    flow = setup["flow"]
    original = {item["id"]: item["content"] for item in flow.state()["chapters"]}
    generate(setup)
    row = next(item for item in flow.state()["requirements"] if item["chapter_id"] == setup["chapter"]["id"])
    payload = {"response": "新核对后的响应内容。"}
    if change == "mapping":
        payload = {"chapter_id": None}
    elif change == "evidence":
        payload = {"evidence_ids": []}
    flow.write("/requirements/" + row["id"], payload, "PATCH")
    assert flow.state()["plan_confirmed"] is False
    assert {item["id"]: item["content"] for item in flow.state()["chapters"]} == original
    blocked = generate(setup, expected=409)
    assert blocked["code"] in ("PLAN_NOT_CONFIRMED", "PLAN_STALE")
    if change == "mapping":
        flow.write("/requirements/" + row["id"], {"chapter_id": setup["chapter"]["id"]}, "PATCH")
    flow.confirm_plan(setup["plan"])
    assert generate(setup)["chapters"][0]["candidate"] is not None


def test_official_body_change_invalidates_candidate_but_does_not_unconfirm_plan(context_client):
    client, provider, repository = context_client
    setup = prepare_context(client, repository)
    flow = setup["flow"]
    candidate = generate(setup)["chapters"][0]["candidate"]
    flow.commit(setup["chapter"]["id"], "合成经理手动提交的新正文。")
    state = flow.state()
    assert state["plan_confirmed"] is True
    assert state["input_fingerprint"] != candidate["input_fingerprint"]
    stale = next(item for item in state["chapters"] if item["id"] == setup["chapter"]["id"])["candidate"]
    assert stale["status"] == "stale"
    assert stale["base_revision"] == setup["chapter"]["revision"]
    assert stale["input_fingerprint"] != state["input_fingerprint"]
    assert generate(setup)["chapters"][0]["candidate"]["input_snapshot"]["official_content"] == "合成经理手动提交的新正文。"


@pytest.mark.parametrize("payload", [
    {"status": "pending"},
    {"valid_until": "2020-01-01", "status": "confirmed", "reason": "合成过期证据，仅用于测试。"},
    {"type": "history", "status": "confirmed", "reason": "此合成资料为历史参考，不作为证据。"},
])
def test_evidence_revalidated_before_provider_even_if_plan_flag_was_stale(context_client, payload):
    client, provider, repository = context_client
    setup = prepare_context(client, repository)
    patch_library(client, setup["flow"], setup["evidence"]["id"], payload)
    response = preview(client, setup)
    assert response["ready"] is False
    codes = {item["code"] for item in response["issues"]}
    assert codes & {"EVIDENCE_NOT_USABLE", "EVIDENCE_EXPIRED"}
    blocked = generate(setup, expected=409)
    assert blocked["code"] in ("PLAN_NOT_CONFIRMED", "PLAN_STALE", "GENERATION_CONTEXT_INVALID")
    assert provider.calls == []


def test_candidate_retains_historic_input_snapshot_after_source_change(context_client):
    client, provider, repository = context_client
    setup = prepare_context(client, repository)
    flow = setup["flow"]
    candidate = generate(setup)["chapters"][0]["candidate"]
    historic = deepcopy(candidate["input_snapshot"])
    row = next(item for item in flow.state()["requirements"] if item["chapter_id"] == setup["chapter"]["id"])
    flow.write("/requirements/" + row["id"], {"response": "合成来源变化后才写的新响应。"}, "PATCH")
    stored = repository.read().workflows[flow.id]["candidates"][setup["chapter"]["id"]]
    assert stored["input_snapshot"] == historic
    assert flow.state()["input_fingerprint"] != stored["input_fingerprint"]
    current = next(item for item in flow.state()["chapters"] if item["id"] == setup["chapter"]["id"])["candidate"]
    assert current["status"] == "stale" and current["input_snapshot"] == historic


@pytest.mark.parametrize("result,code", [
    ("未知事实{{fact:fact-not-in-this-project}}。", "FACT_VARIABLE_INVALID"),
    ("未知服务变量{{sla:NotKnown}}分钟。", "SLA_VARIABLE_UNKNOWN"),
    ("一级故障响应时限{{sla:P1.response}}小时。", "SLA_VARIABLE_UNIT_MISMATCH"),
])
def test_bad_provider_variable_output_is_rejected_without_body_or_candidate(context_client, result, code):
    client, provider, repository = context_client
    setup = prepare_context(client, repository, sla=True)
    before = repository.read()
    provider.result = result
    failure = generate(setup, expected=409)
    assert failure["code"] == code
    assert len(provider.calls) == 1
    after = repository.read()
    assert after.chapters[setup["chapter"]["id"]] == before.chapters[setup["chapter"]["id"]]
    assert after.workflows[setup["flow"].id]["candidates"] == before.workflows[setup["flow"].id]["candidates"]


def test_provider_cannot_drop_existing_fact_or_sla_tokens(context_client):
    client, provider, repository = context_client
    setup = prepare_context(client, repository, sla=True)
    text = ("服务期限{{fact:" + setup["selected"]["id"] + "}}。"
            "一级故障响应时限{{sla:P1.response}}分钟。")
    setup["flow"].commit(setup["chapter"]["id"], text)
    provider.result = "重新写成没有变量的20分钟和12个月。"
    result = generate(setup, expected=409)
    assert result["code"] == "FACT_VARIABLE_LOST"
    assert next(item for item in setup["flow"].state()["chapters"] if item["id"] == setup["chapter"]["id"])["content"] == text
    suggested = suggest(client, setup)
    assert suggested.status_code == 409, suggested.text
    assert suggested.json()["error"]["code"] == "FACT_VARIABLE_LOST"


def test_provider_cannot_reference_omitted_optional_fact(context_client):
    client, provider, repository = context_client
    setup = prepare_context(client, repository)
    provider.result = "服务地点{{fact:" + setup["omitted"]["id"] + "}}。"
    assert generate(setup, expected=409)["code"] == "FACT_VARIABLE_INVALID"


def test_generic_fact_variable_unit_conflict_is_rejected(context_client):
    client, provider, repository = context_client
    setup = prepare_context(client, repository)
    flow = setup["flow"]
    fact_id = setup["selected"]["id"]

    def numeric_unit_metadata(state):
        state.workflows[flow.id]["facts"][fact_id].update(value="12", unit="month")
        state.projects[flow.id].revision += 1
    repository.transaction(numeric_unit_metadata)
    flow.confirm_plan(setup["plan"])
    provider.result = "服务期限{{fact:" + fact_id + "}}小时。"
    assert generate(setup, expected=409)["code"] == "FACT_VARIABLE_UNIT_MISMATCH"
    assert flow.state()["chapters"][0]["content"] == setup["chapter"]["content"]


@pytest.mark.parametrize("suffix,code", [
    ("小时", "FACT_VARIABLE_UNIT_MISMATCH"),
    ("个月", "FACT_VARIABLE_UNIT_DUPLICATED"),
    ("month", "FACT_VARIABLE_UNIT_DUPLICATED"),
])
def test_parsed_value_with_embedded_unit_rejects_provider_suffix(context_client, suffix, code):
    client, provider, repository = context_client
    setup = prepare_context(client, repository)
    assert setup["selected"]["value"] == "12个月" and setup["selected"]["unit"] == ""
    provider.result = "服务期限{{fact:" + setup["selected"]["id"] + "}}" + suffix + "。"
    before = repository.read().chapters[setup["chapter"]["id"]]
    assert generate(setup, expected=409)["code"] == code
    assert repository.read().chapters[setup["chapter"]["id"]] == before


@pytest.mark.parametrize("suffix,code", [
    ("小时", "FACT_VARIABLE_UNIT_MISMATCH"),
    ("个月", "FACT_VARIABLE_UNIT_DUPLICATED"),
    ("month", "FACT_VARIABLE_UNIT_DUPLICATED"),
])
def test_real_parsed_fact_suffix_blocks_check_and_two_volume_export(context_client, suffix, code):
    client, _, _ = context_client
    flow = ProjectFlow(client).ready()
    state = flow.state()
    fact = next(item for item in state["facts"] if item["key"] == "服务期限")
    assert fact["value"] == "12个月" and fact["unit"] == ""
    chapter = next(item for item in state["chapters"] if item["volume"] == "technical")
    flow.commit(chapter["id"], "服务期限{{fact:" + fact["id"] + "}}" + suffix + "。")
    check = flow.write("/checks", {"volume": "all"})["check"]
    assert check["passed"] is False
    assert any(issue["code"] == code and issue["chapter_id"] == chapter["id"] for issue in check["issues"])
    assert flow.write("/exports", {"check_id": check["id"], "kind": "internal"}, expected=409)["code"] == "CHECK_FAILED"


def test_real_parsed_fact_with_embedded_unit_exports_once_without_guessing(context_client):
    client, _, _ = context_client
    flow = ProjectFlow(client).ready()
    state = flow.state()
    fact = next(item for item in state["facts"] if item["key"] == "服务期限")
    chapter = next(item for item in state["chapters"] if item["volume"] == "technical")
    flow.commit(chapter["id"], "服务期限{{fact:" + fact["id"] + "}}。")
    _, exported = flow.checked_export()
    url = next(item["download_url"] for item in exported["volumes"] if item["volume"] == "technical")
    downloaded = client.get(url, headers=flow.headers)
    assert downloaded.status_code == 200
    content = word_text(downloaded.content)
    assert "服务期限12个月。" in content
    assert "{{fact:" not in content and "个月个月" not in content


def test_embedded_value_with_matching_explicit_unit_is_not_appended_twice(context_client):
    from icg_demo.generation_context import resolve_fact_variables
    client, _, repository = context_client
    setup = prepare_context(client, repository)
    fact = setup["selected"]
    def with_unit(state):
        state.workflows[setup["flow"].id]["facts"][fact["id"]]["unit"] = "month"
    repository.transaction(with_unit)
    text = "服务期限{{fact:" + fact["id"] + "}}。"
    assert resolve_fact_variables(repository.read(), setup["flow"].id, text) == "服务期限12个月。"


@pytest.mark.parametrize("instruction", ["把一级故障响应时限改成15分钟。", "将项目事实中的服务期限改成24个月。"])
def test_source_change_instruction_is_rejected_before_model(context_client, instruction):
    client, provider, repository = context_client
    setup = prepare_context(client, repository, sla=True)
    response = suggest(client, setup, instruction)
    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "FACT_SOURCE_CHANGE_REQUIRED"
    assert provider.calls == []


def test_source_changes_during_provider_call_discard_result(context_client):
    client, provider, repository = context_client
    setup = prepare_context(client, repository)
    flow = setup["flow"]
    row = next(item for item in flow.state()["requirements"] if item["chapter_id"] == setup["chapter"]["id"])

    def concurrent_update():
        def edit(state):
            state.workflows[flow.id]["requirements"][row["id"]]["response"] = "模型调用期间的合成来源修改。"
            state.projects[flow.id].revision += 1
        repository.transaction(edit)
    provider.on_call = concurrent_update
    failure = generate(setup, expected=409)
    assert failure["code"] == "VERSION_CONFLICT"
    assert next(item for item in flow.state()["chapters"] if item["id"] == setup["chapter"]["id"])["candidate"] is None
    assert provider.calls


def test_standalone_old_demo_suggestion_keeps_existing_provider_contract(context_client):
    client, provider, repository = context_client
    headers = login(client, "alpha-editor")
    before = client.get("/api/chapters/alpha-tech", headers=headers).json()
    response = client.post("/api/chapters/alpha-tech/suggestions", headers=headers,
                           json={"instruction": "请补充合成说明。"})
    assert response.status_code == 200, response.text
    assert provider.calls == [("请补充合成说明。", before["content"])]
    assert client.get("/api/chapters/alpha-tech", headers=headers).json()["content"] == before["content"]


def test_writing_input_evidence_uses_shanghai_deadline_date(context_client):
    client, provider, repository = context_client
    setup = prepare_context(client, repository)
    flow = setup["flow"]
    flow.write("", {"deadline": "2026-12-31T18:00:00Z"}, "PATCH")
    patch_library(client, flow, setup["evidence"]["id"], {
        "valid_until": "2026-12-31", "status": "confirmed", "reason": "合成跨日有效期反例"})
    assert any(issue["code"] == "EVIDENCE_EXPIRED" for issue in preview(client, setup)["issues"])
    generate(setup, expected=409)
    assert provider.calls == []
    patch_library(client, flow, setup["evidence"]["id"], {
        "valid_until": "2027-01-01", "status": "confirmed", "reason": "有效至北京时间投标日"})
    flow.confirm_plan(setup["plan"])
    assert preview(client, setup)["ready"] is True
    generate(setup)
    assert len(provider.calls) == 1


def test_same_key_with_conflicting_confirmed_values_blocks_input(context_client):
    client, provider, repository = context_client
    setup = prepare_context(client, repository)
    def duplicate(state):
        facts = state.workflows[setup["flow"].id]["facts"]
        facts["fact-conflicting-synthetic"] = {**deepcopy(facts[setup["selected"]["id"]]),
            "id": "fact-conflicting-synthetic", "value": "24个月", "required": True}
        state.projects[setup["flow"].id].revision += 1
    repository.transaction(duplicate)
    assert any(issue["code"] == "FACT_CONFLICT" for issue in preview(client, setup)["issues"])
    assert setup["flow"].confirm_plan(setup["plan"], expected=409)["code"] == "FACT_CONFLICT"
    assert provider.calls == []


def test_required_non_sla_fact_confirmation_is_manager_only(context_client):
    client, provider, repository = context_client
    setup = prepare_context(client, repository)
    flow = setup["flow"]
    before = flow.state()
    response = client.patch(flow.path + '/facts/' + setup["required"]["id"],
        json={"status": "confirmed", "reason": "普通成员不得代确认必备事实"}, headers={
            **login(client, 'alpha-editor'), 'If-Match': str(before['revision']),
            'Idempotency-Key': str(uuid4())})
    assert response.status_code == 403 and response.json()['code'] == 'PROJECT_LEAD_REQUIRED'
    assert flow.state() == before and provider.calls == []
