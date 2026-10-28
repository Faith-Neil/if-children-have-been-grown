# 为什么有这个文件：核对知识库管控接口（/api/v1/kb-admin）与 ICG 摄入流程。
# 它解决什么问题：证明本系统能经 API 管住 RAGFlow：按角色授权、部署招投标专用流程并绑定数据集、
# 调参与乐观锁、上传历史投标原件并只作参考、证书抽取只生成待核验草稿、分块修正、重建迁移原件、全程留痕。

from __future__ import annotations

import base64
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from fake_ragflow_v1 import FakeRagflowV1
from icg.app.main import create_app
from icg.infra.ragflow_pipelines import PROFILES, build_dsl, company_tag, dsl_fingerprint, parse_pipeline_title
from test_reference_flow import login

ADMIN = "alpha-data-admin"


@pytest.fixture()
def fake():
    return FakeRagflowV1()


@pytest.fixture()
def client(fake):
    app = create_app()
    kb = app.state.service.knowledge_base
    kb._client_factory = lambda state, company_id: fake.client()
    kb.background = False
    with TestClient(app) as test_client:
        yield test_client


def _b64(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode()


def _upload(client, headers, kind, filename, text, **meta):
    result = client.post(f"/api/v1/kb-admin/datasets/{kind}/documents", headers=headers,
                         json={"filename": filename, "content_base64": _b64(text), "content_type": "text/markdown",
                               "metadata": meta})
    assert result.status_code == 200, result.text
    return result.json()


def test_roles_gate_every_write(client):
    viewer = login(client, "alpha-viewer")
    assert client.get("/api/v1/kb-admin/overview", headers=viewer).status_code == 403
    manager = login(client, "alpha-manager")
    assert client.get("/api/v1/kb-admin/overview", headers=manager).status_code == 200
    assert client.post("/api/v1/kb-admin/pipelines/deploy", headers=manager, json={}).status_code == 403
    admin = login(client, ADMIN)
    assert client.post("/api/v1/kb-admin/pipelines/deploy", headers=admin, json={}).status_code == 200
    # 删除整类数据集与改连接只允许公司管理员
    deleted = client.post("/api/v1/kb-admin/datasets/history/delete", headers=admin, json={"confirm_name": "x"})
    assert deleted.status_code == 403
    cfg = client.get("/api/v1/ragflow-config", headers=admin).json()
    put = client.put("/api/v1/ragflow-config", headers={**admin, "If-Match": str(cfg["revision"])}, json={"base_url": "http://x"})
    assert put.status_code == 403


def test_deploy_creates_bid_pipelines_and_binds_datasets(client, fake):
    admin = login(client, ADMIN)
    result = client.post("/api/v1/kb-admin/pipelines/deploy", headers=admin, json={}).json()
    assert set(result["datasets"]) == {"library", "history", "certificate"}
    for kind, info in result["datasets"].items():
        assert info["mode"] == "pipeline", info
        dataset = fake.datasets[info["dataset_id"]]
        agent = fake.agents[info["pipeline_id"]]
        assert dataset["pipeline_id"] == agent["id"] and agent["canvas_category"] == "dataflow_canvas"
        tag, profile, version = parse_pipeline_title(agent["title"])
        assert tag == company_tag("alpha") and version == 1 and len(agent["title"]) <= 32
    history = fake.agents[result["datasets"]["history"]["pipeline_id"]]["dsl"]["components"]
    chunker = next(v for k, v in history.items() if k.startswith("TitleChunker"))["obj"]["params"]
    assert chunker["include_heading_content"] is True
    assert any("第[零一二三四五六七八九十百0-9]+章" in e for g in chunker["levels"] for e in g)
    extractor = next(v for k, v in history.items() if k.startswith("Extractor"))["obj"]["params"]
    assert {m["key"] for m in extractor["metadata"]["metadata"]} >= {"project_name", "purchaser", "industry"}
    assert "招标文件" in extractor["questions"]["system_prompt"]
    # 再部署一次：不重复创建
    again = client.post("/api/v1/kb-admin/pipelines/deploy", headers=admin, json={}).json()
    assert len(fake.agents) == 3 and again["datasets"]["history"]["pipeline_id"] == result["datasets"]["history"]["pipeline_id"]


def test_settings_change_updates_pipeline_and_requires_if_match(client, fake):
    admin = login(client, ADMIN)
    client.post("/api/v1/kb-admin/pipelines/deploy", headers=admin, json={})
    settings = client.get("/api/v1/kb-admin/settings", headers=admin).json()
    assert client.put("/api/v1/kb-admin/settings", headers=admin, json={"similarity_threshold": 0.1}).status_code == 428
    body = {"similarity_threshold": 0.12, "keywords_weight": 0.5, "llm_id": "qwen3-32b@local@Ollama",
            "profiles": {"history_bid": {"questions_top_n": 4, "extra_heading_patterns": ["^附件[0-9]+"]}}}
    updated = client.put("/api/v1/kb-admin/settings", headers={**admin, "If-Match": str(settings["revision"])}, json=body)
    assert updated.status_code == 200, updated.text
    assert updated.json()["revision"] == settings["revision"] + 1
    stale = client.put("/api/v1/kb-admin/settings", headers={**admin, "If-Match": str(settings["revision"])}, json=body)
    assert stale.status_code == 409
    bad = client.put("/api/v1/kb-admin/settings", headers={**admin, "If-Match": str(settings["revision"] + 1)},
                     json={"profiles": {"history_bid": {"extra_heading_patterns": ["("]}}})
    assert bad.status_code == 422
    deployed = client.post("/api/v1/kb-admin/pipelines/deploy", headers=admin, json={"kinds": ["history"]}).json()
    pipeline = fake.agents[deployed["datasets"]["history"]["pipeline_id"]]
    extractor = next(v for k, v in pipeline["dsl"]["components"].items() if k.startswith("Extractor"))["obj"]["params"]
    assert extractor["questions"]["top_n"] == 4 and extractor["llm_id"] == "qwen3-32b@local@Ollama"
    chunker = next(v for k, v in pipeline["dsl"]["components"].items() if k.startswith("TitleChunker"))["obj"]["params"]
    assert chunker["levels"][0] == ["^附件[0-9]+"]
    assert deployed["datasets"]["history"]["reparse_required"] is True
    models = client.get("/api/v1/kb-admin/models", headers=admin).json()
    assert models["embedding"][0]["id"] == "bge-m3@local@Ollama"


def test_history_bid_upload_is_reference_only_and_searchable(client, fake):
    admin = login(client, ADMIN)
    doc = _upload(client, admin, "history", "2023合成农商行运维投标.md",
                  "第五章 技术方案\n\n一、运维服务体系\n\n采用三级运维服务体系：一线服务台、二线专家、三线原厂。",
                  project_name="合成农商行运维服务", purchaser="合成农商行")
    assert doc["status"] == "synced" and doc["dataset_kind"] == "history"
    remote = fake.documents[doc["document_id"]]
    assert remote["meta_fields"]["source_id"] == doc["source_id"] and remote["meta_fields"]["purchaser"] == "合成农商行"
    found = client.post("/api/v1/kb-admin/retrieval-test", headers=admin,
                        json={"query": "三级运维服务体系", "kinds": ["history"]}).json()
    hit = next(h for h in found["items"] if h["source_id"] == doc["source_id"])
    assert hit["reference_only"] is True and hit["attachable"] is False
    # 写作检索默认也带上历史参考，但不会出现在只查证据的检索里
    evidence_only = client.post("/api/v1/knowledge-base/search", headers=admin,
                                json={"query": "三级运维服务体系", "kinds": ["evidence"]}).json()
    assert all(h["source_id"] != doc["source_id"] for h in evidence_only["items"])
    # 停用后不再召回
    client.patch(f"/api/v1/kb-admin/datasets/history/documents/{doc['document_id']}", headers=admin, json={"enabled": False})
    again = client.post("/api/v1/kb-admin/retrieval-test", headers=admin,
                        json={"query": "三级运维服务体系", "kinds": ["history"]}).json()
    assert all(h["source_id"] != doc["source_id"] for h in again["items"])
    listing = client.get("/api/v1/kb-admin/datasets/history/documents", headers=admin).json()
    assert listing["items"][0]["source_type"] == "file" and listing["items"][0]["uploaded_by"] == ADMIN
    # 删除
    assert client.delete(f"/api/v1/kb-admin/datasets/history/documents/{doc['document_id']}", headers=admin).status_code == 200
    assert doc["document_id"] not in fake.documents


def test_upload_validation(client):
    admin = login(client, ADMIN)
    bad_type = client.post("/api/v1/kb-admin/datasets/history/documents", headers=admin,
                           json={"filename": "a.exe", "content_base64": _b64("x")})
    assert bad_type.status_code == 422 and bad_type.json()["code"] == "FILE_TYPE_UNSUPPORTED"
    bad_b64 = client.post("/api/v1/kb-admin/datasets/history/documents", headers=admin,
                          json={"filename": "a.pdf", "content_base64": "%%%"})
    assert bad_b64.status_code == 422
    library = client.post("/api/v1/kb-admin/datasets/library/documents", headers=admin,
                          json={"filename": "a.md", "content_base64": _b64("x")})
    assert library.status_code == 422  # 资料库文档只能由资料同步产生


def test_certificate_extraction_creates_pending_library_draft(client, fake):
    fake.metadata_extractor = lambda text: {"cert_name": "合成信息安全管理体系认证证书", "cert_no": "HZ-ISMS-0009",
                                            "issuer": "合成认证中心", "valid_to": "2028-06-30"}
    admin = login(client, ADMIN)
    doc = _upload(client, admin, "certificate", "iso27001.pdf", "证书扫描件文字：合成信息安全管理体系认证证书")
    draft = client.post(f"/api/v1/kb-admin/certificates/{doc['document_id']}/library-draft", headers=admin)
    assert draft.status_code == 200, draft.text
    item = draft.json()["library_item"]
    assert item["status"] == "pending" and item["usable_as_evidence"] is False  # 必须人工核对后确认
    assert item["name"] == "合成信息安全管理体系认证证书" and item["valid_until"] == "2028-06-30"
    assert "HZ-ISMS-0009" in item["content"] and "须人工核对原件" in item["content"]
    # 待核验资料不进知识库
    status = client.get("/api/v1/knowledge-base/status", headers=admin).json()
    assert all(row["source_id"] != item["id"] for row in status["items"])


def test_chunk_review_and_library_documents_are_system_managed(client, fake):
    admin = login(client, ADMIN)
    revision = client.get("/api/v1/library", headers=admin).json()["revision"]
    created = client.post("/api/v1/library", headers={**admin, "If-Match": str(revision), "Idempotency-Key": str(uuid4())},
                          json={"name": "合成等保三级测评报告", "type": "qualification", "content": "测评结论：符合等保三级。",
                                "status": "confirmed", "reason": "合成核对。", "valid_until": "2099-01-01"}).json()["item"]
    entry = next(r for r in client.get("/api/v1/knowledge-base/status", headers=admin).json()["items"]
                 if r["source_id"] == created["id"])
    doc_id = entry["document_id"]
    chunks = client.get(f"/api/v1/kb-admin/datasets/library/documents/{doc_id}/chunks", headers=admin).json()
    assert chunks["total"] >= 1 and all("合成等保三级测评报告" in c["content"] or c["content"].startswith("#") for c in chunks["chunks"])
    chunk_id = chunks["chunks"][-1]["id"]
    blocked = client.patch(f"/api/v1/kb-admin/datasets/library/documents/{doc_id}/chunks/{chunk_id}", headers=admin,
                           json={"content": "改写"})
    assert blocked.status_code == 409
    ok = client.patch(f"/api/v1/kb-admin/datasets/library/documents/{doc_id}/chunks/{chunk_id}", headers=admin,
                      json={"questions": ["投标人须提供网络安全等级保护三级测评报告"], "available": True})
    assert ok.status_code == 200
    assert client.delete(f"/api/v1/kb-admin/datasets/library/documents/{doc_id}", headers=admin).status_code == 409
    # 他司文档 id 一律 404
    other = client.get("/api/v1/kb-admin/datasets/library/documents/not-mine/chunks", headers=admin)
    assert other.status_code == 404


def test_structured_markdown_sections_carry_item_name():
    from icg.domain.knowledge_base import library_document
    long = "。".join(f"第{i}段合成正文内容用于切节" for i in range(80)) + "。"
    doc = library_document({"id": "x", "company_id": "c", "type": "personnel", "status": "confirmed", "name": "合成员工甲",
                            "content": long, "revision": 1})
    sections = [line for line in doc.markdown.splitlines() if line.startswith("## ")]
    assert len(sections) >= 3 and all(line.startswith("## 合成员工甲·人员") for line in sections)


def test_rebuild_migrates_files_and_resyncs_library(client, fake):
    admin = login(client, ADMIN)
    client.post("/api/v1/kb-admin/pipelines/deploy", headers=admin, json={})
    doc = _upload(client, admin, "history", "历史.md", "第一章 总则\n\n合成历史内容玄武。")
    old = client.get("/api/v1/kb-admin/datasets", headers=admin).json()["items"]
    old_history = next(r for r in old if r["kind"] == "history")["dataset_id"]
    settings = client.get("/api/v1/kb-admin/settings", headers=admin).json()
    client.put("/api/v1/kb-admin/settings", headers={**admin, "If-Match": str(settings["revision"])},
               json={"embedding_model": "bge-m3@local@Ollama"})
    overview = client.get("/api/v1/kb-admin/overview", headers=admin).json()
    assert overview["datasets"]["history"]["rebuild_required"] is True
    rebuilt = client.post("/api/v1/kb-admin/datasets/history/rebuild", headers=admin).json()
    assert rebuilt["migrated_files"] == 1 and rebuilt["dataset_id"] != old_history
    assert old_history not in fake.datasets
    assert fake.datasets[rebuilt["dataset_id"]]["embedding_model"] == "bge-m3@local@Ollama"
    client.get("/api/v1/knowledge-base/status?refresh=true", headers=admin)
    hits = client.post("/api/v1/kb-admin/retrieval-test", headers=admin,
                       json={"query": "合成历史内容玄武", "kinds": ["history"]}).json()["items"]
    assert any(h["source_id"] == doc["source_id"] for h in hits)
    actions = [row["action"] for row in client.get("/api/v1/kb-admin/audit", headers=admin).json()["items"]]
    assert {"dataset.rebuild", "settings.update", "document.upload", "pipelines.deploy"} <= set(actions)


def test_falls_back_to_builtin_parser_when_pipelines_unsupported(client, fake):
    fake.supports_agents = False
    admin = login(client, ADMIN)
    result = client.post("/api/v1/kb-admin/pipelines/deploy", headers=admin, json={"kinds": ["library"]}).json()
    info = result["datasets"]["library"]
    assert info["mode"] == "builtin" and "摄入流程不可用" in info["warning"]


def test_dsl_is_deterministic_and_graph_matches_components():
    for profile in PROFILES.values():
        first, second = build_dsl(profile), build_dsl(profile)
        assert dsl_fingerprint(first) == dsl_fingerprint(second)
        node_ids = {n["id"] for n in first["graph"]["nodes"]}
        assert node_ids == set(first["components"])
        edges = {(e["source"], e["target"]) for e in first["graph"]["edges"]}
        assert edges == {(k, d) for k, v in first["components"].items() for d in v["downstream"]}
