# 为什么有这个文件：招标文件的类型、版本链与同公司解析结果复用（APP-M2-T101 / PRD v1.8 §5.2.1、§5.2.3 tender_file）。
# 它解决什么问题：
# 1. 文件类型（招标文件 / 澄清 / 补遗 / 技术规范书 / 合同条款 / 附件）决定抽取后处理怎么对待它：澄清和补遗按版本链修改更早的条款；
# 2. 版本链：上传新版后把旧版“设为被替代”，旧版条目标“所在文件已被替代”，不删除，可查；
# 3. 同一文件（SHA-256 指纹）在本公司已用同一解析服务和参数解析过时直接复用结果，不跨公司复用（§5.2.1 规则 3）；
#    复用记录只存解析结果的内容摘要，正文放文件存储，不进业务状态。

from __future__ import annotations

import json
from typing import Any

FILE_ROLES: dict[str, str] = {
    "tender": "招标文件", "clarification": "澄清", "addendum": "补遗",
    "tech_spec": "技术规范书", "contract": "合同条款", "attachment": "附件",
}
AMENDING_ROLES = {"clarification", "addendum"}  # 按版本链修改更早文件的条款
SERVICES: dict[str, str] = {"auto": "自动选择", "local": "本地文字提取", "ragflow": "RAGFlow DeepDOC（版面识别与 OCR）"}
LOCAL_SERVICE = ("local-text", "local-text-1")          # (服务, 参数版本)
REMOTE_SERVICE = ("ragflow-deepdoc", "deepdoc-builtin-1")
SERVICE_LABELS = {LOCAL_SERVICE[0]: "本地文字提取", REMOTE_SERVICE[0]: "RAGFlow DeepDOC"}
CACHE_STORE = "tender_parse_cache"


def role(record: dict) -> str:
    return record.get("file_role") or "tender"


def amending(record: dict) -> bool:
    return role(record) in AMENDING_ROLES


def superseded(record: dict) -> bool:
    return bool(record.get("superseded_by"))


def order(workflow: dict) -> dict[str, tuple[int, int]]:
    """版本链先后：招标文件、技术规范书、合同条款、附件在前；澄清和补遗按上传先后在后。"""
    return {identity: (1 if amending(record) else 0, position)
            for position, (identity, record) in enumerate((workflow.get("files") or {}).items())}


def effective_files(workflow: dict) -> list[dict]:
    """未被替代的文件（确认解析结果只看这些）。"""
    return [f for f in (workflow.get("files") or {}).values() if not superseded(f)]


def public_fields(record: dict) -> dict:
    return {
        "file_role": role(record), "file_role_label": FILE_ROLES.get(role(record), role(record)),
        "version_no": int(record.get("version_no") or 1), "supersedes_id": record.get("supersedes_id"),
        "superseded_by": record.get("superseded_by"), "superseded_reason": record.get("superseded_reason", ""),
        "uploaded_by": record.get("uploaded_by"), "uploaded_by_name": record.get("uploaded_by_name", ""),
        "uploaded_at": record.get("uploaded_at"), "parse_service": record.get("parse_service"),
        "parse_service_label": SERVICE_LABELS.get(str(record.get("parse_service") or ""), ""),
        "parse_started_at": record.get("parse_started_at"), "parse_finished_at": record.get("parse_finished_at"),
        "parse_duration_ms": record.get("parse_duration_ms"), "reused": bool(record.get("reused_from")),
        "reused_at": (record.get("reused_from") or {}).get("parsed_at"), "batches": record.get("batches") or [],
    }


# ---------------------------------------------------------------- 同公司解析结果复用

def _cache(state: Any, company_id: str) -> dict:
    return ((getattr(state, "service_stores", {}) or {}).get(CACHE_STORE) or {}).get(company_id) or {}


def cache_key(sha256: str, service: tuple[str, str]) -> str:
    return f"{sha256}:{service[0]}:{service[1]}"


def cached(state: Any, company_id: str, sha256: str, service: tuple[str, str]):
    """本公司同指纹、同服务、同参数的解析结果；没有或正文已丢失时返回 None。"""
    entry = _cache(state, company_id).get(cache_key(sha256, service))
    if not entry:
        return None
    from icg.infra.blob_store import get_blob
    from .parsing import ParsedDocument
    try:
        data = json.loads(get_blob(entry["result_blob"]).decode("utf-8"))
    except (OSError, ValueError, KeyError):
        return None
    document = ParsedDocument(pages=data["pages"], pagination=data["pagination"], warnings=data.get("warnings") or [],
                              regions=data.get("regions") or [])
    document.batches = data.get("batches") or []  # type: ignore[attr-defined]
    return document, entry


def remember(state: Any, company_id: str, sha256: str, service: tuple[str, str], document: Any, now: str) -> None:
    from icg.infra.blob_store import put_blob
    body = {"pages": document.pages, "pagination": document.pagination, "warnings": document.warnings,
            "regions": getattr(document, "regions", []) or [], "batches": getattr(document, "batches", []) or []}
    digest = put_blob(json.dumps(body, ensure_ascii=False).encode("utf-8"))
    store = state.service_stores.setdefault(CACHE_STORE, {}).setdefault(company_id, {})
    store[cache_key(sha256, service)] = {"service": service[0], "params_version": service[1], "result_blob": digest,
                                         "page_count": len(document.pages), "parsed_at": now}
