# 为什么有这个文件：本地取不出文字的招标文件（扫描件 PDF、.doc、.xls/.xlsx、图片）交给公司自建 RAGFlow 的 DeepDOC 解析。
# 它解决什么问题：真实招标文件常有扫描页、老版 Word、Excel 评分表；本地 pypdf/docx 解析只能报 OCR_REQUIRED。
# 做法（见 docs/decisions/2026-10-28-kb-control-plane-and-pipelines.md 第 4 节）：
# 1. 上传到本公司 `icg-tender` 数据集（部署了 ICG“招标文件”摄入流程则走流程，否则内置 DeepDOC 解析）；
# 2. 在限定时间内轮询；未完成则文件标为 parsing_remote，下次点“开始解析”接着查，不重复上传；
# 3. 完成后按分块的版面位置（页码、纵坐标）还原逐页文字，交回原有条款/事实抽取；随后删除 RAGFlow 中的临时文档。
# 条款抽取仍不依赖向量检索；RAGFlow 只用来“看懂版面、识别文字”。

from __future__ import annotations

import html
import logging
import os
import re
import time
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any

from .domain import DomainError
from .parsing import ParsedDocument

log = logging.getLogger(__name__)

TENDER_DATASET = "icg-tender"
REMOTE_SUFFIXES = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".png", ".jpg", ".jpeg"}
FALLBACK_CODES = {"OCR_REQUIRED", "FILE_TYPE_UNSUPPORTED"}
MEDIA_TYPES = {
    ".pdf": "application/pdf", ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xls": "application/vnd.ms-excel", ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
}
PAGINATION = "ragflow_deepdoc_positions"
REMOTE_WARNING = "经 RAGFlow DeepDOC 版面识别（含 OCR）提取文字，页码按版面位置还原；识别可能有误，请对照原件核对。"


def wait_seconds() -> float:
    try:
        return max(0.0, float(os.environ.get("ICG_TENDER_REMOTE_WAIT", "60")))
    except ValueError:
        return 60.0


def html_to_text(text: str) -> str:
    """DeepDOC 把表格输出成 HTML：行转换行、单元格用“ | ”分隔，其余标签去掉。"""
    if "<" not in text:
        return text
    value = re.sub(r"(?i)</tr\s*>", "\n", text)
    value = re.sub(r"(?i)</t[dh]\s*>", " | ", value)
    value = re.sub(r"(?i)<br\s*/?>", "\n", value)
    value = re.sub(r"<[^>]+>", "", value)
    lines = [re.sub(r"\s*\|\s*$", "", line).strip() for line in html.unescape(value).splitlines()]
    return "\n".join(line for line in lines if line)


_NOISE = re.compile(r"^([A-Za-z0-9]{1,3}|[\u4e00-\u9fa5]{1,2})$")
_WATERMARK = re.compile(r"水印|试用|^仅供|^样本$")


def drop_ocr_noise(text: str) -> str:
    """去掉扫描件水印与页边残字（单独成行的 1～2 个汉字或 1～3 个字母数字，如“全波”“TV”，以及“试用水”等水印字样）；带数字或标点的短行保留。"""
    lines = [line for line in text.splitlines()
             if not (_NOISE.match(line.strip()) or (len(line.strip()) <= 6 and _WATERMARK.search(line.strip())))]
    return "\n".join(lines)


def _position(chunk: dict) -> tuple[int, float] | None:
    positions = chunk.get("positions") or []
    if positions and isinstance(positions[0], (list, tuple)) and len(positions[0]) >= 4:
        first = positions[0]
    elif len(positions) >= 4 and all(isinstance(v, (int, float)) for v in positions[:4]):
        first = positions
    else:
        return None
    try:
        return max(1, int(first[0])), float(first[3])
    except (TypeError, ValueError):
        return None


def pages_from_chunks(chunks: list[dict]) -> tuple[list[str], bool]:
    """返回 (逐页文字, 是否有版面位置)。没有位置时所有分块放在第 1 页，并由调用方提示页码不可靠。"""
    placed: dict[int, list[tuple[float, int, str]]] = {}
    positioned = True
    for order, chunk in enumerate(chunks):
        text = drop_ocr_noise(html_to_text(str(chunk.get("content") or ""))).strip()
        if not text:
            continue
        where = _position(chunk)
        if where is None:
            positioned = False
            where = (1, float(order))
        placed.setdefault(where[0], []).append((where[1], order, text))
    if not placed:
        return [], positioned
    last = max(placed)
    pages = ["\n".join(text for _, _, text in sorted(placed.get(number, []))) for number in range(1, last + 1)]
    return pages, positioned


@dataclass
class RemoteOutcome:
    state: str                      # done / pending / failed
    document: ParsedDocument | None = None
    remote: dict | None = None      # {"dataset_id", "document_id"}
    message: str = ""


class RemoteTenderParser:
    def __init__(self, knowledge_base: Any, *, sleep=time.sleep, clock=time.monotonic):
        self.kb = knowledge_base
        self.sleep, self.clock = sleep, clock

    def client(self, company_id: str) -> Any:
        return self.kb.client_for(company_id) if self.kb is not None else None

    @staticmethod
    def eligible(filename: str, error: DomainError) -> bool:
        return error.code in FALLBACK_CODES and PurePosixPath(filename).suffix.lower() in REMOTE_SUFFIXES

    def ensure_dataset(self, client: Any, company_id: str) -> str:
        from .knowledge_base import read_index, read_settings
        state = self.kb.repository.read()
        record = read_index(state, company_id).get("tender_dataset") or {}
        dataset_id = record.get("dataset_id", "")
        if dataset_id:
            try:
                client.get_dataset(dataset_id, company_id=company_id)
                return dataset_id
            except Exception:
                dataset_id = ""
        wanted = f"{company_id}::{TENDER_DATASET}"
        found = next((d for d in client.list_datasets(company_id=company_id, page_size=100) if d.name == wanted), None)
        settings = read_settings(state, company_id)
        pipeline_id, mode = "", "builtin"
        if found is not None:
            dataset_id = found.id
        else:
            if settings.get("use_pipelines"):
                try:
                    pipeline_id, _ = self.kb.ensure_pipeline(client, company_id, "tender", settings)
                except Exception as exc:
                    log.warning("tender pipeline unavailable for %s: %s", company_id, type(exc).__name__)
            if pipeline_id:
                dataset_id = client.create_pipeline_dataset(TENDER_DATASET, pipeline_id, company_id=company_id,
                                                            embedding_model=settings.get("embedding_model") or None,
                                                            language=settings.get("language") or "Chinese").id
                mode = "pipeline"
            else:
                dataset_id = client.create_dataset(TENDER_DATASET, company_id=company_id,
                                                   embedding_model=settings.get("embedding_model") or None).id
        self.kb._update_index(company_id, lambda index: index.__setitem__(
            "tender_dataset", {"dataset_id": dataset_id, "pipeline_id": pipeline_id, "mode": mode}))
        return dataset_id

    def submit(self, company_id: str, filename: str, data: bytes) -> RemoteOutcome:
        client = self.client(company_id)
        if client is None:
            return RemoteOutcome("failed", message="未连接 RAGFlow：扫描件、.doc、.xls 与图片须经知识库管理中连接的 RAGFlow 解析。")
        try:
            dataset_id = self.ensure_dataset(client, company_id)
            suffix = PurePosixPath(filename).suffix.lower()
            document = client.upload_file(dataset_id, filename, data, MEDIA_TYPES.get(suffix, "application/octet-stream"))
            client.trigger_parse(dataset_id, [document.id])
        except Exception as exc:
            log.warning("tender remote submit failed for %s: %s", company_id, type(exc).__name__)
            return RemoteOutcome("failed", message=f"RAGFlow 暂不可用（{type(exc).__name__}），原件仍保留，稍后重试。")
        return self.poll(company_id, {"dataset_id": dataset_id, "document_id": document.id})

    def poll(self, company_id: str, remote: dict, *, budget: float | None = None) -> RemoteOutcome:
        client = self.client(company_id)
        if client is None:
            return RemoteOutcome("failed", remote=remote, message="RAGFlow 连接已断开，无法取回解析结果。")
        deadline = self.clock() + (wait_seconds() if budget is None else budget)
        while True:
            try:
                document = client.get_document_status(remote["dataset_id"], remote["document_id"])
            except Exception as exc:
                return RemoteOutcome("pending", remote=remote, message=f"暂时查不到解析进度（{type(exc).__name__}）")
            status = document.sync_status
            if status == "synced":
                return self._collect(client, remote)
            if status == "failed":
                self._cleanup(client, remote)
                return RemoteOutcome("failed", message=f"RAGFlow 解析失败：{(document.progress_msg or '未给出原因')[:200]}")
            if self.clock() >= deadline:
                percent = int(round((document.progress or 0) * 100))
                return RemoteOutcome("pending", remote=remote, message=f"RAGFlow 正在解析（{percent}%）")
            self.sleep(3)

    def _collect(self, client: Any, remote: dict) -> RemoteOutcome:
        chunks: list[dict] = []
        page = 1
        while True:
            batch = client.list_chunks(remote["dataset_id"], remote["document_id"], page=page, page_size=100)
            rows = batch.get("chunks") or []
            chunks.extend(rows)
            if not rows or len(chunks) >= int(batch.get("total") or 0) or page > 200:
                break
            page += 1
        pages, positioned = pages_from_chunks(chunks)
        self._cleanup(client, remote)
        if not any(p.strip() for p in pages):
            return RemoteOutcome("failed", message="RAGFlow 已解析但没有识别出文字，请提供更清晰的扫描件或原始电子版。")
        warnings = [REMOTE_WARNING] + ([] if positioned else ["RAGFlow 未返回版面位置，全部内容按第 1 页处理，页码不可用于定位。"])
        return RemoteOutcome("done", ParsedDocument(pages=pages, pagination=PAGINATION, warnings=warnings))

    @staticmethod
    def _cleanup(client: Any, remote: dict) -> None:
        try:
            client.delete_documents(remote["dataset_id"], [remote["document_id"]])
        except Exception as exc:  # 删除失败不影响解析结果；临时文档留在本公司数据集
            log.info("tender remote cleanup failed: %s", type(exc).__name__)
