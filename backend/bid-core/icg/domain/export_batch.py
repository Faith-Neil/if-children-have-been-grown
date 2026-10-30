# 为什么有这个文件：导出批次的原子生成与历史快照（APP-M2-T202，PRD v1.8 §5.9.1 规则 13、异常，§5.9.3 bid_export）。
# 它解决什么问题：
# 1. 同一次导出的各分册文件共用一个批次号（export_batch_no），递交版的技术、商务两册与合标核对清单同批绑定同一次检查与定稿；
# 2. 导出时就把每册 Word 真正生成出来；任何一册生成失败，本批次整体记为“失败”，不留下任何可下载文件，不产生部分成功的递交版；
# 3. 生成好的 Word 按内容摘要存入文件存储，成为不可改的快照：之后正文再改或分册解锁，旧批次标“已过期”但仍可下载原文件，
#    下载时照常重核当前权限（递交版仍只限项目负责人）。

from __future__ import annotations

import hashlib
import json
from datetime import datetime

from icg.domain.domain import Export

BATCH_PREFIX = {"submission": "S", "internal": "I", "internal_review": "I"}


class ExportRenderError(Exception):
    def __init__(self, volume: str, message: str):
        super().__init__(message)
        self.volume = volume
        self.message = message


def next_batch_no(workflow: dict, kind: str, now: datetime) -> str:
    """批次号：S（递交版）/ I（内部稿）+ 北京时间日期 + 当日序号，如 S20261029-002。失败批次也占号，便于追查。"""
    prefix = f"{BATCH_PREFIX.get(kind, 'I')}{now.strftime('%Y%m%d')}-"
    taken = [r.get("batch_no", "") for r in workflow["exports"].values() if str(r.get("batch_no", "")).startswith(prefix)]
    sequence = max((int(no[len(prefix):]) for no in taken if no[len(prefix):].isdigit()), default=0) + 1
    return f"{prefix}{sequence:03d}"


def docx_meta(document: dict):
    from icg.infra.docx_style import DocxMeta
    cover = document.get("cover")
    return DocxMeta(**cover) if cover else None


def _render(volume: str, document: dict, filename: str) -> bytes:
    from icg.infra.docx_style import build_docx
    record = Export("", "", 1, "", "", filename, document["title"], document["content"])
    data = build_docx(record, project_name=document.get("project_name"), meta=docx_meta(document))
    if not data or data[:2] != b"PK":
        raise ExportRenderError(volume, "生成的 Word 文件不完整")
    return data


def render_batch(documents: dict, volumes: list[dict], render=_render) -> None:
    """先把全部分册都生成成功，再统一写入文件存储；有一册失败就抛出，不写任何快照。"""
    from icg.infra.blob_store import put_blob
    rendered: list[tuple[dict, bytes]] = []
    for entry in volumes:
        volume = entry["volume"]
        try:
            data = render(volume, documents[volume], entry["filename"])
        except ExportRenderError:
            raise
        except Exception as error:  # 模板、附件或版式处理失败
            raise ExportRenderError(volume, f"{type(error).__name__}") from error
        rendered.append((entry, data))
    for entry, data in rendered:
        entry.update(blob=put_blob(data), docx_sha256=hashlib.sha256(data).hexdigest(), size_bytes=len(data))


def volume_bindings(workflow: dict, volumes: list[str]) -> dict:
    """本批次绑定的分册定稿：定稿人、时间与定稿快照摘要（内部稿未定稿时记为未定稿）。"""
    states = workflow.get("volumes", {})
    bound = {}
    for volume in volumes:
        record = states.get(volume, {})
        snapshot = record.get("snapshot")
        bound[volume] = {
            "is_finalized": bool(record.get("is_finalized")),
            "finalized_by": record.get("finalized_by"),
            "finalized_at": record.get("finalized_at"),
            "snapshot_sha256": hashlib.sha256(json.dumps(snapshot, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
            if snapshot is not None else None,
        }
    return bound


def failed_record(identity: str, batch_no: str, kind: str, check: dict, created_at: str, error: ExportRenderError,
                  scope: str) -> dict:
    names = {"technical": "技术分册", "business": "商务分册"}
    return {
        "id": identity, "batch_no": batch_no, "kind": kind, "check_id": check["id"], "fingerprint": check["fingerprint"],
        "created_at": created_at, "excludes_drafts": True, "volumes": [], "documents": {}, "volume": scope,
        "has_blockers": False, "compliance_notice": None, "is_submission": kind == "submission",
        "export_status": "failed", "failed_volume": error.volume,
        "error_message": f"{names.get(error.volume, error.volume)}生成失败（{error.message}），本批次整体作废，未产生任何可下载文件；"
                         "已提交正文与定稿未受影响，请处理后重新导出。",
    }
