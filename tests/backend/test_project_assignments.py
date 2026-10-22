# 为什么有这个文件：通过真实路由验证成员、分册与章节权限，以及逐章确认和交接的边界。
# 它解决什么问题：防止隐藏按钮却仍能越权、无关章节被一起退回、旧锁或重复请求继续写入。

from copy import deepcopy
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from icg_demo.adapters import MemoryRepository, seed_state
from icg_demo.domain import Account
from icg_demo.main import create_app
from test_reference_flow import ProjectFlow, login, word_text
from test_generation_context import CapturingProvider


@pytest.fixture
def setup():
    repository, provider = MemoryRepository(seed_state()), CapturingProvider()
    with TestClient(create_app(repository=repository, model_provider=provider)) as client:
        flow = ProjectFlow(client).ready()
        members = [
            {"user_id": "alpha-manager", "project_role": "lead", "volumes": ["technical", "business"]},
            {"user_id": "alpha-tech", "project_role": "writer", "volumes": ["technical"]},
            {"user_id": "alpha-business", "project_role": "writer", "volumes": ["business"]},
            {"user_id": "alpha-editor", "project_role": "writer", "volumes": ["technical", "business"]},
            {"user_id": "alpha-viewer", "project_role": "readonly", "volumes": ["technical", "business"]},
        ]
        team = {"members": members, "volumes": [{"volume": "technical", "owner_id": "alpha-tech"},
                   {"volume": "business", "owner_id": "alpha-manager"}], "assembly_owner_id": "alpha-editor", "reason": "合成人员分工验收"}
        flow.write("/team", team, "PUT")
        chapters = {c["volume"]: c["id"] for c in flow.state()["chapters"]}
        flow.write("/chapters/" + chapters["technical"] + "/assignment", {"assignee_id": "alpha-tech"}, "PATCH")
        flow.write("/chapters/" + chapters["business"] + "/assignment", {"assignee_id": "alpha-business"}, "PATCH")
        for identity in chapters.values():
            flow.write("/chapters/" + identity + "/plan/confirm", {})
        yield client, flow, chapters, team, repository, provider


def acting(client, flow, actor, route, payload, method="POST", expected=200, headers=None):
    response = client.request(method, flow.path + route, json=payload, headers=headers or {
        **login(client, actor), "If-Match": str(flow.state()["revision"]), "Idempotency-Key": str(uuid4())})
    assert response.status_code == expected, response.text
    return response.json()


def chapter_state(flow, identity):
    return next(c for c in flow.state()["chapters"] if c["id"] == identity)


@pytest.mark.parametrize("actor", ["alpha-editor", "alpha-viewer", "beta-editor"])
def test_only_company_manager_can_create_project(setup, actor):
    client, *_ = setup
    result = client.post("/api/projects", headers=login(client, actor), json={"name": "不得由编写人新建"})
    assert result.status_code == 403
    assert (result.json().get("code") or result.json().get("error", {}).get("code")) == "PROJECT_CREATE_FORBIDDEN"


@pytest.mark.parametrize("actor", ["alpha-outsider-manager", "beta-manager"])
def test_nonmembers_cannot_see_any_existing_resource_or_jobs(setup, actor):
    client, flow, chapters, _, _, _ = setup
    _, output = flow.checked_export()
    data = flow.state()
    outsider = login(client, actor)
    urls = [flow.path + "/workspace", flow.path + "/team", flow.path + "/checks",
            "/api/projects/" + flow.id + "/chapters", "/api/chapters/" + chapters["technical"],
            "/api/chapters/" + chapters["technical"] + "/versions",
            "/api/chapters/" + chapters["technical"] + "/audit",
            flow.path + "/chapters/" + chapters["technical"] + "/writing-input",
            data["files"][0]["download_url"], data["files"][0]["download_url"] + "/preview",
            output["volumes"][0]["download_url"]]
    for url in urls:
        assert client.get(url, headers=outsider).status_code == 404, url
    assert flow.id not in {p["id"] for p in client.get("/api/projects", headers=outsider).json()["projects"]}
    assert flow.id not in {j["project_id"] for j in client.get("/api/v1/jobs", headers=outsider).json()["jobs"]}


@pytest.mark.parametrize("actor", ["alpha-tech", "alpha-business", "alpha-editor", "alpha-viewer"])
def test_only_project_lead_can_manage_team_or_sources(setup, actor):
    client, flow, _, team, repository, _ = setup
    before = repository.read()
    for route, payload, method in [("/team", team, "PUT"), ("", {"name": "越权改项目"}, "PATCH"),
                                    ("/parse/confirm", {}, "POST"), ("/parse", {}, "POST")]:
        acting(client, flow, actor, route, payload, method, expected=403)
    assert repository.read().projects == before.projects
    assert repository.read().project_teams == before.project_teams


@pytest.mark.parametrize("change,code", [
    ("last_lead", "LAST_PROJECT_LEAD_REQUIRED"), ("editor_lead", "PROJECT_LEAD_COMPANY_ROLE_REQUIRED"),
    ("viewer_writer", "MEMBER_ROLE_NOT_WRITABLE"), ("viewer_owner", "ASSIGNEE_NOT_WRITABLE"),
    ("outsider_owner", "ASSIGNEE_NOT_WRITABLE"), ("cross_company", "NOT_FOUND"),
    ("wrong_volume", "ASSIGNEE_NOT_WRITABLE"), ("readonly_assembly", "ASSIGNEE_NOT_WRITABLE"),
    ("duplicate_member", "DUPLICATE_MEMBER")])
def test_team_rejects_invalid_roles_and_owners_atomically(setup, change, code):
    client, flow, _, original, repository, _ = setup
    team = deepcopy(original)
    if change == "last_lead":
        team["members"][0]["project_role"] = "writer"
    elif change == "editor_lead":
        team["members"][1].update(project_role="lead", volumes=["technical", "business"])
    elif change == "viewer_writer":
        team["members"][-1]["project_role"] = "writer"
    elif change == "viewer_owner":
        team["volumes"][0]["owner_id"] = "alpha-viewer"
    elif change == "outsider_owner":
        team["volumes"][0]["owner_id"] = "alpha-outsider-manager"
    elif change == "cross_company":
        team["members"][1]["user_id"] = "beta-editor"
    elif change == "wrong_volume":
        team["volumes"][0]["owner_id"] = "alpha-business"
    elif change == "readonly_assembly":
        team["assembly_owner_id"] = "alpha-viewer"
    else:
        team["members"].append(deepcopy(team["members"][1]))
    before = repository.read()
    result = acting(client, flow, "alpha-manager", "/team", team, "PUT", 409 if change == "last_lead" else 404 if change == "cross_company" else 422)
    assert result["code"] == code
    after = repository.read()
    assert (after.projects, after.project_teams, after.chapters, after.audit) == (before.projects, before.project_teams, before.chapters, before.audit)


def test_team_versions_and_receipts_are_not_unconditional(setup):
    client, flow, _, original, _, _ = setup
    team = deepcopy(original)
    team["members"].append({"user_id": "alpha-outsider-manager", "project_role": "writer", "volumes": []})
    headers = {**flow.headers, "If-Match": str(flow.state()["revision"]), "Idempotency-Key": str(uuid4())}
    first = acting(client, flow, "alpha-manager", "/team", team, "PUT", headers=headers)
    assert acting(client, flow, "alpha-manager", "/team", team, "PUT", headers=headers) == first
    changed = deepcopy(team)
    changed["members"][-1]["project_role"] = "readonly"
    assert acting(client, flow, "alpha-manager", "/team", changed, "PUT", 409, headers)["code"] == "IDEMPOTENCY_CONFLICT"
    stale = {**headers, "Idempotency-Key": str(uuid4())}
    assert acting(client, flow, "alpha-manager", "/team", changed, "PUT", 409, stale)["code"] == "VERSION_CONFLICT"


def test_permissions_include_current_scope_and_hide_candidate_accounts(setup):
    client, flow, chapters, _, _, _ = setup
    tech = client.get(flow.path + "/workspace", headers=login(client, "alpha-tech")).json()
    assert tech["team"]["available_accounts"] == []
    assert tech["permissions"]["check_volumes"] == ["technical"]
    assert not tech["permissions"]["manage_team"]
    assert next(c for c in tech["chapters"] if c["id"] == chapters["technical"])["permissions"]["manage_structure"]
    business = next(c for c in tech["chapters"] if c["id"] == chapters["business"])
    assert not any(business["permissions"].values())
    viewer = client.get(flow.path + "/workspace", headers=login(client, "alpha-viewer")).json()
    assert not any(v for k, v in viewer["permissions"].items() if isinstance(v, bool))
    assert all(not any(c["permissions"].values()) for c in viewer["chapters"])


def test_single_chapter_confirmation_and_unrelated_plan_edits_are_independent(setup):
    client, flow, chapters, _, _, provider = setup
    technical, business = chapters["technical"], chapters["business"]
    before_business = deepcopy(chapter_state(flow, business)["writing_input"])
    acting(client, flow, "alpha-tech", f"/chapters/{technical}/plan", {"writing_points": "只修改技术要点", "fact_ids": [], "target_length": 600}, "PATCH")
    assert not chapter_state(flow, technical)["writing_input"]["is_current"]
    assert chapter_state(flow, business)["writing_input"] == before_business
    acting(client, flow, "alpha-tech", "/generate", {"chapter_ids": [technical]}, expected=409)
    assert provider.calls == []
    acting(client, flow, "alpha-business", "/generate", {"chapter_ids": [business]})
    acting(client, flow, "alpha-tech", f"/chapters/{technical}/plan/confirm", {})
    confirmed = chapter_state(flow, technical)["writing_input"]
    assert confirmed["is_current"] and confirmed["confirmed_by"] == "alpha-tech" and confirmed["confirmed_at"]
    assert chapter_state(flow, business)["writing_input"] == before_business
    acting(client, flow, "alpha-tech", "/generate", {"chapter_ids": [technical]})


@pytest.mark.parametrize("route,payload,method", [
    ("plan", {"fact_ids": [], "writing_points": "不属于我的章", "target_length": 500}, "PATCH"),
    ("plan/confirm", {}, "POST"), ("assignment", {"assignee_id": "alpha-tech"}, "PATCH")])
def test_volume_owner_cannot_change_other_volume_chapter(setup, route, payload, method):
    client, flow, chapters, _, _, _ = setup
    acting(client, flow, "alpha-tech", f"/chapters/{chapters['business']}/{route}", payload, method, 403)


def test_assignee_cannot_smuggle_structure_into_plan_or_batch(setup):
    client, flow, chapters, _, _, _ = setup
    acting(client, flow, "alpha-business", f"/chapters/{chapters['business']}/plan", {
        "title": "不得偷偷改标题", "fact_ids": []}, "PATCH", 422)
    selected = chapter_state(flow, chapters["business"])
    acting(client, flow, "alpha-business", "/plan", {"scope": "business", "chapters": [
        {"id": selected["id"], "title": selected["title"], "volume": selected["volume"]}]}, expected=403)
    acting(client, flow, "alpha-business", "/generate", {"chapter_ids": [chapters["technical"]]}, expected=403)


def test_scoped_outline_preserves_other_volume_and_rejects_cross_volume(setup):
    client, flow, chapters, _, _, _ = setup
    business = deepcopy(chapter_state(flow, chapters["business"]))
    tech = chapter_state(flow, chapters["technical"])
    result = acting(client, flow, "alpha-tech", "/plan", {"scope": "technical", "chapters": [
        {"id": tech["id"], "title": "技术册新标题", "volume": "technical", "writing_points": "本册结构调整"}]})
    assert len(result["chapters"]) == 1
    assert chapter_state(flow, chapters["business"])["writing_input"] == business["writing_input"]
    assert chapter_state(flow, chapters["business"])["title"] == business["title"]
    acting(client, flow, "alpha-tech", "/plan", {"scope": "business", "chapters": [
        {"id": business["id"], "title": "越权", "volume": "business"}]}, expected=403)


def test_no_volume_owner_prevents_confirmation_but_preserves_history(setup):
    client, flow, chapters, original, _, _ = setup
    team = deepcopy(original)
    team["volumes"][0]["owner_id"] = None
    flow.write("/team", team, "PUT")
    historic = chapter_state(flow, chapters["technical"])["writing_input"]
    assert historic["confirmed_at"] and not historic["is_current"]
    result = acting(client, flow, "alpha-manager", f"/chapters/{chapters['technical']}/plan/confirm", {}, expected=403)
    assert result["code"] == "VOLUME_OWNER_REQUIRED"
    assert chapter_state(flow, chapters["business"])["writing_input"]["is_current"]


def test_unrelated_readonly_member_change_and_body_commit_keep_other_confirmation(setup):
    client, flow, chapters, original, _, _ = setup
    technical = deepcopy(chapter_state(flow, chapters["technical"])["writing_input"])
    team = deepcopy(original)
    team["members"][-1]["volumes"] = []
    flow.write("/team", team, "PUT")
    assert chapter_state(flow, chapters["technical"])["writing_input"] == technical
    flow.commit(chapters["business"], "只更新商务正文，不能使技术方案待确认。")
    assert chapter_state(flow, chapters["technical"])["writing_input"] == technical


def test_changed_relevant_matrix_and_evidence_only_invalidate_dependent_chapter(setup):
    client, flow, chapters, _, _, _ = setup
    business = deepcopy(chapter_state(flow, chapters["business"])["writing_input"])
    technical_row = next(r for r in flow.state()["requirements"] if r["volume"] == "technical")
    acting(client, flow, "alpha-tech", "/requirements/" + technical_row["id"], {"response": "技术负责人新响应"}, "PATCH")
    assert not chapter_state(flow, chapters["technical"])["writing_input"]["is_current"]
    assert chapter_state(flow, chapters["business"])["writing_input"] == business


def test_handoff_requires_reason_preserves_private_draft_and_revokes_old_lease(setup):
    client, flow, chapters, original, repository, _ = setup
    chapter_id = chapters["business"]
    writer = login(client, "alpha-business")
    path = "/api/chapters/" + chapter_id
    chapter = client.get(path, headers=writer).json()
    lease = client.post(path + "/lock", headers=writer, json={}).json()["lease_token"]
    payload = {"lease_token": lease, "base_revision": chapter["revision"], "sequence": 1,
               "input_fingerprint": flow.state()["input_fingerprint"], "content": "商务编写人的私有草稿保留标记"}
    assert client.put(path + "/draft", headers=writer, json=payload).status_code == 200
    before = repository.read()
    result = acting(client, flow, "alpha-manager", f"/chapters/{chapter_id}/assignment", {"assignee_id": "alpha-editor"}, "PATCH", 409)
    assert result["code"] == "HANDOFF_REASON_REQUIRED"
    assert repository.read().chapters == before.chapters
    acting(client, flow, "alpha-manager", f"/chapters/{chapter_id}/assignment", {"assignee_id": "alpha-editor", "reason": "按工作量交给另一个编写人，保留原稿供本人核对"}, "PATCH")
    after = repository.read()
    assert after.chapters[chapter_id].content == before.chapters[chapter_id].content
    assert after.chapters[chapter_id].versions == before.chapters[chapter_id].versions
    assert after.chapters[chapter_id].drafts == before.chapters[chapter_id].drafts
    assert after.chapters[chapter_id].lock is None
    assert client.put(path + "/draft", headers=writer, json=payload).status_code == 403
    assert client.post(path + "/lock/renew", headers=writer, json={"lease_token": lease}).status_code == 403
    assert client.get(path, headers=login(client, "alpha-editor")).json()["draft"] is None
    assert client.get(path, headers=writer).json()["draft"]["content"] == payload["content"]
    visible = flow.state()["team"]["handoffs"][-1]
    assert visible["preserved_draft_count"] == 1 and visible["revoked_lock_count"] == 1
    assert payload["content"] not in str(visible)
    assert client.request("DELETE", path + "/draft", headers=writer, json={"sequence": 2}).status_code == 409
    assert client.request("DELETE", path + "/draft", headers=writer, json={"sequence": 1}).json()["discarded"]


@pytest.mark.parametrize("operation", ["generate", "suggestion"])
def test_permission_change_during_model_call_leaves_no_partial_result(setup, operation):
    client, flow, chapters, original, repository, provider = setup
    actor = login(client, "alpha-business")
    before_audit = len(repository.read().audit)
    def revoke():
        team = deepcopy(original)
        team["members"] = [m for m in team["members"] if m["user_id"] != "alpha-business"]
        flow.write("/team", team, "PUT")
    provider.on_call = revoke
    if operation == "generate":
        response = client.post(flow.path + "/generate", json={"chapter_ids": [chapters["business"]]}, headers={
            **actor, "If-Match": str(flow.state()["revision"]), "Idempotency-Key": str(uuid4())})
    else:
        response = client.post("/api/chapters/" + chapters["business"] + "/suggestions", headers=actor, json={"instruction": "改善文字"})
    assert response.status_code == 404, response.text
    state = repository.read()
    assert state.workflows[flow.id]["candidates"].get(chapters["business"]) is None
    assert not any(e["action"] == "suggestion.generate" for e in state.audit[before_audit:])


def test_cached_generation_cannot_be_replayed_after_reassignment(setup):
    client, flow, chapters, _, _, provider = setup
    actor = login(client, "alpha-business")
    headers = {**actor, "If-Match": str(flow.state()["revision"]), "Idempotency-Key": str(uuid4())}
    payload = {"chapter_ids": [chapters["business"]]}
    assert client.post(flow.path + "/generate", headers=headers, json=payload).status_code == 200
    assert len(provider.calls) == 1
    flow.write(f"/chapters/{chapters['business']}/assignment", {"assignee_id": "alpha-editor"}, "PATCH")
    assert client.post(flow.path + "/generate", headers=headers, json=payload).status_code == 403
    assert len(provider.calls) == 1


def test_only_lead_or_volume_owner_can_check_and_export_matching_scope(setup):
    client, flow, chapters, _, _, _ = setup
    for actor in ("alpha-editor", "alpha-business"):
        acting(client, flow, actor, "/checks", {"volume": "all"}, expected=403)
        acting(client, flow, actor, "/checks", {"volume": "business"}, expected=403)
    acting(client, flow, "alpha-tech", "/checks", {"volume": "business"}, expected=403)
    acting(client, flow, "alpha-tech", "/checks", {"volume": "all"}, expected=403)
    check = acting(client, flow, "alpha-tech", "/checks", {"volume": "technical"})["check"]
    assert check["passed"]
    acting(client, flow, "alpha-tech", "/exports", {"check_id": check["id"], "kind": "internal"}, expected=403)
    exported = acting(client, flow, "alpha-tech", "/exports", {"check_id": check["id"], "volume": "technical", "kind": "internal"})["export"]
    assert [v["volume"] for v in exported["volumes"]] == ["technical"]
    output = client.get(exported["volumes"][0]["download_url"], headers=login(client, "alpha-editor"))
    assert output.status_code == 200
    text = word_text(output.content)
    assert "技术正文验收标记" in text and "商务正文验收标记" not in text
    assert client.get(flow.path + "/exports/" + exported["id"] + "/business", headers=flow.headers).status_code == 404


def test_removed_member_is_denied_all_old_paths_but_rejoining_restores_private_draft(setup):
    client, flow, chapters, original, repository, _ = setup
    identity = chapters["business"]
    actor = login(client, "alpha-business")
    old = client.get("/api/chapters/" + identity, headers=actor).json()
    token = client.post("/api/chapters/" + identity + "/lock", headers=actor, json={}).json()["lease_token"]
    saved = client.put("/api/chapters/" + identity + "/draft", headers=actor, json={"lease_token": token,
        "base_revision": old["revision"], "input_fingerprint": flow.state()["input_fingerprint"], "sequence": 1, "content": "原本人草稿"})
    assert saved.status_code == 200
    team = deepcopy(original)
    team["members"] = [m for m in team["members"] if m["user_id"] != "alpha-business"]
    team["reason"] = "退出项目，草稿保留，旧编辑权撤销"
    flow.write("/team", team, "PUT")
    for suffix in ("", "/versions", "/audit"):
        assert client.get("/api/chapters/" + identity + suffix, headers=actor).status_code == 404
    assert client.post("/api/chapters/" + identity + "/lock", headers=actor, json={}).status_code == 404
    assert client.request("DELETE", "/api/chapters/" + identity + "/draft", headers=actor, json={"sequence": 1}).status_code == 404
    assert repository.read().chapters[identity].drafts["alpha-business"].content == "原本人草稿"
    flow.write("/team", original, "PUT")
    assert client.get("/api/chapters/" + identity, headers=actor).json()["draft"]["content"] == "原本人草稿"


def test_scoped_batch_result_reports_whole_project_confirmation_honestly(setup):
    client, flow, chapters, _, _, _ = setup
    flow.write(f"/chapters/{chapters['business']}/plan", {"fact_ids": [], "target_length": 700}, "PATCH")
    tech = chapter_state(flow, chapters["technical"])
    result = acting(client, flow, "alpha-tech", "/plan", {"scope": "technical", "chapters": [
        {"id": tech["id"], "title": tech["title"], "volume": "technical"}]})
    assert result["plan_confirmed"] is False
    assert result["chapters"][0]["writing_input"]["is_current"] is True
    assert flow.state()["plan_confirmed"] is False


def test_confirmation_rejects_unmapped_matrix_and_parse_not_confirmed(setup):
    client, flow, chapters, _, _, _ = setup
    row = next(r for r in flow.state()["requirements"] if r["volume"] == "technical")
    flow.write("/requirements/" + row["id"], {"chapter_id": None}, "PATCH")
    result = acting(client, flow, "alpha-tech", f"/chapters/{chapters['technical']}/plan/confirm", {}, expected=409)
    assert result["code"] == "MATRIX_MAPPING_MISSING"
    flow.write("/requirements/" + row["id"], {"chapter_id": chapters["technical"], "status": "pending"}, "PATCH")
    result = acting(client, flow, "alpha-tech", f"/chapters/{chapters['technical']}/plan/confirm", {}, expected=409)
    assert result["code"] == "PARSE_NOT_CONFIRMED"


def test_project_fact_change_invalidates_selected_chapter_and_not_omitting_chapter(setup):
    client, flow, chapters, _, _, _ = setup
    fact = next(f for f in flow.state()["facts"] if f["key"] == "服务期限")
    flow.write(f"/chapters/{chapters['technical']}/plan", {"fact_ids": [fact["id"]], "target_length": 700}, "PATCH")
    flow.write(f"/chapters/{chapters['technical']}/plan/confirm", {})
    business = deepcopy(chapter_state(flow, chapters["business"])["writing_input"])
    flow.write("/facts/" + fact["id"], {"value": "24个月", "reason": "合成需求变化核对"}, "PATCH")
    assert not chapter_state(flow, chapters["technical"])["writing_input"]["is_current"]
    assert chapter_state(flow, chapters["business"])["writing_input"] == business


def test_old_formal_commit_receipt_cannot_be_used_after_losing_chapter_assignment(setup):
    client, flow, chapters, _, repository, _ = setup
    identity = chapters["business"]
    actor = login(client, "alpha-business")
    url = "/api/chapters/" + identity
    chapter = client.get(url, headers=actor).json()
    lease = client.post(url + "/lock", headers=actor, json={}).json()["lease_token"]
    payload = {"lease_token": lease, "base_revision": chapter["revision"], "content": "合成写入收据测试正文",
               "input_fingerprint": flow.state()["input_fingerprint"], "idempotency_key": str(uuid4())}
    first = client.post(url + "/versions", headers=actor, json=payload)
    assert first.status_code == 200
    flow.write(f"/chapters/{identity}/assignment", {"assignee_id": "alpha-editor", "reason": "写入后交接，旧权限立即失效"}, "PATCH")
    previous_versions = deepcopy(repository.read().chapters[identity].versions)
    assert client.post(url + "/versions", headers=actor, json=payload).status_code == 403
    assert repository.read().chapters[identity].versions == previous_versions


@pytest.mark.parametrize("operation", ["generate", "suggestion"])
def test_company_role_downgrade_during_model_call_is_rechecked(setup, operation):
    client, flow, chapters, _, repository, provider = setup
    actor = login(client, "alpha-business")
    def downgrade():
        def change(state):
            old = state.accounts["alpha-business"]
            state.accounts[old.id] = Account(old.id, old.name, old.company_id, "viewer")
        repository.transaction(change)
    provider.on_call = downgrade
    if operation == "generate":
        response = client.post(flow.path + "/generate", headers={**actor, "If-Match": str(flow.state()["revision"]),
            "Idempotency-Key": str(uuid4())}, json={"chapter_ids": [chapters["business"]]})
    else:
        response = client.post("/api/chapters/" + chapters["business"] + "/suggestions", headers=actor, json={"instruction": "改善文字"})
    assert response.status_code == 403
    assert repository.read().workflows[flow.id]["candidates"].get(chapters["business"]) is None


def test_bulk_generation_stops_before_another_call_when_source_changes(setup):
    client, flow, _, _, repository, provider = setup
    def change_source():
        flow.write("", {"name": "首章调用时资料发生变化"}, "PATCH")
    provider.on_call = change_source
    response = flow.write("/generate", {}, expected=409)
    assert response["code"] == "VERSION_CONFLICT"
    assert len(provider.calls) == 1
    assert repository.read().workflows[flow.id]["candidates"] == {}
