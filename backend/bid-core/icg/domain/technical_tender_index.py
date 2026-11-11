# 为什么有这个文件：当前招标单独建项目级索引，写正文和写作助手先检索本标切片。
# 它解决什么问题：DeepDoc 只出文字页时没有向量库；公司 history/materials 里别的项目切片会进 prompt。禁止写入公司双库。

from __future__ import annotations

import logging
import re
from typing import Any

log = logging.getLogger(__name__)

TOKEN = re.compile(r"[\u4e00-\u9fff]{2}|[A-Za-z0-9]{2,}")
FORBIDDEN_KINDS = frozenset({"history", "materials", "library", "snippet"})


def project_dataset_suffix(project_id: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_-]+", "-", project_id).strip("-") or "project"
    return f"project-tender-{slug[:48]}"


def chunk_pages(pages: list[str], *, file_id: str = "", size: int = 700) -> list[dict]:
    chunks: list[dict] = []
    for page_no, page in enumerate(pages, start=1):
        text = str(page or "").strip()
        if not text:
            continue
        if len(text) <= size:
            chunks.append({"id": f"{file_id}:{page_no}:0", "file_id": file_id, "page": page_no, "text": text})
            continue
        start = 0
        index = 0
        while start < len(text):
            piece = text[start:start + size].strip()
            if piece:
                chunks.append({
                    "id": f"{file_id}:{page_no}:{index}",
                    "file_id": file_id,
                    "page": page_no,
                    "text": piece,
                })
                index += 1
            start += size
    return chunks


def build_local_index(workflow: dict) -> dict[str, Any]:
    chunks: list[dict] = []
    for file_id, record in (workflow.get("files") or {}).items():
        pages = []
        for page in record.get("pages") or []:
            pages.append(page if isinstance(page, str) else str(page.get("text") or ""))
        chunks.extend(chunk_pages(pages, file_id=str(file_id)))
    index = {
        "backend": "local",
        "dataset_id": "",
        "dataset_name": "workflow.pages",
        "chunk_count": len(chunks),
        "chunks": chunks,
        "skip_reason": "" if chunks else "no tender pages",
    }
    workflow["tender_index"] = index
    return index


def _tokens(text: str) -> set[str]:
    return set(TOKEN.findall(text or ""))


def _lexical(chunks: list[dict], query: str, *, limit: int = 8) -> list[dict]:
    wanted = _tokens(query)
    if not wanted:
        return []
    ranked: list[tuple[int, dict]] = []
    for chunk in chunks:
        score = len(wanted & _tokens(chunk.get("text") or ""))
        if score:
            ranked.append((score, chunk))
    ranked.sort(key=lambda item: (-item[0], item[1].get("page") or 0))
    hits = []
    for score, chunk in ranked[:limit]:
        hits.append({
            "id": chunk.get("id") or "",
            "name": f"本标第{chunk.get('page') or '?'}页",
            "content": chunk.get("text") or "",
            "score": float(score),
            "dataset_kind": "tender",
            "reference_only": False,
            "document_id": chunk.get("file_id") or "",
            "chunk_id": chunk.get("id") or "",
            "cite_tag": f"[标:p{chunk.get('page') or 0}]",
            "page": chunk.get("page"),
        })
    return hits


def _ensure_ragflow_dataset(kb: Any, company_id: str, project_id: str, index: dict) -> dict:
    """把本标页写入独立数据集。失败时保留本地索引。绝不写入 history/materials。"""
    if kb is None or not company_id or not project_id:
        return index
    try:
        state = kb.repository.read() if getattr(kb, "repository", None) else None
        client = kb.client_for(company_id, state) if hasattr(kb, "client_for") else None
    except Exception as exc:
        index["skip_reason"] = f"client:{type(exc).__name__}"
        return index
    if client is None:
        index["skip_reason"] = "RAGFlow is not configured"
        return index
    suffix = project_dataset_suffix(project_id)
    name = f"{company_id}::{suffix}"
    if any(part in suffix for part in ("icg-history", "icg-material")):
        index["skip_reason"] = "refused company dataset name"
        return index
    try:
        found = next((item for item in client.list_datasets(company_id=company_id, page_size=100) if item.name == name), None)
        dataset_id = found.id if found is not None else client.create_dataset(suffix, company_id=company_id).id
        blob = "\n\n".join(
            f"[p{chunk.get('page')}] {chunk.get('text')}" for chunk in (index.get("chunks") or [])[:80]
        ).encode("utf-8")
        document = client.upload_file(dataset_id, f"{project_id}-tender.txt", blob, "text/plain")
        if hasattr(client, "trigger_parse"):
            client.trigger_parse(dataset_id, [document.id])
        index["backend"] = "ragflow"
        index["dataset_id"] = dataset_id
        index["dataset_name"] = name
        index["document_id"] = getattr(document, "id", "")
        index["skip_reason"] = ""
    except Exception as exc:
        log.warning("project tender index skipped for %s: %s", project_id, type(exc).__name__)
        index["skip_reason"] = type(exc).__name__
        index["backend"] = "local"
    return index


def index_current_tender(workflow: dict, *, kb: Any = None, company_id: str = "", project_id: str = "") -> dict:
    index = build_local_index(workflow)
    if index.get("chunks") and kb is not None:
        _ensure_ragflow_dataset(kb, company_id, project_id, index)
        workflow["tender_index"] = index
    return index


def retrieve_tender(workflow: dict, query: str, *, kb: Any = None, company_id: str = "",
                    limit: int = 8) -> tuple[list[dict], dict]:
    index = workflow.get("tender_index") or build_local_index(workflow)
    audit = {
        "query": query,
        "tender_searched": False,
        "tender_hits": 0,
        "tender_dataset": index.get("dataset_name") or "workflow.pages",
        "tender_backend": index.get("backend") or "local",
        "skip_reason": "",
        "top": [],
    }
    if index.get("backend") in FORBIDDEN_KINDS:
        audit["skip_reason"] = "refused company dataset"
        return [], audit
    hits: list[dict] = []
    dataset_id = str(index.get("dataset_id") or "")
    if dataset_id and kb is not None and company_id:
        try:
            state = kb.repository.read() if getattr(kb, "repository", None) else None
            client = kb.client_for(company_id, state) if hasattr(kb, "client_for") else None
            if client is not None:
                result = client.retrieve(question=(query or "")[:2000], dataset_ids=[dataset_id], page_size=max(limit, 8))
                audit["tender_searched"] = True
                for chunk in (getattr(result, "chunks", None) or [])[:limit]:
                    hits.append({
                        "id": getattr(chunk, "id", "") or "",
                        "name": "本标切片",
                        "content": getattr(chunk, "content", "") or "",
                        "score": float(getattr(chunk, "similarity", 0) or 0),
                        "dataset_kind": "tender",
                        "reference_only": False,
                        "document_id": getattr(chunk, "document_id", "") or "",
                        "chunk_id": getattr(chunk, "id", "") or "",
                        "cite_tag": f"[标:{getattr(chunk, 'id', '')[:8]}]",
                    })
        except Exception as exc:
            audit["skip_reason"] = type(exc).__name__
    if not hits:
        hits = _lexical(index.get("chunks") or [], query, limit=limit)
        audit["tender_searched"] = True
        if not hits and not audit["skip_reason"]:
            audit["skip_reason"] = index.get("skip_reason") or "zero tender hits"
    audit["tender_hits"] = len(hits)
    audit["top"] = [{"name": item.get("name"), "dataset_kind": "tender", "score": item.get("score")} for item in hits[:8]]
    return hits, audit
