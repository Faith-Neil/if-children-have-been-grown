# 为什么有这个文件：历史标书 history_bid 管道四类质量验收（切块 / 抽取分类 / 检索 / 整管健康）。
# 它解决什么问题：只在真实 RAGFlow 上对照脱敏金标原件断言，假服务绿测不能冒充解析质量已验收。

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from icg.app.main import create_app
from test_reference_flow import login

ADMIN = "alpha-data-admin"
FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "history-bid-golden"
MANIFEST_PATH = FIXTURE_DIR / "manifest.json"
PARSE_TIMEOUT_SEC = int(os.environ.get("ICG_HISTORY_BID_PARSE_TIMEOUT", "1800"))
POLL_SEC = 15
DOC_PREFIX = "golden-accept-"

_real_ready = (
    os.environ.get("ICG_RUN_REAL_RAGFLOW_TESTS") == "1"
    and bool(os.environ.get("ICG_RAGFLOW_BASE_URL", "").strip())
    and bool(os.environ.get("ICG_RAGFLOW_API_KEY", "").strip())
)

pytestmark = pytest.mark.skipif(
    not _real_ready,
    reason="真实 RAGFlow 验收需要 ICG_RUN_REAL_RAGFLOW_TESTS=1 与 ICG_RAGFLOW_BASE_URL/API_KEY",
)


def _manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _fixture_bytes(name: str) -> bytes:
    path = FIXTURE_DIR / name
    assert path.is_file(), f"缺少金标夹具 {path}"
    return path.read_bytes()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _all_chunks(client: TestClient, headers: dict, document_id: str) -> list[dict]:
    chunks: list[dict] = []
    page = 1
    while True:
        resp = client.get(
            f"/api/v1/kb-admin/datasets/history/documents/{document_id}/chunks",
            headers=headers,
            params={"page": page, "page_size": 100},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        batch = body.get("chunks") or []
        chunks.extend(batch)
        total = int(body.get("total") or len(chunks))
        if len(chunks) >= total or not batch:
            break
        page += 1
    return chunks


def _wait_synced(client: TestClient, headers: dict, document_id: str) -> dict:
    deadline = time.time() + PARSE_TIMEOUT_SEC
    last = None
    while time.time() < deadline:
        listing = client.get("/api/v1/kb-admin/datasets/history/documents", headers=headers).json()
        row = next((item for item in listing.get("items") or [] if item.get("document_id") == document_id), None)
        last = row
        if row and row.get("status") in ("synced", "failed"):
            return row
        # 远端 run 字段有时先变 DONE
        if row and str(row.get("run") or "").upper() in ("DONE", "3") and int(row.get("chunk_count") or 0) > 0:
            return row
        time.sleep(POLL_SEC)
    pytest.fail(f"解析超时 {PARSE_TIMEOUT_SEC}s document={document_id} last={last}")


@pytest.fixture(scope="module")
def golden_session():
    """部署管道、上传两份金标、等到解析完成；模块结束时删除本轮文档。"""
    app = create_app()
    kb = app.state.service.knowledge_base
    kb.background = False
    uploaded: list[str] = []
    with TestClient(app) as client:
        headers = login(client, ADMIN)
        deploy = client.post("/api/v1/kb-admin/pipelines/deploy", headers=headers, json={"kinds": ["history"]})
        assert deploy.status_code == 200, deploy.text
        deploy_body = deploy.json()
        history_info = deploy_body["datasets"]["history"]
        assert history_info.get("mode") == "pipeline", history_info

        # 读远端 DSL 做 D 类健康核验所需快照
        pipeline_id = history_info.get("pipeline_id") or ""
        assert pipeline_id, history_info
        agent = kb.client_for("alpha").get_agent(pipeline_id)
        dsl = agent.get("dsl") or {}

        docs: dict[str, dict] = {}
        manifest = _manifest()
        for item in manifest["documents"]:
            data = _fixture_bytes(item["fixture"])
            assert _sha256(data) == item["sha256"], item["fixture"]
            filename = f"{DOC_PREFIX}{item['id']}-{item['fixture']}"
            upload = client.post(
                "/api/v1/kb-admin/datasets/history/documents/raw",
                headers=headers,
                params={
                    "filename": filename,
                    "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                },
                content=data,
            )
            assert upload.status_code == 200, upload.text
            document_id = upload.json()["document_id"]
            uploaded.append(document_id)
            row = _wait_synced(client, headers, document_id)
            assert row.get("status") != "failed", row
            # 检索只认本地索引 status=synced；远端 DONE 后必须刷新索引，否则末份文档永远 zero hits。
            kb.refresh_status("alpha")
            chunks = _all_chunks(client, headers, document_id)
            docs[item["id"]] = {
                "document_id": document_id,
                "filename": filename,
                "row": row,
                "chunks": chunks,
                "spec": item,
            }

        kb.refresh_status("alpha")
        payload = {
            "client": client,
            "headers": headers,
            "deploy": deploy_body,
            "dsl": dsl,
            "docs": docs,
            "manifest": manifest,
            "kb": kb,
            "pipeline_id": pipeline_id,
        }
        try:
            yield payload
        finally:
            for document_id in uploaded:
                try:
                    client.delete(
                        f"/api/v1/kb-admin/datasets/history/documents/{document_id}",
                        headers=headers,
                    )
                except Exception:
                    pass


def test_d_pipeline_health(golden_session):
    """D：部署后远端 DSL 表格并入正文、关闭问法；两份金标均解析成功。"""
    dsl = golden_session["dsl"]
    components = dsl.get("components") or {}
    parser = next(v for k, v in components.items() if k.startswith("Parser"))["obj"]["params"]
    assert parser.get("docx", {}).get("flatten_media_to_text") is True
    assert parser.get("docx", {}).get("remove_toc") is True
    extractor = next(v for k, v in components.items() if k.startswith("Extractor"))["obj"]["params"]
    assert extractor.get("questions", {}).get("enabled") is False
    assert int(extractor.get("questions", {}).get("top_n") or 0) == 0
    # 再拉一次远端，防止画布保存后重开问法
    live = golden_session["kb"].client_for("alpha").get_agent(golden_session["pipeline_id"])
    live_ext = next(
        v for k, v in (live.get("dsl") or {}).get("components", {}).items() if k.startswith("Extractor")
    )["obj"]["params"]
    assert live_ext.get("questions", {}).get("enabled") is False
    assert int(live_ext.get("questions", {}).get("top_n") or 0) == 0
    for doc in golden_session["docs"].values():
        assert doc["row"].get("status") in ("synced", "parsing") or int(doc["row"].get("chunk_count") or 0) > 0
        assert len(doc["chunks"]) > 0, doc["row"]


def test_a_chunk_quality(golden_session):
    """A：块数合理；表格/技术标记语进块；目录页不单独主导。"""
    for doc in golden_session["docs"].values():
        spec = doc["spec"]
        chunks = doc["chunks"]
        n = len(chunks)
        assert spec["min_chunks"] <= n <= spec["max_chunks"], (spec["id"], n)
        joined = "\n".join(c.get("content") or "" for c in chunks)
        for marker in spec["chunk_markers"]:
            assert marker in joined, f"{spec['id']} missing marker {marker!r}"
        # 纯目录短块不应占主导
        toc_only = 0
        for chunk in chunks:
            text = (chunk.get("content") or "").strip()
            if len(text) < 80 and "目录" in text and not any(m in text for m in spec["chunk_markers"]):
                toc_only += 1
        assert toc_only <= max(2, n // 10), (spec["id"], toc_only, n)


def test_b_extract_classify(golden_session):
    """B：技术段关键词非空；问法关闭；分类枚举若写出则落在允许集。"""
    manifest = golden_session["manifest"]
    allowed_role = set(manifest["allowed_content_role"])
    allowed_dtype = set(manifest["allowed_document_type"])
    allowed_reuse = set(manifest["allowed_reusability"])
    for doc in golden_session["docs"].values():
        chunks = doc["chunks"]
        tech_chunks = [
            c for c in chunks
            if any(m in (c.get("content") or "") for m in doc["spec"]["chunk_markers"])
        ]
        assert tech_chunks, doc["spec"]["id"]
        # 至少一块技术段有关键词（Extractor 生效）
        with_kw = [c for c in tech_chunks if c.get("important_keywords")]
        assert with_kw, f"{doc['spec']['id']} tech chunks have no keywords"
        for chunk in chunks:
            assert not (chunk.get("questions") or []), chunk.get("id")
            meta = chunk.get("metadata") or {}
            role = str(meta.get("content_role") or "").strip()
            dtype = str(meta.get("document_type") or "").strip()
            reuse = str(meta.get("reusability") or "").strip()
            if role:
                assert role in allowed_role, (doc["spec"]["id"], role)
            if dtype:
                assert dtype in allowed_dtype, (doc["spec"]["id"], dtype)
            if reuse:
                assert reuse in allowed_reuse, (doc["spec"]["id"], reuse)


def test_c_retrieval(golden_session):
    """C：字面查询命中对应金标；负例不误召回核心标记。"""
    client = golden_session["client"]
    headers = golden_session["headers"]
    overrides = dict(golden_session["manifest"].get("retrieval_overrides") or {})
    for doc in golden_session["docs"].values():
        for query in doc["spec"]["queries"]:
            resp = client.post(
                "/api/v1/kb-admin/retrieval-test",
                headers=headers,
                json={"query": query["q"], "kinds": ["history"], "limit": 8, **overrides},
            )
            assert resp.status_code == 200, resp.text
            body = resp.json()
            items = body.get("items") or []
            # 向量未就绪时再等一轮索引（解析 DONE 后偶发检索仍为空）
            if not items or body.get("skipped_reason") == "zero hits":
                time.sleep(20)
                resp = client.post(
                    "/api/v1/kb-admin/retrieval-test",
                    headers=headers,
                    json={"query": query["q"], "kinds": ["history"], "limit": 8, **overrides},
                )
                assert resp.status_code == 200, resp.text
                body = resp.json()
                items = body.get("items") or []
            assert items, (doc["spec"]["id"], query, body)
            hit_text = "\n".join(
                f"{it.get('filename') or ''} {it.get('quote') or it.get('content') or ''}" for it in items
            )
            assert query["expect_marker"] in hit_text, (doc["spec"]["id"], query, items[:3])

    neg = golden_session["manifest"]["negative_query"]
    resp = client.post(
        "/api/v1/kb-admin/retrieval-test",
        headers=headers,
        json={"query": neg["q"], "kinds": ["history"], "limit": 5, **overrides},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    hit_text = "\n".join(
        f"{it.get('quote') or it.get('content') or ''}" for it in (body.get("items") or [])
    )
    for marker in neg["forbid_markers"]:
        assert marker not in hit_text, (marker, body.get("items"))
