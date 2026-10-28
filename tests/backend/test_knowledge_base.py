# 为什么有这个文件：核对公司知识库（RAGFlow）同步与检索的完整闭环。
# 它解决什么问题：证明资料确认后进入知识库、改版/撤销确认/过期后旧文档被删除且不再召回、
# 检索命中能映射回资料并实时复核、片段同步状态真实反映解析结果、未配置时不伪造“已同步”。

from __future__ import annotations

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


def test_confirmed_library_item_is_synced_and_retrievable_by_source_id(client, fake):
    headers = login(client)
    item = _library_write(client, headers, _confirmed("合成信息安全管理体系认证", "合成证书编号 ZX-0001，覆盖运维服务。"))
    entry, status = _entry(client, headers, "library:" + item["id"])
    assert status["enabled"] is True and status["dataset_id"]
    assert entry["status"] == "synced" and entry["chunk_count"] > 0
    ds = fake.datasets[status["dataset_id"]]
    assert ds["name"] == f"{_company(client, headers)}::icg-library"
    doc = fake.documents[entry["document_id"]]
    assert doc["meta_fields"]["source_id"] == item["id"] and doc["meta_fields"]["revision"] == "1"

    found = _search(client, headers, "信息安全管理体系认证证书")
    hit = next(h for h in found["items"] if h["source_id"] == item["id"])
    assert hit["cite_tag"] == f"[片:{item['id']}]"
    assert hit["attachable"] is True and hit["reference_only"] is False
    retrieval = [c for c in fake.calls if c[1] == "/api/v1/retrieval"][-1][2]
    assert entry["document_id"] in retrieval["document_ids"]


def test_pending_items_never_enter_the_knowledge_base(client, fake):
    headers = login(client)
    item = _library_write(client, headers, {"name": "合成待审资料", "type": "qualification", "content": "合成待审正文。"})
    entry, _ = _entry(client, headers, "library:" + item["id"])
    assert entry is None
    assert all(d["meta_fields"].get("source_id") != item["id"] for d in fake.documents.values())


def test_revision_change_replaces_document_and_old_version_is_not_recalled(client, fake):
    headers = login(client)
    item = _library_write(client, headers, _confirmed("合成运维人员证书", "旧版正文：合成工程师甲持证。"))
    first, _ = _entry(client, headers, "library:" + item["id"])
    updated = _library_write(client, headers, {"content": "新版正文：合成工程师乙持证。", "status": "confirmed",
                                               "reason": "合成复核。"}, item["id"])
    assert updated["revision"] == 2
    second, _ = _entry(client, headers, "library:" + item["id"])
    assert second["document_id"] != first["document_id"] and second["revision"] == 2
    assert first["document_id"] not in fake.documents  # 旧版本文档已删除
    hits = _search(client, headers, "合成工程师持证")["items"]
    texts = " ".join(h["content"] for h in hits if h["source_id"] == item["id"])
    assert "新版正文" in texts and "旧版正文" not in texts


def test_unconfirmed_item_is_removed_and_stale_index_is_filtered_live(client, fake):
    headers = login(client)
    item = _library_write(client, headers, _confirmed("合成撤销资料", "合成撤销正文，含唯一词青鸾。"))
    entry, _ = _entry(client, headers, "library:" + item["id"])
    assert _search(client, headers, "青鸾")["items"]

    # 索引还没来得及同步时（如后台同步排队中），资料状态已变：检索按 DemoState 实时复核并丢弃。
    repository = client.app.state.service.repository
    repository.transaction(lambda state: state.library[item["id"]].__setitem__("status", "pending"))
    assert all(h["source_id"] != item["id"] for h in _search(client, headers, "青鸾")["items"])
    repository.transaction(lambda state: state.library[item["id"]].__setitem__("status", "confirmed"))

    # RAGFlow 删除失败：文档仍在 RAGFlow，但已不在索引里，检索按索引文档过滤，不会召回。
    fake.fail_deletes = True
    _library_write(client, headers, {"status": "rejected"}, item["id"])
    assert entry["document_id"] in fake.documents
    assert all(h["source_id"] != item["id"] for h in _search(client, headers, "青鸾")["items"])
    pending = repository.read().service_stores["kb_index"][_company(client, headers)].get("pending_deletes")
    assert entry["document_id"] in pending
    fake.fail_deletes = False
    client.post("/api/v1/knowledge-base/sync", headers=headers)
    assert entry["document_id"] not in fake.documents


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
    hits = _search(client, headers, "玄武平台运维")["items"]
    hit = next(h for h in hits if h["source_id"] == item["id"])
    assert hit["reference_only"] is True and hit["attachable"] is False
    only_evidence = _search(client, headers, "玄武平台运维", kinds=["evidence"])["items"]
    assert all(h["source_id"] != item["id"] for h in only_evidence)


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
        assert entry["status"] == "parsing"
        assert all(h["source_id"] != item["id"] for h in _search(client, headers, "合成异步正文")["items"])
        fake.finish_parsing()
        refreshed = client.get("/api/v1/knowledge-base/status?refresh=true", headers=headers).json()
        assert next(r for r in refreshed["items"] if r["key"] == "library:" + item["id"])["status"] == "synced"


def test_parse_failure_and_upload_failure_are_recorded_and_retried(client, fake):
    headers = login(client)
    item = _library_write(client, headers, _confirmed("合成解析失败资料", "合成正文 " + FAIL_MARKER))
    entry, status = _entry(client, headers, "library:" + item["id"])
    assert entry["status"] == "failed" and status["counts"].get("failed", 0) >= 1

    fake.fail_uploads = True
    other = _library_write(client, headers, _confirmed("合成上传失败资料", "合成上传失败正文。"))  # 保存不受影响
    assert other["status"] == "confirmed"
    failed, _ = _entry(client, headers, "library:" + other["id"])
    assert failed["status"] == "failed" and "上传" in failed["message"]
    fake.fail_uploads = False
    result = client.post("/api/v1/knowledge-base/sync", headers=headers).json()
    assert result["enabled"] is True and result["uploaded"] >= 1
    retried, _ = _entry(client, headers, "library:" + other["id"])
    assert retried["status"] == "synced"


def test_full_sync_repairs_drift_between_index_and_ragflow(client, fake):
    headers = login(client)
    item = _library_write(client, headers, _confirmed("合成漂移资料", "合成漂移正文：麒麟平台。"))
    entry, status = _entry(client, headers, "library:" + item["id"])
    del fake.documents[entry["document_id"]]  # 有人在 RAGFlow 里手工删了文档
    orphan = fake.client().upload_document(status["dataset_id"], "orphan.md", "遗留文档")
    result = client.post("/api/v1/knowledge-base/sync", headers=headers).json()
    assert result["uploaded"] >= 1
    repaired, _ = _entry(client, headers, "library:" + item["id"])
    assert repaired["status"] == "synced" and repaired["document_id"] in fake.documents
    assert orphan.id not in fake.documents
    assert any(h["source_id"] == item["id"] for h in _search(client, headers, "麒麟平台")["items"])


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
    assert detail["kb_sync_status"] == "synced"  # 发布后自动同步（测试中为同步执行）
    synced = client.post(f"/api/v1/snippet-publications/{snippet['id']}/sync",
                         headers={**headers, "Idempotency-Key": str(uuid4()), "If-Match": "1"}, json={})
    assert synced.status_code == 200 and synced.json()["synced"] is True
    hits = _search(client, headers, "白虎巡检流程", kinds=["snippet"])["items"]
    assert hits and hits[0]["source_type"] == "snippet" and hits[0]["attachable"] is False


def test_without_ragflow_sync_never_claims_success():
    app = create_app()
    with TestClient(app) as client:
        headers = login(client)
        status = client.get("/api/v1/knowledge-base/status", headers=headers).json()
        assert status["enabled"] is False
        assert client.post("/api/v1/knowledge-base/sync", headers=headers).json()["enabled"] is False
        assert _search(client, headers, "任意")["skipped_reason"] == "RAGFlow is not configured"


def test_generation_context_gets_knowledge_candidates_as_pian_not_zheng(client, fake):
    from icg.domain.knowledge_base import KnowledgeEvidenceService
    from icg.infra.retrieval import CandidateRequest

    headers = login(client)
    company = _company(client, headers)
    item = _library_write(client, headers, _confirmed("合成等保三级测评报告", "合成测评结论：符合等保三级要求。"))
    service = client.app.state.service
    assert isinstance(service.evidence_service, KnowledgeEvidenceService)
    result = service.evidence_service.collect(CandidateRequest(company_id=company, query="等保三级测评", library_items=[]))
    kb_candidates = [c for c in result.candidates if c.path == "B" and c.source_id == item["id"]]
    assert kb_candidates and kb_candidates[0].name == "合成等保三级测评报告"
    search_hits = service.evidence_service.search(company, "等保三级测评")
    assert any(h.id == item["id"] and h.text for h in search_hits)
    # 其他公司检索不到。
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
