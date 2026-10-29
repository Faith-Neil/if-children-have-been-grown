# 为什么有这个文件：复现主流程中正常演示容易遗漏的安全和恢复边界。
# 它解决什么问题：防止敏感正文绕过本地模型限制、坏文件卡死项目、时区误判和过期候选或资料继续被采用。

from concurrent.futures import ThreadPoolExecutor
from threading import Event
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from icg_demo.domain import DomainError
from icg_demo.main import create_app
from icg_demo.parsing import LocalTextParser
from test_reference_flow import ProjectFlow, login


class SpyModel:
    name = "synthetic-spy"
    is_real_model = True

    def __init__(self, local=False):
        self.is_local = local
        self.calls = []

    def suggest(self, instruction, content):
        self.calls.append((instruction, content))
        return "合成模型候选，仍须人工核对。"


@pytest.mark.parametrize("local,expected", [(False, 409), (True, 200)])
def test_sensitive_model_gate_covers_both_generation_routes(local, expected):
    model = SpyModel(local)
    with TestClient(create_app(model_provider=model)) as client:
        flow = ProjectFlow(client).ready()
        flow.write("", {"sensitive": True}, "PATCH")
        flow.confirm_plan()
        chapter = flow.state()["chapters"][0]
        response = client.post(f"/api/chapters/{chapter['id']}/suggestions", headers=flow.headers,
                               json={"instruction": "依据合成正文提出建议"})
        assert response.status_code == expected, response.text
        generated = flow.write("/generate", {}, expected=expected)
        if local:
            assert len(model.calls) == 3  # 旧建议一次，新两册各一次。
            assert response.json()["input_fingerprint"] == flow.state()["input_fingerprint"]
        else:
            assert response.json()["error"]["code"] == "LOCAL_MODEL_REQUIRED"
            assert generated["code"] == "LOCAL_MODEL_REQUIRED"
            assert model.calls == []


def test_sensitive_project_rejects_provider_with_undeclared_location():
    class UnknownProvider:
        def __init__(self):
            self.calls = 0

        def suggest(self, instruction, content):
            self.calls += 1
            return "没有声明模型位置的合成适配器。"

    model = UnknownProvider()
    with TestClient(create_app(model_provider=model)) as client:
        flow = ProjectFlow(client).ready()
        flow.write("", {"sensitive": True}, "PATCH")
        chapter = flow.state()["chapters"][0]
        result = client.post(f"/api/chapters/{chapter['id']}/suggestions", headers=flow.headers,
                             json={"instruction": "合成建议"})
        assert result.status_code == 409 and model.calls == 0
        assert flow.write("/generate", {}, expected=409)["code"] == "LOCAL_MODEL_REQUIRED"


@pytest.fixture
def client():
    with TestClient(create_app()) as actual:
        yield actual


def test_failed_file_can_be_removed_and_project_recovered(client):
    flow = ProjectFlow(client).ready()
    check, exported = flow.checked_export()
    original_ids = {r["source"]["file_id"] for r in flow.state()["requirements"]}
    bad = flow.upload(b"not a valid DOCX", "broken.docx")
    flow.write("/parse", {"file_ids": [bad["id"]]}, expected=422)
    assert flow.write("/parse/confirm", {}, expected=409)["code"] == "PARSE_INCOMPLETE"
    result = flow.write("/files/" + bad["id"], {"reason": "误传了损坏的合成测试文件。"}, "DELETE")
    assert result["deleted_file_id"] == bad["id"]
    state = flow.state()
    assert {r["source"]["file_id"] for r in state["requirements"]} == original_ids
    assert all(f["id"] != bad["id"] for f in state["files"])
    assert state["parse_confirmed"] is False and state["plan_confirmed"] is False
    assert next(c for c in state["checks"] if c["id"] == check["id"])["status"] == "stale"
    # 旧批次标“已过期”但保留下载当时的快照（PRD §5.9.1 规则 13，APP-M2-T202）
    stale = client.get(exported["volumes"][0]["download_url"], headers=flow.headers)
    assert stale.status_code == 200 and stale.headers["X-ICG-Export-Status"] == "stale"
    flow.write("/parse/confirm", {})
    flow.confirm_plan({"chapters": [{"id": c["id"], "title": c["title"], "volume": c["volume"]}
                                     for c in flow.state()["chapters"]]})
    flow.checked_export()
    state = client.app.state.service.repository.read()
    deletion = next(e for e in state.audit if e["action"] == "file.delete:" + bad["id"])
    assert deletion["details"]["reason"] == "误传了损坏的合成测试文件。"


def test_file_removal_permissions_version_replay_and_provenance(client):
    flow = ProjectFlow(client).ready()
    source_file = flow.state()["files"][0]["id"]
    assert flow.write("/files/" + source_file, {"reason": "不能删除有来源的文件。"}, "DELETE", 409)["code"] == "FILE_IN_USE"
    pending = flow.upload("技术要求：尚未解析的合成文件。".encode(), "pending.txt")
    path = flow.path + "/files/" + pending["id"]
    revision = flow.state()["revision"]
    headers = {**flow.headers, "If-Match": str(revision), "Idempotency-Key": str(uuid4())}
    assert client.request("DELETE", path, headers=flow.headers, json={"reason": "误传"}).status_code == 428
    assert client.request("DELETE", path, headers=headers, json={"reason": "  "}).status_code == 422
    assert client.request("DELETE", path, headers={**headers, **login(client, "alpha-viewer")}, json={"reason": "误传"}).status_code == 403
    assert client.request("DELETE", path, headers={**headers, **login(client, "beta-editor")}, json={"reason": "误传"}).status_code == 404
    first = client.request("DELETE", path, headers=headers, json={"reason": "误传"})
    assert first.status_code == 200, first.text
    assert client.request("DELETE", path, headers=headers, json={"reason": "误传"}).json() == first.json()
    assert client.request("DELETE", path, headers=headers, json={"reason": "不同理由"}).status_code == 409
    assert flow.write("/files/" + pending["id"], {"reason": "已经删除"}, "DELETE", 404)["code"] == "NOT_FOUND"


def test_file_with_existing_sources_cannot_be_removed_after_reparse_failure():
    class FailAgainParser:
        def __init__(self):
            self.calls = 0

        def parse(self, filename, content):
            self.calls += 1
            if self.calls > 1:
                raise DomainError(502, "PARSER_UNAVAILABLE", "合成解析服务临时失败。")
            return LocalTextParser().parse(filename, content)

    with TestClient(create_app(parser_provider=FailAgainParser())) as client:
        flow = ProjectFlow(client).ready()
        file_id = flow.state()["files"][0]["id"]
        flow.write("/parse", {}, expected=502)
        assert flow.state()["files"][0]["status"] == "failed"
        assert flow.write("/files/" + file_id, {"reason": "有来源不能删"}, "DELETE", 409)["code"] == "FILE_IN_USE"


def test_removing_file_during_parse_rejects_old_snapshot():
    started, resume = Event(), Event()

    class PausedParser:
        def parse(self, filename, content):
            started.set()
            if not resume.wait(5):
                raise RuntimeError("test did not resume synthetic parser")
            return LocalTextParser().parse(filename, content)

    with TestClient(create_app(parser_provider=PausedParser())) as client:
        flow = ProjectFlow(client)
        uploaded = flow.upload()
        headers = {**flow.headers, "If-Match": str(flow.state()["revision"]), "Idempotency-Key": str(uuid4())}
        with ThreadPoolExecutor(max_workers=1) as pool:
            parsing = pool.submit(client.post, flow.path + "/parse", headers=headers, json={})
            try:
                assert started.wait(5)
                flow.write("/files/" + uploaded["id"], {"reason": "解析中发现上传文件错误。"}, "DELETE")
            finally:
                resume.set()
            result = parsing.result(timeout=5)
        assert result.status_code == 409, result.text
        assert result.json()["code"] == "VERSION_CONFLICT"
        assert flow.state()["files"] == [] and flow.state()["requirements"] == []


def set_deadline(flow, project_value, fact_value):
    flow.write("", {"deadline": project_value}, "PATCH")
    fact = next(f for f in flow.state()["facts"] if f["key"] == "投标截止时间")
    flow.write("/facts/" + fact["id"], {"value": fact_value, "status": "confirmed"}, "PATCH")
    flow.write("/parse/confirm", {})
    flow.confirm_plan({"chapters": [{"id": c["id"], "title": c["title"], "volume": c["volume"]}
                                     for c in flow.state()["chapters"]]})


@pytest.mark.parametrize("fact_value,matching", [
    ("2026-12-31T00:30:00+08:00", True),
    ("2026-12-30T16:30:00Z", True),
    ("2026-12-31T00:30:00", True),
    ("2026-12-31", True),
    ("2026-12-31T03:30:00+08:00", False),
    ("2026-12-30", False),
])
def test_deadline_fact_uses_same_instant_or_explicit_date_only(client, fact_value, matching):
    flow = ProjectFlow(client).ready()
    set_deadline(flow, "2026-12-30T16:30:00Z", fact_value)
    check = flow.write("/checks", {})["check"]
    assert (not any(issue["code"] == "PROJECT_FACT_MISMATCH" for issue in check["issues"])) is matching


def library_patch(client, flow, item_id, payload):
    revision = client.get("/api/v1/library", headers=flow.headers).json()["revision"]
    return client.patch("/api/v1/library/" + item_id, json=payload,
                        headers={**flow.headers, "If-Match": str(revision), "Idempotency-Key": str(uuid4())})


def test_evidence_date_covers_local_deadline_not_previous_utc_day(client):
    flow = ProjectFlow(client).ready()
    set_deadline(flow, "2026-12-30T16:30:00Z", "2026-12-31T00:30:00+08:00")
    evidence = client.get("/api/v1/library", headers=flow.headers).json()["items"][0]
    updated = library_patch(client, flow, evidence["id"], {"valid_until": "2026-12-30", "status": "confirmed", "reason": "核对合成证据截止日。"})
    assert updated.status_code == 200, updated.text
    check = flow.write("/checks", {})["check"]
    assert any(issue["code"] == "EVIDENCE_EXPIRED" for issue in check["issues"])
    updated = library_patch(client, flow, evidence["id"], {"valid_until": "2026-12-31", "status": "confirmed", "reason": "有效至北京时间当天。"})
    assert updated.status_code == 200, updated.text
    # 来源改变后确认方案，再单独验证有效期恢复；旧方案不能沿用。
    flow.confirm_plan()
    assert flow.write("/checks", {})["check"]["passed"] is True


@pytest.mark.parametrize("change", ["response", "fact", "evidence", "project", "content"])
def test_candidate_input_changes_mark_history_stale(client, change):
    flow = ProjectFlow(client).ready()
    chapter = next(c for c in flow.state()["chapters"] if c["volume"] == "technical")
    flow.write("/generate", {"chapter_ids": [chapter["id"]]})
    before = flow.state()
    candidate = next(c for c in before["chapters"] if c["id"] == chapter["id"])["candidate"]
    assert candidate["input_fingerprint"] == before["input_fingerprint"]
    if change == "response":
        row = next(r for r in before["requirements"] if r["volume"] == "technical")
        flow.write("/requirements/" + row["id"], {"response": "修改后的合成响应。"}, "PATCH")
    elif change == "fact":
        fact = next(f for f in before["facts"] if f["key"] == "服务期限")
        flow.write("/facts/" + fact["id"], {"value": "24个月"}, "PATCH")
    elif change == "evidence":
        evidence = client.get("/api/v1/library", headers=flow.headers).json()["items"][0]
        assert library_patch(client, flow, evidence["id"], {"content": "新合成证明内容。"}).status_code == 200
    elif change == "project":
        flow.write("", {"name": "项目输入名称变化"}, "PATCH")
    else:
        flow.commit(chapter["id"], "不同的合成已提交正文。")
    after = flow.state()
    assert after["input_fingerprint"] != candidate["input_fingerprint"]
    stale = next(c for c in after["chapters"] if c["id"] == chapter["id"])["candidate"]
    assert stale["status"] == "stale" and stale["input_snapshot"] == candidate["input_snapshot"]


def test_old_suggestion_rejects_project_change_during_model_call():
    class MutatingModel(SpyModel):
        def suggest(self, instruction, content):
            def change(state):
                state.projects[self.project_id].name = "合成并发修改"
            self.repository.transaction(change)
            return super().suggest(instruction, content)

    model = MutatingModel(local=True)
    with TestClient(create_app(model_provider=model)) as client:
        flow = ProjectFlow(client).ready()
        model.project_id = flow.id
        model.repository = client.app.state.service.repository
        chapter = flow.state()["chapters"][0]
        result = client.post(f"/api/chapters/{chapter['id']}/suggestions", headers=flow.headers, json={"instruction": "合成修改"})
        assert result.status_code == 409, result.text
        assert result.json()["error"]["code"] == "VERSION_CONFLICT"
        assert flow.state()["chapters"][0]["content"] == chapter["content"]


@pytest.mark.parametrize("field,value", [("name", "新合成资料名称"), ("type", "performance"),
                                         ("content", "改变后尚未人工核对。"), ("valid_until", "2028-12-31")])
def test_material_evidence_change_clears_previous_confirmation(client, field, value):
    flow = ProjectFlow(client).ready()
    evidence = client.get("/api/v1/library", headers=flow.headers).json()["items"][0]
    result = library_patch(client, flow, evidence["id"], {field: value})
    assert result.status_code == 200, result.text
    item = result.json()["item"]
    assert item["status"] == "pending" and item["usable_as_evidence"] is False
    check = flow.write("/checks", {})["check"]
    assert any(issue["code"] == "EVIDENCE_NOT_USABLE" for issue in check["issues"])


def test_material_change_explicit_reconfirmation_requires_new_review_reason(client):
    flow = ProjectFlow(client).ready()
    evidence = client.get("/api/v1/library", headers=flow.headers).json()["items"][0]
    before = client.get("/api/v1/library", headers=flow.headers).json()
    result = library_patch(client, flow, evidence["id"], {"content": "明确重新核对的合成内容。", "status": "confirmed"})
    assert result.status_code == 409 and result.json()["code"] == "REVIEW_REASON_REQUIRED"
    assert client.get("/api/v1/library", headers=flow.headers).json() == before
    result = library_patch(client, flow, evidence["id"], {"content": "明确重新核对的合成内容。", "status": "confirmed", "reason": "本次已对照合成原件逐项复核。"})
    assert result.status_code == 200, result.text
    assert result.json()["item"]["status"] == "confirmed"
    assert result.json()["item"]["reason"] == "本次已对照合成原件逐项复核。"
