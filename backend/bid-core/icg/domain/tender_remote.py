# 为什么有这个文件：本地取不出文字的招标文件（扫描件 PDF、.doc、.xls/.xlsx、图片）交给公司自建 RAGFlow 的 DeepDOC 解析。
# 它解决什么问题：真实招标文件常有扫描页、老版 Word、Excel 评分表；本地 pypdf/docx 解析只能报 OCR_REQUIRED。
# 做法（见 docs/decisions/2026-10-28-kb-control-plane-and-pipelines.md 第 4 节）：
# 1. Word（.doc / .docx）先转成 PDF。RAGFlow 只对 PDF 使用 DeepDOC；Word 直接上传没有页码位置。
#    再上传到本公司 `icg-tender` 数据集（部署了 ICG“招标文件”摄入流程则走流程，否则内置 DeepDOC 解析）；
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

from icg.infra.ragflow_client import _audit_ragflow_io as _audit_ragflow

from .domain import DomainError
from .parsing import BATCH_PAGES, ParsedDocument, batch_ranges

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
# 招标解析临时数据集必须用公司知识库配置的内网嵌入；外网嵌入会在 Tokenizer 阶段出网失败（B5/B6）。
_EXTERNAL_EMBEDDING = ("jiekou", "openai.com", "api.openai", "google-gemini", "@gemini")
MISSING_LOCAL_EMBEDDING = (
    "知识库未配置本公司内网嵌入模型。请在「知识库配置」选择本地 Embedding（如 bge-m3），"
    "招标文件解析禁止使用外网嵌入。"
)


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
    """返回 (逐页文字, 是否有版面位置)。没有位置时所有分块放在第 1 页，并由调用方提示页码不可靠。

    分块跨页且行数与位置框数相同时逐行按各自位置归页（真实扫描件里一个分块常跨 2～3 页，
    整块归到首页会让后两页的条款页码错一页，原件上也定位不到）。"""
    placed: dict[int, list[tuple[float, int, str]]] = {}
    positioned = True
    for order, chunk in enumerate(chunks):
        split = _split_lines(chunk)
        if split and len({box[0] for _, box in split}) > 1:
            by_page: dict[int, list[tuple[str, list[float]]]] = {}
            for line, box in split:
                by_page.setdefault(box[0], []).append((line, box))
            for page, rows in by_page.items():
                text = "\n".join(line for line, _ in rows)
                placed.setdefault(page, []).append((rows[0][1][3], order, text))
            continue
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


def _boxes(chunk: dict) -> list[list[float]]:
    """DeepDOC 分块位置 [页码, x0, x1, top, bottom]，单位为 PDF 点（左上角为原点）。"""
    positions = chunk.get("positions") or []
    if len(positions) >= 5 and all(isinstance(v, (int, float)) for v in positions[:5]):
        positions = [positions]
    boxes = []
    for item in positions:
        try:
            page, x0, x1, top, bottom = (float(v) for v in item[:5])
        except (TypeError, ValueError):
            continue
        if x1 > x0 and bottom > top:
            boxes.append([max(1, int(page)), round(x0, 1), round(x1, 1), round(top, 1), round(bottom, 1)])
    return boxes


def _split_lines(chunk: dict) -> list[tuple[str, list[float]]]:
    """行数与位置框数相同时返回 [(去噪后的行, [页, x0, x1, top, bottom])]；否则返回空表。"""
    boxes = _boxes(chunk)
    lines = [line.strip() for line in html_to_text(str(chunk.get("content") or "")).splitlines() if line.strip()]
    if not boxes or len(lines) != len(boxes):
        return []
    return [(line, box) for line, box in zip(lines, boxes) if drop_ocr_noise(line).strip()]


def regions_from_chunks(chunks: list[dict]) -> list[list[dict]]:
    """逐页的“文字区域”，供原件 PDF 上按条款原句画高亮（APP-M2-T103）。

    扫描件没有文字层，浏览器无法在 PDF 里搜原句，只能用 DeepDOC 返回的位置框。
    分块行数与位置框数相同时逐行对应（高亮到行）；否则整块作为一个区域（高亮到段/表）。
    返回 pages[i] = [{"text": 区域文字, "boxes": [[x0, x1, top, bottom], ...]}]，与 pages_from_chunks 页码一致。"""
    placed: dict[int, list[dict]] = {}
    for chunk in chunks:
        boxes = _boxes(chunk)
        if not boxes:
            continue
        split = _split_lines(chunk)
        if split:
            for line, box in split:
                placed.setdefault(box[0], []).append({"text": line, "boxes": [box[1:]]})
            continue
        text = drop_ocr_noise(html_to_text(str(chunk.get("content") or ""))).strip()
        if not text:
            continue
        for page in sorted({box[0] for box in boxes}):
            placed.setdefault(page, []).append({"text": text, "boxes": [box[1:] for box in boxes if box[0] == page]})
    if not placed:
        return []
    return [placed.get(number, []) for number in range(1, max(placed) + 1)]


def remote_batch_pages() -> int:
    try:
        return max(1, int(os.environ.get("ICG_REMOTE_BATCH_PAGES", str(BATCH_PAGES))))
    except ValueError:
        return BATCH_PAGES


def split_pdf(data: bytes, size: int) -> list[tuple[int, int, bytes]] | None:
    """页数超过 size 的 PDF 按页码范围切成若干份；读不出页数（加密、损坏、未装 pypdf）时返回 None，整份提交。"""
    try:
        from io import BytesIO
        from pypdf import PdfReader, PdfWriter
        reader = PdfReader(BytesIO(data))
        if reader.is_encrypted or len(reader.pages) <= size:
            return None
        parts = []
        for first, last in batch_ranges(len(reader.pages), size):
            writer = PdfWriter()
            for index in range(first - 1, last):
                writer.add_page(reader.pages[index])
            output = BytesIO()
            writer.write(output)
            parts.append((first, last, output.getvalue()))
        return parts
    except Exception as exc:  # 切分失败不影响整份提交
        log.info("tender pdf split skipped: %s", type(exc).__name__)
        return None


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

    @staticmethod
    def embedding_is_external(model_id: str | None) -> bool:
        text = (model_id or "").strip().lower()
        if not text:
            return False
        # 本公司内网 OpenAI 兼容实例（instance=qwen）不算外网。
        if "@qwen@openai-api-compatible" in text:
            return False
        return any(marker in text for marker in _EXTERNAL_EMBEDDING)

    @staticmethod
    def explain_parse_failure(progress_msg: str) -> str:
        """把 RAGFlow 原始 progress_msg 收成可见、可重试的中文说明；禁止静默假成功。"""
        raw = (progress_msg or "").strip() or "未给出原因"
        lower = raw.lower()
        if any(marker in lower for marker in ("jiekou", "openai.com", "api.openai", "failed to send request", "embeddin")):
            return (
                f"RAGFlow 解析失败：嵌入/模型请求疑似出网或外网嵌入不可用。"
                f"请确认知识库嵌入为本公司内网模型后重试。原始原因：{raw[:240]}"
            )
        if "q_" in lower and "vec not found" in lower:
            return (
                f"RAGFlow 解析失败：数据集嵌入模型与向量库列不一致（曾改过嵌入却未重建）。"
                f"系统将在下次解析时重建招标临时数据集。原始原因：{raw[:240]}"
            )
        return f"RAGFlow 解析失败：{raw[:280]}"

    def resolve_embedding(self, client: Any, settings: dict) -> str:
        """优先用公司知识库配置的内网嵌入；未配时尝试 RAGFlow 上第一个非外网 embedding。"""
        configured = (settings.get("embedding_model") or "").strip()
        if configured and not self.embedding_is_external(configured):
            return configured
        try:
            models = client.list_models(model_type="embedding") or []
        except Exception:
            models = []
        for row in models:
            model_id = str((row or {}).get("id") or "").strip()
            if model_id and not self.embedding_is_external(model_id):
                return model_id
        raise DomainError(422, "RAGFLOW_EMBEDDING_REQUIRED", MISSING_LOCAL_EMBEDDING)

    def ensure_dataset(self, client: Any, company_id: str) -> str:
        """保证招标临时数据集使用公司配置的内网嵌入；嵌入不一致时删除重建，禁止沿用外网默认嵌入。"""
        from .knowledge_base import read_index, read_settings
        state = self.kb.repository.read()
        settings = read_settings(state, company_id)
        embedding = self.resolve_embedding(client, settings)
        record = read_index(state, company_id).get("tender_dataset") or {}
        dataset_id = str(record.get("dataset_id") or "")
        pipeline_id, mode = "", "builtin"
        current = None
        if dataset_id:
            try:
                current = client.get_dataset(dataset_id, company_id=company_id)
            except Exception:
                dataset_id, current = "", None
        wanted = f"{company_id}::{TENDER_DATASET}"
        if current is None:
            found = next((d for d in client.list_datasets(company_id=company_id, page_size=100) if d.name == wanted), None)
            if found is not None:
                current, dataset_id = found, found.id
        if current is not None and getattr(current, "embedding_model", "") != embedding:
            # 就地改嵌入会让 Infinity 向量列维度对不上（实测 q_1024_vec not found），必须删建。
            log.warning("tender dataset embedding mismatch for %s: %s -> %s; recreating",
                        company_id, getattr(current, "embedding_model", ""), embedding)
            try:
                client.delete_datasets([dataset_id])
            except Exception as exc:
                log.warning("tender dataset delete failed: %s", type(exc).__name__)
            dataset_id, current = "", None
        if current is None:
            # 默认内置 DeepDOC：真实扫描件实测按版面位置还原的页码准确（35/35 页）；ICG 招标流程按标题切块后
            # 只还原出 32 页、评分条款页码前移，条款原句无法按页回查。需要时用 ICG_TENDER_USE_PIPELINE=1 打开。
            if os.environ.get("ICG_TENDER_USE_PIPELINE", "0") == "1" and settings.get("use_pipelines"):
                try:
                    pipeline_id, _ = self.kb.ensure_pipeline(client, company_id, "tender", settings)
                except Exception as exc:
                    log.warning("tender pipeline unavailable for %s: %s", company_id, type(exc).__name__)
            if pipeline_id:
                dataset_id = client.create_pipeline_dataset(
                    TENDER_DATASET, pipeline_id, company_id=company_id,
                    embedding_model=embedding, language=settings.get("language") or "Chinese").id
                mode = "pipeline"
            else:
                dataset_id = client.create_dataset(
                    TENDER_DATASET, company_id=company_id, embedding_model=embedding).id
        self.kb._update_index(company_id, lambda index: index.__setitem__(
            "tender_dataset", {
                "dataset_id": dataset_id, "pipeline_id": pipeline_id, "mode": mode,
                "embedding_model": embedding,
            }))
        return dataset_id

    def submit(self, company_id: str, filename: str, data: bytes) -> RemoteOutcome:
        client = self.client(company_id)
        if client is None:
            _audit_ragflow("submit_skip", {"company_id": company_id, "filename": filename, "reason": "no_client"})
            return RemoteOutcome("failed", message="未连接 RAGFlow：扫描件、.doc、.xls 与图片须经知识库管理中连接的 RAGFlow 解析。")
        from .office_pdf import prepare_for_deepdoc
        prepared = prepare_for_deepdoc(filename, data)
        converted = False
        if isinstance(prepared, str):
            _audit_ragflow("submit_fail", {"company_id": company_id, "filename": filename, "reason": prepared})
            return RemoteOutcome("failed", message=prepared)
        if prepared is not None:
            filename, data = prepared
            converted = True
        suffix = PurePosixPath(filename).suffix.lower()
        parts = split_pdf(data, remote_batch_pages()) if suffix == ".pdf" else None
        uploaded: list[dict] = []
        dataset_id = ""
        _audit_ragflow("submit_start", {
            "company_id": company_id, "filename": filename, "bytes": len(data),
            "converted_to_pdf": converted, "suffix": suffix, "pdf_parts": len(parts or []),
        })
        try:
            dataset_id = self.ensure_dataset(client, company_id)
            if parts:
                # 超过单次页数上限：按页码范围分批提交，取回后按原页码合并（PRD §5.2.1 规则 1）
                stem = PurePosixPath(filename).stem
                for first, last, chunk in parts:
                    document = client.upload_file(dataset_id, f"{stem}-p{first}-{last}.pdf", chunk, MEDIA_TYPES[".pdf"])
                    uploaded.append({"document_id": document.id, "first_page": first, "last_page": last})
                client.trigger_parse(dataset_id, [p["document_id"] for p in uploaded])
            else:
                document = client.upload_file(dataset_id, filename, data, MEDIA_TYPES.get(suffix, "application/octet-stream"))
                client.trigger_parse(dataset_id, [document.id])
            _audit_ragflow("submit_uploaded", {
                "company_id": company_id, "dataset_id": dataset_id,
                "document_ids": [p["document_id"] for p in uploaded] if uploaded else [document.id],
                "parts": uploaded or None,
            })
        except DomainError as exc:
            for part in uploaded:
                self._cleanup(client, {"dataset_id": dataset_id, "document_id": part["document_id"]})
            _audit_ragflow("submit_fail", {"company_id": company_id, "error": exc.message})
            return RemoteOutcome("failed", message=exc.message)
        except Exception as exc:
            log.warning("tender remote submit failed for %s: %s", company_id, type(exc).__name__)
            for part in uploaded:
                self._cleanup(client, {"dataset_id": dataset_id, "document_id": part["document_id"]})
            _audit_ragflow("submit_fail", {"company_id": company_id, "error": type(exc).__name__})
            return RemoteOutcome("failed", message=f"RAGFlow 暂不可用（{type(exc).__name__}），原件仍保留，稍后重试。")
        if uploaded:
            outcome = self.poll(company_id, {"dataset_id": dataset_id, "document_id": uploaded[0]["document_id"],
                                             "parts": uploaded})
        else:
            outcome = self.poll(company_id, {"dataset_id": dataset_id, "document_id": document.id})
        if converted and outcome.state == "done" and outcome.document is not None:
            outcome.document.warnings = [
                "原件是 Word，已转成 PDF 后交 RAGFlow DeepDOC 按版面识别。页码对应转换后的 PDF。",
                *outcome.document.warnings,
            ]
        pages = len(outcome.document.pages) if outcome.document is not None else 0
        _audit_ragflow("submit_done", {
            "company_id": company_id, "state": outcome.state, "pages": pages,
            "message": (outcome.message or "")[:500],
        })
        return outcome

    def poll(self, company_id: str, remote: dict, *, budget: float | None = None) -> RemoteOutcome:
        client = self.client(company_id)
        if client is None:
            return RemoteOutcome("failed", remote=remote, message="RAGFlow 连接已断开，无法取回解析结果。")
        deadline = self.clock() + (wait_seconds() if budget is None else budget)
        if remote.get("parts"):
            return self._poll_parts(client, remote, deadline)
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
                return RemoteOutcome("failed", message=self.explain_parse_failure(document.progress_msg))
            if self.clock() >= deadline:
                percent = int(round((document.progress or 0) * 100))
                return RemoteOutcome("pending", remote=remote, message=f"RAGFlow 正在解析（{percent}%）")
            self.sleep(3)

    def _poll_parts(self, client: Any, remote: dict, deadline: float) -> RemoteOutcome:
        parts = remote["parts"]
        while True:
            progress = []
            for part in parts:
                try:
                    document = client.get_document_status(remote["dataset_id"], part["document_id"])
                except Exception as exc:
                    return RemoteOutcome("pending", remote=remote, message=f"暂时查不到解析进度（{type(exc).__name__}）")
                if document.sync_status == "failed":
                    for other in parts:
                        self._cleanup(client, {"dataset_id": remote["dataset_id"], "document_id": other["document_id"]})
                    detail = self.explain_parse_failure(document.progress_msg)
                    return RemoteOutcome(
                        "failed",
                        message=f"RAGFlow 解析第 {part['first_page']}～{part['last_page']} 页这一批失败：{detail.removeprefix('RAGFlow 解析失败：')}",
                    )
                progress.append(1.0 if document.sync_status == "synced" else float(document.progress or 0))
            if all(value >= 1.0 for value in progress):
                return self._collect_parts(client, remote)
            if self.clock() >= deadline:
                percent = int(round(sum(progress) / len(progress) * 100))
                done = sum(1 for value in progress if value >= 1.0)
                return RemoteOutcome("pending", remote=remote,
                                     message=f"RAGFlow 正在分 {len(parts)} 批解析（已完成 {done} 批，总进度 {percent}%）")
            self.sleep(3)

    def _collect_parts(self, client: Any, remote: dict) -> RemoteOutcome:
        """各批按自己的页数补齐或截断后首尾相接：第 2 批的第 1 页就是原件第 201 页，页码连续。"""
        pages: list[str] = []
        regions: list[list[dict]] = []
        positioned_all = True
        for part in remote["parts"]:
            chunks = self._chunks(client, remote["dataset_id"], part["document_id"])
            count = part["last_page"] - part["first_page"] + 1
            part_pages, positioned = pages_from_chunks(chunks)
            positioned_all = positioned_all and positioned
            part_regions = regions_from_chunks(chunks) if positioned else []
            pages.extend((part_pages + [""] * count)[:count])
            regions.extend((part_regions + [[] for _ in range(count)])[:count])
            self._cleanup(client, {"dataset_id": remote["dataset_id"], "document_id": part["document_id"]})
        if not any(p.strip() for p in pages):
            return RemoteOutcome("failed", message="RAGFlow 已解析但没有识别出文字，请提供更清晰的扫描件或原始电子版。")
        batches = [[p["first_page"], p["last_page"]] for p in remote["parts"]]
        warnings = [REMOTE_WARNING, f"共 {len(pages)} 页，按每批 {remote_batch_pages()} 页分 {len(batches)} 批提交 RAGFlow，"
                                    "取回后按原页码合并。"]
        if not positioned_all:
            warnings.append("部分批次 RAGFlow 未返回版面位置，这些页的内容按该批第 1 页处理，页码不可用于定位。")
        return RemoteOutcome("done", ParsedDocument(pages=pages, pagination=PAGINATION, warnings=warnings,
                                                    regions=regions if any(regions) else [], batches=batches))

    @staticmethod
    def _chunks(client: Any, dataset_id: str, document_id: str) -> list[dict]:
        chunks: list[dict] = []
        page = 1
        while True:
            batch = client.list_chunks(dataset_id, document_id, page=page, page_size=100)
            rows = batch.get("chunks") or []
            chunks.extend(rows)
            if not rows or len(chunks) >= int(batch.get("total") or 0) or page > 200:
                break
            page += 1
        return chunks

    def _collect(self, client: Any, remote: dict) -> RemoteOutcome:
        chunks = self._chunks(client, remote["dataset_id"], remote["document_id"])
        pages, positioned = pages_from_chunks(chunks)
        self._cleanup(client, remote)
        if not any(p.strip() for p in pages):
            return RemoteOutcome("failed", message="RAGFlow 已解析但没有识别出文字，请提供更清晰的扫描件或原始电子版。")
        warnings = [REMOTE_WARNING] + ([] if positioned else ["RAGFlow 未返回版面位置，全部内容按第 1 页处理，页码不可用于定位。"])
        regions = regions_from_chunks(chunks) if positioned else []
        regions = (regions + [[] for _ in range(len(pages) - len(regions))])[:len(pages)] if regions else []
        return RemoteOutcome("done", ParsedDocument(pages=pages, pagination=PAGINATION, warnings=warnings, regions=regions))

    @staticmethod
    def _cleanup(client: Any, remote: dict) -> None:
        try:
            client.delete_documents(remote["dataset_id"], [remote["document_id"]])
        except Exception as exc:  # 删除失败不影响解析结果；临时文档留在本公司数据集
            log.info("tender remote cleanup failed: %s", type(exc).__name__)
