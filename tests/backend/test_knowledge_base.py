# 为什么有这个文件：核对公司知识库（RAGFlow）同步与检索的完整闭环。
# 它解决什么问题：证明资料确认后进入知识库、改版/撤销确认/过期后旧文档被删除且不再召回、
# 检索命中能映射回资料并实时复核、片段同步状态真实反映解析结果、未配置时不伪造“已同步”。

from __future__ import annotations

import base64
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from fake_ragflow_v1 import FAIL_MARKER, FakeRagflowV1
from icg.app.main import create_app
from icg.domain.generation_context import build_generation_context  # noqa: F401  (保证导入路径可用)
from icg.domain.knowledge_base import KnowledgeBaseService, desired_documents
from test_reference_flow import login


@pytest.fixture()
def fake():
    return FakeRagflowV1()


@pytest.fixture()
def client(fake):
    app = create_app()
    kb: KnowledgeBaseService = app.state.service.knowledge_base
    kb._client_factory = lambda state, company_id: fake.client()
    kb.background = False
    with TestClient(app) as test_client:
        yield test_client


def _company(client, headers) -> str:
    return client.get("/api/v1/session", headers=headers).json()["user"]["company_id"]


def _library_write(client, headers, payload, item_id=None):
    revision = client.get("/api/v1/library", headers=headers).json()["revision"]
    h = {**headers, "If-Match": str(revision), "Idempotency-Key": str(uuid4())}
    if item_id:
        result = client.patch(f"/api/v1/library/{item_id}", headers=h, json=payload)
    else:
        result = client.post("/api/v1/library", headers=h, json=payload)
    assert result.status_code == 200, result.text
    return result.json()["item"]


def _confirmed(name, content, **extra):
    return {"name": name, "type": "qualification", "content": content, "status": "confirmed",
            "reason": "合成核对依据。", "valid_until": "2099-12-31", **extra}


def _entry(client, headers, key):
    status = client.get("/api/v1/knowledge-base/status", headers=headers).json()
    return next((row for row in status["items"] if row["key"] == key), None), status


def _search(client, headers, query, **extra):
    result = client.post("/api/v1/knowledge-base/search", headers=headers, json={"query": query, **extra})
    assert result.status_code == 200, result.text
    return result.json()


def _b64(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode()


def _upload_kb_file(client, headers, fake, kind: str, filename: str, text: str, **meta):
    if kind in ("history", "materials"):
        ensured = client.post(f"/api/v1/kb-admin/datasets/{kind}/ensure", headers=headers, json={})
        assert ensured.status_code == 200, ensured.text
    uploaded = client.post(
        f"/api/v1/kb-admin/datasets/{kind}/documents",
        headers=headers,
        json={"filename": filename, "content_base64": _b64(text), "content_type": "text/markdown", "metadata": meta},
    )
    assert uploaded.status_code == 200, uploaded.text
    fake.finish_parsing()
    company = _company(client, headers)
    client.app.state.service.knowledge_base.refresh_status(company)
    return uploaded.json()


def test_confirmed_library_item_is_synced_and_retrievable_by_source_id(client, fake):
    headers = login(client)
    item = _library_write(client, headers, _confirmed("合成信息安全管理体系认证", "合成证书编号 ZX-0001，覆盖运维服务。"))
    entry, status = _entry(client, headers, "library:" + item["id"])
    assert entry is None
    assert fake.datasets == {}
    assert status["message"] == "资料与方案片段不再同步到知识库。"


def test_pending_items_never_enter_the_knowledge_base(client, fake):
    headers = login(client)
    item = _library_write(client, headers, {"name": "合成待审资料", "type": "qualification", "content": "合成待审正文。"})
    entry, _ = _entry(client, headers, "library:" + item["id"])
    assert entry is None
    assert all(d["meta_fields"].get("source_id") != item["id"] for d in fake.documents.values())


def test_revision_change_replaces_document_and_old_version_is_not_recalled(client, fake):
    headers = login(client)
    item = _library_write(client, headers, _confirmed("合成运维人员证书", "旧版正文：合成工程师甲持证。"))
    assert all(d["meta_fields"].get("source_id") != item["id"] for d in fake.documents.values())
    updated = _library_write(client, headers, {"content": "新版正文：合成工程师乙持证。", "status": "confirmed",
                                               "reason": "合成复核。"}, item["id"])
    assert updated["revision"] == 2
    assert all(d["meta_fields"].get("source_id") != item["id"] for d in fake.documents.values())
    assert all(h["source_id"] != item["id"] for h in _search(client, headers, "合成工程师持证")["items"])


def test_unconfirmed_item_is_removed_and_stale_index_is_filtered_live(client, fake):
    headers = login(client)
    item = _library_write(client, headers, _confirmed("合成撤销资料", "合成撤销正文，含唯一词青鸾。"))
    assert all(h["source_id"] != item["id"] for h in _search(client, headers, "青鸾")["items"])
    assert all(d["meta_fields"].get("source_id") != item["id"] for d in fake.documents.values())

    repository = client.app.state.service.repository
    company = _company(client, headers)

    def seed_stale(state):
        index = state.service_stores.setdefault("kb_index", {}).setdefault(company, {"entries": {}, "files": {}, "datasets": {}})
        index["entries"]["library:" + item["id"]] = {
            "key": "library:" + item["id"], "source_type": "library", "source_id": item["id"], "revision": 1,
            "name": item["name"], "item_type": "qualification", "content_hash": "deadbeef", "document_id": "stale-doc",
            "status": "synced", "message": "", "chunk_count": 1, "updated_at": "2020-01-01T00:00:00+08:00", "enabled": True,
        }
        index["dataset_id"] = "legacy-dataset"

    repository.transaction(seed_stale)
    fake.documents["stale-doc"] = {"id": "stale-doc", "dataset_id": "legacy-dataset", "name": "stale.md",
                                   "content": "合成撤销正文，含唯一词青鸾。", "meta_fields": {"source_id": item["id"]},
                                   "ingestion_status": "COMPLETED", "chunk_count": 1, "chunks": [{"id": "c1", "content": "青鸾"}],
                                   "enabled": 1, "progress": 1.0, "progress_msg": ""}
    fake.datasets["legacy-dataset"] = {"id": "legacy-dataset", "name": f"{company}::icg-library", "pipeline_id": ""}

    repository.transaction(lambda state: state.library[item["id"]].__setitem__("status", "pending"))
    assert all(h["source_id"] != item["id"] for h in _search(client, headers, "青鸾")["items"])


def test_expired_items_are_not_indexed():
    from icg.domain.domain import DemoState
    state = DemoState()
    state.library["old"] = {"id": "old", "company_id": "c1", "type": "qualification", "status": "confirmed",
                            "name": "过期证书", "content": "合成。", "revision": 1, "valid_until": "2000-01-01"}
    state.library["long"] = {"id": "long", "company_id": "c1", "type": "qualification", "status": "confirmed",
                             "name": "长期证书", "content": "合成。", "revision": 1, "valid_until": "2000-01-01",
                             "is_long_term": True}
    state.library["other"] = {"id": "other", "company_id": "c2", "type": "qualification", "status": "confirmed",
                              "name": "他司证书", "content": "合成。", "revision": 1}
    assert set(desired_documents(state, "c1")) == {"library:long"}


def test_history_items_are_reference_only(client, fake):
    headers = login(client)
    item = _library_write(client, headers, {**_confirmed("合成历史标书", "合成历史方案：玄武平台运维。"), "type": "history"})
    assert all(d["meta_fields"].get("source_id") != item["id"] for d in fake.documents.values())
    assert all(h["source_id"] != item["id"] for h in _search(client, headers, "玄武平台运维")["items"])


def test_restricted_items_need_permission(client, fake):
    admin = login(client)
    item = _library_write(client, admin, {**_confirmed("合成受限资料", "合成受限正文：朱雀合同。"), "is_restricted": True})
    viewer = login(client, "alpha-viewer")
    assert all(h["source_id"] != item["id"] for h in _search(client, viewer, "朱雀合同")["items"])


def test_async_parsing_reports_parsing_until_refresh(fake):
    fake.async_parse = True
    app = create_app()
    kb = app.state.service.knowledge_base
    kb._client_factory = lambda state, company_id: fake.client()
    kb.background = False
    with TestClient(app) as client:
        headers = login(client)
        item = _library_write(client, headers, _confirmed("合成异步资料", "合成异步正文。"))
        entry, _ = _entry(client, headers, "library:" + item["id"])
        assert entry is None
        assert all(d["meta_fields"].get("source_id") != item["id"] for d in fake.documents.values())
        assert all(h["source_id"] != item["id"] for h in _search(client, headers, "合成异步正文")["items"])


def test_parse_failure_and_upload_failure_are_recorded_and_retried(client, fake):
    headers = login(client)
    item = _library_write(client, headers, _confirmed("合成解析失败资料", "合成正文 " + FAIL_MARKER))
    entry, status = _entry(client, headers, "library:" + item["id"])
    assert entry is None
    assert all(d["meta_fields"].get("source_id") != item["id"] for d in fake.documents.values())

    other = _library_write(client, headers, _confirmed("合成上传失败资料", "合成上传失败正文。"))
    assert other["status"] == "confirmed"
    failed, _ = _entry(client, headers, "library:" + other["id"])
    assert failed is None
    assert all(d["meta_fields"].get("source_id") != other["id"] for d in fake.documents.values())
    result = client.post("/api/v1/knowledge-base/sync", headers=headers).json()
    assert result["enabled"] is True and result["uploaded"] == 0
    assert result["message"] == "资料与方案片段不再同步到知识库。"


def test_full_sync_repairs_drift_between_index_and_ragflow(client, fake):
    headers = login(client)
    item = _library_write(client, headers, _confirmed("合成漂移资料", "合成漂移正文：麒麟平台。"))
    assert all(d["meta_fields"].get("source_id") != item["id"] for d in fake.documents.values())
    result = client.post("/api/v1/knowledge-base/sync", headers=headers).json()
    assert result["uploaded"] == 0 and result["message"] == "资料与方案片段不再同步到知识库。"
    assert all(h["source_id"] != item["id"] for h in _search(client, headers, "麒麟平台")["items"])


def test_snippet_publish_sync_reflects_real_status(client, fake):
    headers = login(client)
    created = client.post("/api/v1/snippet-publications", headers={**headers, "Idempotency-Key": str(uuid4())},
                          json={"product": "合成运维平台", "snippet_type": "服务方案", "variables": [],
                                "source_group": "", "boilerplate_group": "", "draft_body": "合成片段正文：白虎巡检流程。"})
    assert created.status_code == 200, created.text
    snippet = created.json()
    published = client.post(f"/api/v1/snippet-publications/{snippet['id']}/publish",
                            headers={**headers, "Idempotency-Key": str(uuid4()), "If-Match": "1"}, json={})
    assert published.json()["blocked"] is False
    detail = client.get(f"/api/v1/snippet-publications/{snippet['id']}", headers=headers).json()
    assert detail["kb_sync_status"] == "unsynced"
    synced = client.post(f"/api/v1/snippet-publications/{snippet['id']}/sync",
                         headers={**headers, "Idempotency-Key": str(uuid4()), "If-Match": "1"}, json={})
    assert synced.status_code == 200 and synced.json()["synced"] is False
    assert all(d["meta_fields"].get("source_id") != snippet["id"] for d in fake.documents.values())
    assert all(h["source_id"] != snippet["id"] for h in _search(client, headers, "白虎巡检流程", kinds=["snippet"])["items"])


def test_without_ragflow_sync_never_claims_success():
    app = create_app()
    with TestClient(app) as client:
        headers = login(client)
        status = client.get("/api/v1/knowledge-base/status", headers=headers).json()
        assert status["enabled"] is False
        assert client.post("/api/v1/knowledge-base/sync", headers=headers).json()["enabled"] is False
        assert _search(client, headers, "任意")["skipped_reason"] == "RAGFlow is not configured"


def test_writing_prompt_splits_history_and_materials(client, fake):
    from icg.domain.chapter_generation import (
        HISTORY_HEADING,
        MATERIALS_HEADING,
        ChapterGenerationService,
    )

    kb_admin = login(client, "alpha-company-admin")
    company = _company(client, kb_admin)
    client.post("/api/v1/kb-admin/pipelines/deploy", headers=kb_admin, json={})

    hist_file = "合成历史投标玄武.docx"
    mat_file = "合成权威资料青龙.pdf"
    hist_phrase = "玄武架构HIST4TASK"
    mat_phrase = "青龙参数MAT4TASK"
    _upload_kb_file(client, kb_admin, fake, "history", hist_file, f"# 历史方案\n\n{hist_phrase} 优秀技术表述。")
    _upload_kb_file(client, kb_admin, fake, "materials", mat_file, f"{mat_phrase} 产品技术参数说明。")

    hits, reason = client.app.state.service.knowledge_base.search(company, hist_phrase, limit=5)
    assert not reason, reason
    assert any(h.name == hist_file for h in hits)
    mat_hits, mat_reason = client.app.state.service.knowledge_base.search(company, mat_phrase, limit=5)
    assert not mat_reason, mat_reason
    assert any(h.name == mat_file for h in mat_hits)

    repository = client.app.state.service.repository
    from icg.domain.generation_context import writing_source_fingerprint

    def seed_workflow(state):
        state.workflows["alpha-project"] = {
            "parse_confirmed": True,
            "requirements": {
                "req-kb-split": {
                    "id": "req-kb-split",
                    "volume": "technical",
                    "category": "technical",
                    "chapter_id": "alpha-tech",
                    "text": f"须说明 {hist_phrase} 与 {mat_phrase}",
                    "response": "经核对响应。",
                    "status": "confirmed",
                    "evidence_ids": [],
                    "source": None,
                    "volume_confirmed_at": "2026-10-01T00:00:00+00:00",
                }
            },
            "writing_plan": {
                "chapters": {
                    "alpha-tech": {"writing_points": hist_phrase, "target_length": 500, "fact_ids": []},
                }
            },
            "knowledge_base_enabled": True,
            "facts": {},
        }
        chapter_plan = state.workflows["alpha-project"]["writing_plan"]["chapters"]["alpha-tech"]
        chapter_plan["confirmed_at"] = "2026-10-01T00:00:00+00:00"
        chapter_plan["confirmed_input_fingerprint"] = writing_source_fingerprint(state, "alpha-project", "alpha-tech")

    repository.transaction(seed_workflow)

    service = client.app.state.service
    chapter_gen = ChapterGenerationService(service, service.repository, service.evidence_service)
    plan_data = chapter_gen.assemble_writing_prompt_plan("alpha-project", "alpha-tech")
    prompt = plan_data["prompt"]

    hist_pos = prompt.index(HISTORY_HEADING)
    mat_pos = prompt.index(MATERIALS_HEADING)
    assert hist_pos < mat_pos
    history_block = prompt[hist_pos:mat_pos]
    assert hist_file in history_block or hist_phrase in history_block
    assert mat_file not in history_block
    materials_block = prompt[mat_pos:]
    assert mat_file in materials_block or mat_phrase in materials_block


def test_generation_context_gets_knowledge_candidates_as_pian_not_zheng(client, fake):
    from icg.domain.knowledge_base import KnowledgeEvidenceService
    from icg.infra.retrieval import CandidateRequest

    headers = login(client)
    company = _company(client, headers)
    item = _library_write(client, headers, _confirmed("合成等保三级测评报告", "合成测评结论：符合等保三级要求。"))
    assert all(d["meta_fields"].get("source_id") != item["id"] for d in fake.documents.values())
    service = client.app.state.service
    assert isinstance(service.evidence_service, KnowledgeEvidenceService)
    result = service.evidence_service.collect(CandidateRequest(company_id=company, query="等保三级测评", library_items=[]))
    assert all(c.source_id != item["id"] for c in result.candidates if c.path == "B")
    search_hits = service.evidence_service.search(company, "等保三级测评")
    assert all(h.id != item["id"] for h in search_hits)
    assert service.evidence_service.search("other-company", "等保三级测评") == []


@pytest.mark.skipif(not (__import__("os").environ.get("ICG_RUN_REAL_RAGFLOW_TESTS") == "1"
                         and __import__("os").environ.get("ICG_RAGFLOW_BASE_URL")
                         and __import__("os").environ.get("ICG_RAGFLOW_API_KEY")),
                    reason="真实 RAGFlow 联调需要 ICG_RUN_REAL_RAGFLOW_TESTS=1 与 ICG_RAGFLOW_BASE_URL/API_KEY")
def test_live_ragflow_sync_and_search_round_trip():
    """真实 RAGFlow：同步一条合成资料，等待解析，检索命中后清理临时数据集。"""
    import time

    app = create_app()
    kb = app.state.service.knowledge_base
    kb.background = False
    with TestClient(app) as client:
        headers = login(client)
        company = _company(client, headers)
        item = _library_write(client, headers, _confirmed("合成联调资料：玄鸟运维平台认证",
                                                          "合成联调正文：玄鸟运维平台通过合成认证，编号 XN-0001。"))
        deadline = time.time() + 600
        status = None
        while time.time() < deadline:
            status = client.get("/api/v1/knowledge-base/status?refresh=true", headers=headers).json()
            row = next(r for r in status["items"] if r["key"] == "library:" + item["id"])
            if row["status"] in ("synced", "failed"):
                break
            time.sleep(10)
        try:
            assert row["status"] == "synced", row
            hits = _search(client, headers, "玄鸟运维平台认证编号")["items"]
            assert any(h["source_id"] == item["id"] for h in hits), hits
        finally:
            kb_client = kb.client_for(company)
            kb_client._send_request("DELETE", kb_client.datasets_url, json_body={"ids": [status["dataset_id"]]})
