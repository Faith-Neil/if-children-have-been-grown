# 为什么有这个文件：通过真实HTTP路由验证后端demo的权限、并发写入和Word输出。
# 它解决什么问题：避免成功页面掩盖公司越权、旧锁写入、重复版本或失效检查导出。
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
from zipfile import ZipFile
import xml.etree.ElementTree as ET

import pytest
from fastapi.testclient import TestClient

from icg_demo.main import create_app
from icg_demo.adapters import MemoryRepository, seed_state


VALID_CONTENT = "本项目采用双机热备并定期巡检，备份验证结果保留完整记录。"
CHAPTER = "alpha-tech"


class MutableClock:
    def __init__(self):
        self.value = 1_800_000_000.0

    def __call__(self):
        return self.value


@pytest.fixture
def clock():
    return MutableClock()


@pytest.fixture
def client(clock):
    with TestClient(create_app(clock=clock)) as actual_client:
        yield actual_client


def login(client, account="alpha-editor"):
    response = client.post("/api/v1/auth/login", json={"username": account, "password": "X_2026"})
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": "Bearer " + token}


def get_chapter(client, headers, chapter=CHAPTER):
    response = client.get(f"/api/chapters/{chapter}", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def acquire(client, headers, chapter=CHAPTER, reason=None):
    response = client.post(
        f"/api/chapters/{chapter}/lock", headers=headers,
        json={"takeover_reason": reason},
    )
    assert response.status_code == 200, response.text
    assert response.json()["lease_token"]
    assert response.json()["expires_at"]
    return response.json()["lease_token"]


def submit(client, headers, lease, content=VALID_CONTENT, key="submission-1", base=None):
    if base is None:
        base = get_chapter(client, headers)["revision"]
    return client.post(
        f"/api/chapters/{CHAPTER}/versions", headers=headers,
        json={"lease_token": lease, "base_revision": base, "content": content,
              "idempotency_key": key},
    )


def snapshot(client, headers):
    chapter = get_chapter(client, headers)
    versions = client.get(f"/api/chapters/{CHAPTER}/versions", headers=headers)
    audit = client.get(f"/api/chapters/{CHAPTER}/audit", headers=headers)
    assert versions.status_code == audit.status_code == 200
    return chapter, versions.json()["versions"], audit.json()["events"]


def checked_export(client, headers, lease):
    saved = submit(client, headers, lease)
    assert saved.status_code == 200, saved.text
    check = client.post(f"/api/chapters/{CHAPTER}/checks", headers=headers, json={})
    assert check.status_code == 200, check.text
    assert check.json()["passed"] is True, check.text
    exported = client.post(
        f"/api/chapters/{CHAPTER}/exports", headers=headers,
        json={"check_id": check.json()["id"]},
    )
    assert exported.status_code == 200, exported.text
    return check.json(), exported.json()


def test_authentication_boundary_without_demo_routes(client):
    # 演示账号列表与免密登录已移除。
    assert client.get("/api/demo/accounts").status_code == 404
    assert client.post("/api/demo/login", json={"account_id": "alpha-manager"}).status_code in (404, 405)
    wrong = client.post("/api/v1/auth/login", json={"username": "alpha-manager", "password": "wrong"})
    assert wrong.status_code == 401
    assert client.get("/api/projects").status_code == 401
    assert client.get(f"/api/chapters/{CHAPTER}").status_code == 401
    assert client.get("/api/projects", headers={"Authorization": "Bearer invalid"}).status_code == 401


def test_companies_cannot_see_each_others_projects_or_chapters(client):
    alpha, beta = login(client), login(client, "beta-editor")
    alpha_projects = client.get("/api/projects", headers=alpha).json()["projects"]
    beta_projects = client.get("/api/projects", headers=beta).json()["projects"]
    assert "alpha-project" in {project["id"] for project in alpha_projects}
    assert "beta-project" not in {project["id"] for project in alpha_projects}
    assert "beta-project" in {project["id"] for project in beta_projects}
    assert "alpha-project" not in {project["id"] for project in beta_projects}
    for headers, foreign_project, foreign_chapter in [
        (alpha, "beta-project", "beta-tech"),
        (beta, "alpha-project", CHAPTER),
    ]:
        assert client.get(f"/api/projects/{foreign_project}/chapters", headers=headers).status_code in {403, 404}
        assert client.get(f"/api/chapters/{foreign_chapter}", headers=headers).status_code in {403, 404}
    chapters = client.get("/api/projects/alpha-project/chapters", headers=alpha)
    assert chapters.status_code == 200
    assert {chapter["id"] for chapter in chapters.json()["chapters"]} >= {"alpha-tech", "alpha-business"}


@pytest.mark.parametrize("operation,payload", [
    ("lock", {"takeover_reason": None}),
    ("suggestions", {"instruction": "补充说明"}),
    ("checks", {}),
])
def test_viewer_cannot_call_write_operations(client, operation, payload):
    viewer = login(client, "alpha-viewer")
    assert client.get(f"/api/chapters/{CHAPTER}", headers=viewer).status_code == 200
    assert client.post(f"/api/chapters/{CHAPTER}/{operation}", headers=viewer, json=payload).status_code == 403


def test_viewer_cannot_save_drafts_or_versions(client):
    editor = login(client)
    viewer = login(client, "alpha-viewer")
    lease = acquire(client, editor)
    revision = get_chapter(client, editor)["revision"]
    draft = client.put(f"/api/chapters/{CHAPTER}/draft", headers=viewer,
                       json={"lease_token": lease, "base_revision": revision,
                             "sequence": 1, "content": "无权写入"})
    version = submit(client, viewer, lease, base=revision)
    assert draft.status_code == version.status_code == 403


def test_editor_cannot_take_over_manager_lock(client):
    manager, editor = login(client, "alpha-manager"), login(client)
    manager_lease = acquire(client, manager)
    before = snapshot(client, manager)
    refused = client.post(f"/api/chapters/{CHAPTER}/lock", headers=editor,
                          json={"takeover_reason": "尝试编辑者越权接管"})
    assert refused.status_code == 403
    assert snapshot(client, manager) == before
    assert submit(client, manager, manager_lease).status_code == 200


@pytest.mark.parametrize("reason", [None, "", "   "])
def test_manager_takeover_requires_reason_and_failure_preserves_editor_lease(client, reason):
    editor, manager = login(client), login(client, "alpha-manager")
    lease = acquire(client, editor)
    before = snapshot(client, editor)
    refused = client.post(f"/api/chapters/{CHAPTER}/lock", headers=manager,
                          json={"takeover_reason": reason})
    assert refused.status_code in {400, 409, 422}
    assert snapshot(client, editor) == before
    assert submit(client, editor, lease).status_code == 200


def test_other_members_see_lock_holder_name(client):
    editor, manager = login(client), login(client, "alpha-manager")
    acquire(client, editor)
    lock = get_chapter(client, manager)["lock"]
    assert lock["owner_id"] == "alpha-editor"
    assert lock["owner_name"]


def test_takeover_invalidates_old_lease_without_partial_write(client):
    editor, manager = login(client), login(client, "alpha-manager")
    old_lease = acquire(client, editor)
    new_lease = acquire(client, manager, reason="负责人已授权处理当前章节")
    assert old_lease != new_lease
    before = snapshot(client, manager)
    rejected = submit(client, editor, old_lease, content="旧租约不得覆盖正文")
    assert rejected.status_code == 423
    assert snapshot(client, manager) == before
    assert submit(client, manager, new_lease).status_code == 200


def test_expired_lease_rejects_save_and_renew(client, clock):
    headers = login(client)
    lease = acquire(client, headers)
    clock.value += 10_000
    # 重新登录排除会话有效期影响，只验证原章节租约确实已经过期。
    headers = login(client)
    before = snapshot(client, headers)
    rejected = submit(client, headers, lease)
    renewed = client.post(f"/api/chapters/{CHAPTER}/lock/renew", headers=headers,
                          json={"lease_token": lease})
    assert rejected.status_code == 423
    assert renewed.status_code == 423
    assert snapshot(client, headers) == before
    assert acquire(client, headers) != lease


def test_release_and_renew_require_actual_lease(client):
    headers = login(client)
    lease = acquire(client, headers)
    assert client.post(f"/api/chapters/{CHAPTER}/lock/renew", headers=headers,
                       json={"lease_token": "wrong-lease"}).status_code == 423
    assert client.post(f"/api/chapters/{CHAPTER}/lock/release", headers=headers,
                       json={"lease_token": "wrong-lease"}).status_code == 423
    assert client.post(f"/api/chapters/{CHAPTER}/lock/renew", headers=headers,
                       json={"lease_token": lease}).status_code == 200
    assert client.post(f"/api/chapters/{CHAPTER}/lock/release", headers=headers,
                       json={"lease_token": lease}).status_code == 200
    assert submit(client, headers, lease).status_code == 423


def test_old_heartbeat_and_release_cannot_destroy_manager_takeover(client):
    editor, manager = login(client), login(client, "alpha-manager")
    old_lease = acquire(client, editor)
    new_lease = acquire(client, manager, reason="演示负责人接管")
    before = snapshot(client, manager)
    for operation in ["renew", "release"]:
        response = client.post(f"/api/chapters/{CHAPTER}/lock/{operation}", headers=editor,
                               json={"lease_token": old_lease})
        assert response.status_code == 423
        assert snapshot(client, manager) == before
    assert submit(client, manager, new_lease).status_code == 200


def test_concurrent_sessions_cannot_both_acquire_same_chapter(client):
    # 同一账号的两个浏览器也不能继承对方会话的租约。
    sessions = [login(client), login(client)]

    def take_lock(headers):
        return client.post(f"/api/chapters/{CHAPTER}/lock", headers=headers,
                           json={"takeover_reason": None})

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(take_lock, sessions))
    assert sorted(response.status_code for response in results) == [200, 423]
    winner = next(i for i, response in enumerate(results) if response.status_code == 200)
    lease = results[winner].json()["lease_token"]
    before = snapshot(client, sessions[winner])
    rejected = submit(client, sessions[1 - winner], lease)
    assert rejected.status_code == 423
    assert snapshot(client, sessions[winner]) == before
    assert submit(client, sessions[winner], lease).status_code == 200


def test_out_of_order_draft_is_rejected_without_mutation(client):
    headers = login(client)
    lease = acquire(client, headers)
    revision = get_chapter(client, headers)["revision"]
    new = client.put(f"/api/chapters/{CHAPTER}/draft", headers=headers,
                     json={"lease_token": lease, "base_revision": revision,
                           "sequence": 2, "content": "第二次草稿，不被旧请求覆盖。"})
    assert new.status_code == 200, new.text
    before = snapshot(client, headers)
    old = client.put(f"/api/chapters/{CHAPTER}/draft", headers=headers,
                     json={"lease_token": lease, "base_revision": revision,
                           "sequence": 1, "content": "延迟到达的第一次草稿"})
    assert old.status_code == 409
    assert snapshot(client, headers) == before


def test_stale_revision_rejects_both_draft_and_version_atomically(client):
    headers = login(client)
    lease = acquire(client, headers)
    original_revision = get_chapter(client, headers)["revision"]
    assert submit(client, headers, lease, base=original_revision).status_code == 200
    before = snapshot(client, headers)
    stale_version = submit(client, headers, lease, key="stale-version", base=original_revision)
    stale_draft = client.put(f"/api/chapters/{CHAPTER}/draft", headers=headers,
                             json={"lease_token": lease, "base_revision": original_revision,
                                   "sequence": 1, "content": "旧版本草稿"})
    assert stale_version.status_code == stale_draft.status_code == 409
    assert snapshot(client, headers) == before


def test_idempotent_version_does_not_duplicate_version_or_audit(client):
    headers = login(client)
    lease = acquire(client, headers)
    base = get_chapter(client, headers)["revision"]
    before = snapshot(client, headers)
    first = submit(client, headers, lease, key="same-request", base=base)
    assert first.status_code == 200, first.text
    accepted = snapshot(client, headers)
    assert len(accepted[1]) == len(before[1]) + 1
    second = submit(client, headers, lease, key="same-request", base=base)
    assert second.status_code == 200, second.text
    assert second.json() == first.json()
    assert snapshot(client, headers) == accepted
    conflicting = submit(client, headers, lease, key="same-request", base=base,
                         content="相同幂等键却改变了提交内容。")
    assert conflicting.status_code == 409
    assert snapshot(client, headers) == accepted


def test_injected_model_provider_is_used_without_automatic_writing(clock):
    class SpyProvider:
        def __init__(self):
            self.calls = []

        def suggest(self, instruction, content):
            self.calls.append((instruction, content))
            return "可替换模型接口返回的建议，尚未写入正文。"

    provider = SpyProvider()
    with TestClient(create_app(model_provider=provider, clock=clock)) as client:
        headers = login(client)
        before = snapshot(client, headers)
        result = client.post(f"/api/chapters/{CHAPTER}/suggestions", headers=headers,
                             json={"instruction": "请补充边界说明"})
        assert result.status_code == 200, result.text
        assert result.json()["content"].startswith("可替换模型接口")
        assert result.json()["base_revision"] == before[0]["revision"]
        assert provider.calls == [("请补充边界说明", before[0]["content"])]
        # 建议可记录审计，但不得创建正式版本或改正文。
        after = snapshot(client, headers)
        assert after[0] == before[0]
        assert after[1] == before[1]


def test_default_suggestions_are_explicit_demo_and_do_not_write(client):
    headers = login(client)
    before = snapshot(client, headers)
    result = client.post(f"/api/chapters/{CHAPTER}/suggestions", headers=headers,
                         json={"instruction": "补充巡检说明"})
    assert result.status_code == 200
    assert result.json()["provider"] == "demo"
    assert result.json()["is_real_model"] is False
    assert snapshot(client, headers)[:2] == before[:2]


def test_provider_failure_does_not_leave_partial_write(clock):
    class FailingProvider:
        def suggest(self, instruction, content):
            raise RuntimeError("synthetic provider failure")

    with TestClient(create_app(model_provider=FailingProvider(), clock=clock),
                    raise_server_exceptions=False) as client:
        headers = login(client)
        before = snapshot(client, headers)
        response = client.post(f"/api/chapters/{CHAPTER}/suggestions", headers=headers,
                               json={"instruction": "失败建议"})
        assert response.status_code in {500, 502, 503}
        assert snapshot(client, headers) == before


def test_replacement_repository_and_failure_after_operation_roll_back(clock):
    class ReplaceableRepository:
        mode = "test-injected"

        def __init__(self):
            state = seed_state()
            state.chapters[CHAPTER].content = "替换存储中的合成正文。"
            self.delegate = MemoryRepository(state)
            self.fail_next = False

        def read(self):
            return self.delegate.read()

        def transaction(self, operation):
            if not self.fail_next:
                return self.delegate.transaction(operation)
            self.fail_next = False

            def fail_after_operation(state):
                operation(state)
                raise RuntimeError("synthetic database failure before commit")

            return self.delegate.transaction(fail_after_operation)

    repository = ReplaceableRepository()
    with TestClient(create_app(repository=repository, clock=clock),
                    raise_server_exceptions=False) as client:
        headers = login(client)
        assert get_chapter(client, headers)["content"] == "替换存储中的合成正文。"
        lease = acquire(client, headers)
        before = snapshot(client, headers)
        repository.fail_next = True
        failed = submit(client, headers, lease, key="rollback-request")
        assert failed.status_code == 500
        assert "synthetic database" not in failed.text
        assert snapshot(client, headers) == before
        # 故障重试成功，说明幂等记录也没有随着失败留下部分提交。
        retried = submit(client, headers, lease, key="rollback-request")
        assert retried.status_code == 200, retried.text
        after = snapshot(client, headers)
        assert len(after[1]) == len(before[1]) + 1
        assert len(after[2]) == len(before[2]) + 1


@pytest.mark.parametrize("content", ["", "   ", "设备参数待补，验收指标待补充。",
                                    "参数[待补]。", "商务条款【待补】。"])
def test_empty_or_placeholder_content_cannot_pass_check_or_export(client, content):
    headers = login(client, "alpha-manager")
    lease = acquire(client, headers)
    saved = submit(client, headers, lease, content=content)
    assert saved.status_code == 200, saved.text
    checked = client.post(f"/api/chapters/{CHAPTER}/checks", headers=headers, json={})
    assert checked.status_code == 200
    assert checked.json()["passed"] is False
    assert checked.json()["issues"]
    export = client.post(f"/api/chapters/{CHAPTER}/exports", headers=headers,
                         json={"check_id": checked.json()["id"]})
    assert export.status_code in {400, 409, 422}


def test_export_is_real_docx_and_cannot_cross_company_or_skip_authentication(client):
    headers = login(client, "alpha-manager")
    lease = acquire(client, headers)
    checked, exported = checked_export(client, headers, lease)
    download = client.get(exported["download_url"], headers=headers)
    assert download.status_code == 200
    assert "wordprocessingml.document" in download.headers["content-type"]
    assert exported["filename"].endswith(".docx")
    with ZipFile(BytesIO(download.content)) as docx:
        assert {"[Content_Types].xml", "_rels/.rels", "word/document.xml"} <= set(docx.namelist())
        for filename in ["[Content_Types].xml", "_rels/.rels", "word/document.xml"]:
            ET.fromstring(docx.read(filename))
        document = ET.fromstring(docx.read("word/document.xml"))
        text = "".join(document.itertext())
        assert VALID_CONTENT in text
    assert client.get(exported["download_url"]).status_code == 401
    assert client.get(exported["download_url"], headers=login(client, "beta-editor")).status_code in {403, 404}
    viewer = login(client, "alpha-viewer")
    assert client.post(f"/api/chapters/{CHAPTER}/exports", headers=viewer,
                       json={"check_id": checked["id"]}).status_code == 403


def test_new_committed_version_invalidates_previous_check_and_export_download(client):
    headers = login(client, "alpha-manager")
    lease = acquire(client, headers)
    checked, exported = checked_export(client, headers, lease)
    revision = get_chapter(client, headers)["revision"]
    changed = submit(client, headers, lease, key="after-check",
                     content=VALID_CONTENT + "新增一项承诺。", base=revision)
    assert changed.status_code == 200, changed.text
    stale_export = client.post(f"/api/chapters/{CHAPTER}/exports", headers=headers,
                               json={"check_id": checked["id"]})
    assert stale_export.status_code == 409
    assert client.get(exported["download_url"], headers=headers).status_code == 409


def test_uncommitted_draft_never_enters_exported_docx(client):
    headers = login(client, "alpha-manager")
    lease = acquire(client, headers)
    checked, exported = checked_export(client, headers, lease)
    committed = get_chapter(client, headers)
    draft_only = "仅草稿中的新承诺，未经提交不得出现在Word。"
    draft = client.put(f"/api/chapters/{CHAPTER}/draft", headers=headers,
                       json={"lease_token": lease, "base_revision": committed["revision"],
                             "sequence": 1, "content": draft_only})
    assert draft.status_code == 200, draft.text
    after = get_chapter(client, headers)
    assert after["revision"] == committed["revision"]
    assert after["content"] == committed["content"]
    another_export = client.post(f"/api/chapters/{CHAPTER}/exports", headers=headers,
                                 json={"check_id": checked["id"]})
    assert another_export.status_code == 200, another_export.text
    for item in [exported, another_export.json()]:
        downloaded = client.get(item["download_url"], headers=headers)
        assert downloaded.status_code == 200
        with ZipFile(BytesIO(downloaded.content)) as docx:
            text = "".join(ET.fromstring(docx.read("word/document.xml")).itertext())
            assert VALID_CONTENT in text
            assert draft_only not in text


def test_docx_preserves_special_characters_and_rejects_invalid_xml_input(client):
    headers = login(client, "alpha-manager")
    lease = acquire(client, headers)
    content = "技术说明：A&B < C > D，中文与引号\"保留\"。\n第二行正文。"
    assert submit(client, headers, lease, content=content).status_code == 200
    before = snapshot(client, headers)
    invalid = submit(client, headers, lease, key="invalid-xml", content="非法控制符" + chr(0))
    assert invalid.status_code == 422
    assert snapshot(client, headers) == before
    checked = client.post(f"/api/chapters/{CHAPTER}/checks", headers=headers, json={})
    assert checked.status_code == 200 and checked.json()["passed"] is True
    exported = client.post(f"/api/chapters/{CHAPTER}/exports", headers=headers,
                           json={"check_id": checked.json()["id"]})
    assert exported.status_code == 200
    downloaded = client.get(exported.json()["download_url"], headers=headers)
    assert downloaded.status_code == 200
    with ZipFile(BytesIO(downloaded.content)) as docx:
        document = ET.fromstring(docx.read("word/document.xml"))
        paragraphs = document.findall(".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p")
        exported_lines = ["".join(paragraph.itertext()) for paragraph in paragraphs]
        assert all(line in exported_lines for line in content.splitlines())
