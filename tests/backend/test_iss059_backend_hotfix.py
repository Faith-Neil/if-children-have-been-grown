# 为什么有这个文件：登记 ISSUE-059 后端热修的复现与回归。
# 它解决什么问题：防止热路径指纹误过期、技术卷进度落库失败静默续写、知识库重建把 PDF 当 Word 上传、MySQL 开发种子账号热路径失效回归。

from __future__ import annotations

import base64
import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from fake_ragflow_v1 import FakeRagflowV1
from icg.app.main import create_app as create_icg_app
from icg.domain.domain import DemoState, Project
from icg.domain.input_snapshot import project_input_fingerprint
from icg.domain.kb_admin import _migration_upload
from icg_demo.main import create_app as create_demo_app
from test_generation_session import _active_session, _chapter, _finish, _frames, _ready, _start, _wait_status
from test_reference_flow import ProjectFlow, login

ADMIN = "alpha-data-admin"


def _state_with_company_rows(order):
    state = DemoState()
    state.projects["p"] = Project(id="p", name="合成项目", company_id="alpha")
    state.workflows["p"] = {"requirements": {}, "facts": {}, "conflicts": {}, "files": {}, "chapter_order": []}
    for item_id in order:
        state.library[item_id] = {"id": item_id, "company_id": "alpha", "name": item_id,
                                  "type": "qualification", "content": item_id, "status": "confirmed", "revision": 1}
        state.sla_templates[item_id] = {"id": item_id, "company_id": "alpha", "name": item_id,
                                        "status": "confirmed", "revision": 1, "variables": []}
    return state


def test_input_fingerprint_is_stable_for_entry_insertion_order():
    forward = _state_with_company_rows(("zz-order", "aa-order"))
    reverse = _state_with_company_rows(("aa-order", "zz-order"))
    assert list(forward.library) != list(reverse.library)
    assert project_input_fingerprint(forward, "p") == project_input_fingerprint(reverse, "p")


def test_mysql_seed_fallback_is_empty_in_production_mode(monkeypatch):
    from icg.infra.repositories.mysql_repository import MysqlConnectionRepository
    monkeypatch.setenv("ICG_ENV", "production")
    production = MysqlConnectionRepository("mysql+pymysql://unused:unused@127.0.0.1:1/unused")
    assert production._development_seed_accounts == {}
    monkeypatch.setenv("ICG_ENV", "development")
    development = MysqlConnectionRepository("mysql+pymysql://unused:unused@127.0.0.1:1/unused")
    assert "alpha-manager" in development._development_seed_accounts


def test_migration_upload_uses_pdf_name_and_type_for_converted_word_bytes():
    entry = {"name": "合成资料.doc", "content_type": "application/msword",
             "user_meta": {"original_filename": "合成资料.doc", "converted_from": "doc"}}
    assert _migration_upload(entry, b"%PDF-1.4\nconverted") == ("合成资料.pdf", "application/pdf", b"%PDF-1.4\nconverted")


@pytest.fixture()
def kb_client():
    fake = FakeRagflowV1()
    app = create_icg_app()
    kb = app.state.service.knowledge_base
    kb._client_factory = lambda state, company_id: fake.client()
    kb.background = False
    with TestClient(app) as client:
        yield client, fake


def _upload_converted_doc(client, fake, monkeypatch):
    import icg.domain.office_pdf as office_pdf
    monkeypatch.setattr(office_pdf, "prepare_for_deepdoc", lambda filename, data: ("合成资料.pdf", b"%PDF-1.4\nconverted"))
    admin = login(client, ADMIN)
    ensured = client.post("/api/v1/kb-admin/datasets/materials/ensure", headers=admin, json={})
    assert ensured.status_code == 200, ensured.text
    ole = bytes([0xD0, 0xCF, 0x11, 0xE0]) + b"legacy-doc"
    result = client.post("/api/v1/kb-admin/datasets/materials/documents", headers=admin,
                         json={"filename": "合成资料.doc", "content_base64": base64.b64encode(ole).decode(),
                               "content_type": "application/msword"})
    assert result.status_code == 200, result.text
    return admin, result.json()


def test_word_conversion_failure_is_422_on_upload(kb_client, monkeypatch):
    client, fake = kb_client
    import icg.domain.office_pdf as office_pdf
    monkeypatch.setattr(office_pdf, "prepare_for_deepdoc", lambda filename, data: "合成转换失败")
    admin = login(client, ADMIN)
    assert client.post("/api/v1/kb-admin/datasets/materials/ensure", headers=admin, json={}).status_code == 200
    ole = bytes([0xD0, 0xCF, 0x11, 0xE0]) + b"legacy-doc"
    result = client.post("/api/v1/kb-admin/datasets/materials/documents", headers=admin,
                         json={"filename": "合成资料.doc", "content_base64": base64.b64encode(ole).decode(),
                               "content_type": "application/msword"})
    assert result.status_code == 422 and result.json()["code"] == "FILE_CONVERSION_FAILED"
    assert fake.documents == {}


def test_rebuild_reuploads_converted_pdf_identity(kb_client, monkeypatch):
    client, fake = kb_client
    admin, doc = _upload_converted_doc(client, fake, monkeypatch)
    old_dataset = fake.documents[doc["document_id"]]["dataset_id"]
    rebuilt = client.post("/api/v1/kb-admin/datasets/materials/rebuild", headers=admin)
    assert rebuilt.status_code == 200, rebuilt.text
    new_dataset = rebuilt.json()["dataset_id"]
    migrated = fake.docs_in(new_dataset)[0]
    assert new_dataset != old_dataset and old_dataset not in fake.datasets
    assert migrated["name"] == "合成资料.pdf"
    assert migrated["raw"].startswith(b"%PDF-")
    assert migrated["meta_fields"]["converted_from"] == "doc"
    assert migrated["meta_fields"]["original_filename"] == "合成资料.doc"
    assert not migrated["name"].lower().endswith((".doc", ".docx"))


def test_rebuild_converts_legacy_word_bytes_before_reupload(kb_client, monkeypatch):
    client, fake = kb_client
    admin, doc = _upload_converted_doc(client, fake, monkeypatch)
    remote = fake.documents[doc["document_id"]]
    old_dataset = remote["dataset_id"]
    remote["raw"] = bytes([0xD0, 0xCF, 0x11, 0xE0]) + b"legacy-doc"
    rebuilt = client.post("/api/v1/kb-admin/datasets/materials/rebuild", headers=admin)
    assert rebuilt.status_code == 200, rebuilt.text
    migrated = fake.docs_in(rebuilt.json()["dataset_id"])[0]
    assert migrated["name"] == "合成资料.pdf" and migrated["raw"].startswith(b"%PDF-")
    assert old_dataset not in fake.datasets


def test_rebuild_conversion_failure_is_422_before_dataset_move(kb_client, monkeypatch):
    client, fake = kb_client
    admin, doc = _upload_converted_doc(client, fake, monkeypatch)
    remote = fake.documents[doc["document_id"]]
    old_dataset = remote["dataset_id"]
    # 模拟存量条目实际取回的是未转换 Word 原件；重建必须先补转换，失败则不能搬库。
    remote["raw"] = bytes([0xD0, 0xCF, 0x11, 0xE0]) + b"legacy-doc"
    import icg.domain.office_pdf as office_pdf
    monkeypatch.setattr(office_pdf, "prepare_for_deepdoc", lambda filename, data: "合成转换失败")
    result = client.post("/api/v1/kb-admin/datasets/materials/rebuild", headers=admin)
    assert result.status_code == 422, result.text
    assert result.json()["code"] == "FILE_CONVERSION_FAILED"
    assert old_dataset in fake.datasets
    assert len(fake.docs_in(old_dataset)) == 1


@pytest.fixture()
def generation_client():
    with TestClient(create_demo_app()) as client:
        yield client


def test_progress_persistence_failure_stops_generation_before_chapter_write(generation_client, monkeypatch):
    headers, project_id, workspace, model = _ready(generation_client)
    chapter_id = workspace["technical_outline"]["chapter_id"]
    before = _chapter(generation_client, headers, project_id, chapter_id)["content"]
    repository = generation_client.app.state.service.repository
    original = repository.update_job_progress
    calls = {"count": 0}

    def fail_after_begin(job_id, *args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            return original(job_id, *args, **kwargs)
        return False
    monkeypatch.setattr(repository, "update_job_progress", fail_after_begin)

    responses = []
    worker = _start(generation_client, headers, project_id, workspace, responses)
    job = _active_session(generation_client, headers, project_id)
    failed = _wait_status(generation_client, headers, job["id"], {"failed"}, timeout=15)
    assert "任务存储" in failed["message"] or "任务存储" in str(failed.get("error"))
    assert _chapter(generation_client, headers, project_id, chapter_id)["content"] == before
    events = _frames(_finish(worker, responses).text)
    kinds = [event["event"] for event in events]
    # SSE 心跳 session.live 可与终态事件穿插；语义断言：volume.failed 必达、
    # 其后没有任何正文/完成事件，且全程无 volume.done。
    assert "volume.failed" in kinds, kinds
    failed_at = len(kinds) - 1 - kinds[::-1].index("volume.failed")
    assert not any(event["event"] not in ("session.live",) for event in events[failed_at + 1:]), kinds
    assert not any(event["event"] == "volume.done" for event in events)


def test_initial_job_row_failure_marks_job_failed_and_does_not_start(generation_client, monkeypatch):
    headers, project_id, workspace, model = _ready(generation_client)
    repository = generation_client.app.state.service.repository

    def broken_save(job_data, **kwargs):
        raise RuntimeError("synthetic demo_job insert failure")
    monkeypatch.setattr(repository, "save_job", broken_save)
    response = generation_client.post(
        f"/api/v1/projects/{project_id}/technical-volume/stream",
        headers={**headers, "If-Match": str(workspace["revision"]), "Idempotency-Key": str(uuid4())}, json={})
    assert response.status_code == 500 and response.json()["code"] == "INTERNAL_ERROR"
    assert response.json()["details"]["reason"] == "job_persistence"
    state = repository.read()
    jobs = [j for j in state.recoverable_jobs.values() if j.get("project_id") == project_id and j.get("type") == "technical_volume"]
    assert jobs and jobs[-1]["status"] == "failed"
    assert "任务行写入失败" in jobs[-1]["message"]
    assert not model.started.wait(0.2)


@pytest.mark.mysql
def test_mysql_seed_account_remains_authenticated_on_hot_paths():
    with TestClient(create_demo_app()) as client:
        headers = login(client, "alpha-manager")
        created = client.post("/api/v1/projects", headers=headers, json={"name": "合成MySQL种子账号热路径"})
        assert created.status_code == 200, created.text
        workspace = client.get(f"/api/v1/projects/{created.json()['id']}/workspace", headers=headers)
        assert workspace.status_code == 200, workspace.text


@pytest.mark.mysql
def test_mysql_hot_project_state_matches_full_fingerprint_with_legacy_json_and_entry_order():
    with TestClient(create_demo_app()) as client:
        flow = ProjectFlow(client).ready()
        repository = client.app.state.service.repository

        def extra(state):
            for item_id in ("zz-order", "aa-order"):
                state.library[item_id] = {"id": item_id, "company_id": "alpha", "name": item_id,
                                          "type": "qualification", "content": item_id, "status": "confirmed", "revision": 1,
                                          "valid_until": "2099-01-01"}
            state.sla_templates["sla-hot"] = {"id": "sla-hot", "company_id": "alpha", "name": "合成SLA",
                                              "status": "confirmed", "revision": 1, "variables": []}
            state.service_stores.setdefault("attachments", {}).setdefault("items", {})["att-hot"] = {
                "id": "att-hot", "company_id": "alpha", "library_id": "zz-order", "sha256": "a",
                "page_from": 1, "page_to": 1, "is_sensitive": False, "shows_identity": False, "feature_tags": []}
        repository.transaction(extra)
        # 历史行可能是带空格的非紧凑 JSON；热路径不得靠 LIKE 字符串形状判断 company_id。
        with repository.engine.begin() as connection:
            row = connection.execute(text("SELECT entry_id, body FROM demo_state_entry WHERE scope='library' LIMIT 1")).first()
            connection.execute(text("UPDATE demo_state_entry SET body=:body WHERE scope='library' AND entry_id=:entry_id"),
                               {"body": json.dumps(json.loads(row.body), ensure_ascii=False), "entry_id": row.entry_id})
        # 清掉条目缓存，模拟进程重启后首次按历史 JSON 行重建全量态。
        repository._entries.cache.clear()
        # 检查与导出是在同一批输入之后生成；工作台/下载门禁读取热路径时必须仍显示有效。
        flow.checked_export()
        workspace = flow.state()
        assert workspace["checks"][-1]["status"] == "passed"
        assert workspace["exports"][-1]["status"] == "valid"
        full = repository.read()
        token = flow.headers["Authorization"].split(" ", 1)[1]
        principal = type("P", (), {"session_token": token, "user": full.accounts["alpha-manager"]})()
        hot = repository.read_project_state(flow.id, principal)
        assert len(hot.library) == len(full.library)
        assert len(hot.sla_templates) == len(full.sla_templates)
        assert project_input_fingerprint(hot, flow.id) == project_input_fingerprint(full, flow.id)
