# 为什么有这个文件：技术分册的矩阵响应从历史标书取做法。
# 它解决什么问题：历史做法要和本次招标条款比较。高于要求是正偏离，低于要求是负偏离，正好符合才是无偏离。

from __future__ import annotations

import json
import re
from typing import Any, Callable

from icg.domain.domain import DomainError

BOOK = re.compile(r"《[^》]{2,40}》")
JUDGMENT = re.compile(r"\{.*\}", re.S)
KINDS = {
    "无偏离": ("comply", "none"),
    "正偏离": ("exceed", "positive"),
    "负偏离": ("deviate", "negative"),
}
JUDGE_SYSTEM = (
    "你只判断历史做法相对本次招标条款是更高、更低，还是正好符合。"
    "只输出一行 JSON：{\"deviation\":\"无偏离|正偏离|负偏离\",\"reason\":\"...\"}。"
    "高于招标要求是正偏离，低于招标要求是负偏离，正好符合才是无偏离。"
    "正偏离要写明优在哪一项、优多少。负偏离要写明哪一项做不到。"
    "不要编造项目名称、报价、人员和证书。"
)
_search_fn: Callable[[str], list[dict]] | None = None
_draft_fn: Callable[[str], str] | None = None
_judge_fn: Callable[[str, str], dict] | None = None


def bind_history_search(fn: Callable[[str], list[dict]] | None):
    global _search_fn
    previous = _search_fn
    _search_fn = fn
    return previous


def reset_history_search(previous) -> None:
    global _search_fn
    _search_fn = previous


def bind_history_draft(fn: Callable[[str], str] | None):
    global _draft_fn
    previous = _draft_fn
    _draft_fn = fn
    return previous


def reset_history_draft(previous) -> None:
    global _draft_fn
    _draft_fn = previous


def bind_deviation_judge(fn: Callable[[str, str], dict] | None):
    global _judge_fn
    previous = _judge_fn
    _judge_fn = fn
    return previous


def reset_deviation_judge(previous) -> None:
    global _judge_fn
    _judge_fn = previous


def visible_quote(quote: str, clause: str) -> str:
    """去掉本次条款里没有的其他项目名称。数字留给偏离判断。"""

    def book(match: re.Match[str]) -> str:
        return match.group(0) if match.group(0) in clause else ""

    return re.sub(r"\s+", " ", BOOK.sub(book, quote or "")).strip()


def parse_judgment(text: str) -> dict:
    matched = JUDGMENT.search(text or "")
    if matched is None:
        raise ValueError("模型没有给出偏离判断")
    data = json.loads(matched.group(0))
    deviation = str(data.get("deviation") or "")
    if deviation not in KINDS:
        raise ValueError("偏离判断只能是无偏离、正偏离或负偏离")
    return {"deviation": deviation, "reason": str(data.get("reason") or "").strip()}


def judge_deviation(clause: str, quote: str, model: Any = None) -> dict:
    """有注入的判断时用注入结果。否则只把条款和历史做法交给本地模型。"""
    if _judge_fn is not None:
        return parse_judgment(json.dumps(_judge_fn(clause, quote), ensure_ascii=False))
    if model is None or not getattr(model, "is_real_model", False) or getattr(model, "is_local", False) is False:
        raise RuntimeError("没有本地模型，不能判断历史做法是否偏离")
    url = getattr(model, "base_url", "") or ""
    if url:
        from icg.infra.openai_model import is_public_model_url
        if is_public_model_url(url):
            raise RuntimeError("本地部署已打开，公网地址不能判断偏离")
    return parse_judgment(model.suggest(JUDGE_SYSTEM, f"本次招标条款：{clause}\n历史做法：{quote}"))


def local_draft(clause: str) -> str:
    """没有接通本地模型时的替身。只复述本次条款，不写其他项目。"""
    return f"无偏离。按本次招标文件响应「{clause}」。"


def _fail(row: dict, origin: str) -> None:
    row.update(response="", response_type=None, deviation_type=None, response_origin=origin,
               history_filename="", history_quote="", status="pending")


def _hit_source(item: dict) -> str:
    return str(item.get("source") or "history")


def _material_sources(hits: list[dict]) -> list[dict]:
    return [
        {"filename": str(item.get("filename") or ""), "quote": str(item.get("quote") or "")}
        for item in hits
        if _hit_source(item) == "materials"
    ]


def _best_history_hit(hits: list[dict]) -> dict | None:
    history = [item for item in hits if _hit_source(item) == "history"]
    if not history:
        return None
    history.sort(key=lambda item: float(item.get("score") or 0), reverse=True)
    return history[0]


def _apply_history(row: dict, clause: str, filename: str, quote: str, model: Any) -> None:
    try:
        judgment = judge_deviation(clause, quote, model)
    except Exception:
        _fail(row, "draft_failed")
        row.update(history_filename=filename, history_quote=quote)
        return
    kind, deviation_type = KINDS[judgment["deviation"]]
    reason = judgment["reason"]
    if kind != "comply" and not reason:
        _fail(row, "draft_failed")
        row.update(history_filename=filename, history_quote=quote)
        return
    response = f"{judgment['deviation']}。{reason}" if reason else f"无偏离。按本次招标文件响应「{clause}」。"
    row.update(
        response=response,
        response_type=kind,
        deviation_type=deviation_type,
        deviation_reason=reason if kind != "comply" else "",
        response_origin="history",
        history_filename=filename,
        history_quote=quote,
        status="pending",
    )


def fill_technical_responses(state: Any, workflow: dict, *, model: Any = None, search: Callable[[str], list[dict]] | None = None) -> None:
    """抽出条款后用知识库检索填写响应。没有命中就留空，不写成无偏离。"""
    rows = [row for row in workflow.get("requirements", {}).values() if not row.get("merged_into")]
    if not rows:
        workflow["technical_retrieval"] = "done"
        return
    del state
    search = _search_fn or search
    workflow["technical_retrieval"] = "running"
    try:
        for row in rows:
            clause = row.get("text") or ""
            try:
                hits = list(search(clause) if search else [])
            except Exception:
                _fail(row, "retrieval_failed")
                continue
            materials = _material_sources(hits)
            best = _best_history_hit(hits)
            if best is not None:
                _apply_history(
                    row,
                    clause,
                    str(best.get("filename") or ""),
                    visible_quote(str(best.get("quote") or ""), clause),
                    model,
                )
                row["material_sources"] = materials
                continue
            if materials:
                _fail(row, "no_evidence")
                row["material_sources"] = materials
                continue
            _fail(row, "no_evidence")
    finally:
        workflow["technical_retrieval"] = "done"


def guard_technical_confirm(workflow: dict, row: dict, *, batch: bool) -> None:
    """检索未结束、失败、清空，以及没有历史做法的整表确认，都不能进正文。"""
    if not row.get("technical_clause"):
        return
    if workflow.get("technical_retrieval") == "running":
        raise DomainError(409, "REQUIREMENT_NOT_READY", "历史标书还在检索，不能确认矩阵。")
    origin = row.get("response_origin") or ""
    if origin in ("retrieval_failed", "draft_failed", "no_evidence"):
        raise DomainError(409, "REQUIREMENT_NOT_READY", "没有检索依据、检索失败或拟写失败的条款不进入正文。",
                          {"requirement_ids": [row["id"]]})
    if not str(row.get("response") or "").strip():
        raise DomainError(409, "REQUIREMENT_NOT_READY", "清空的响应不进入正文。", {"requirement_ids": [row["id"]]})
    from icg.domain.matrix import response_type
    if batch and (origin != "history" or response_type(row) != "comply"):
        raise DomainError(409, "REQUIREMENT_NOT_READY", "没有历史做法的条款，以及正偏离、偏离，必须逐条确认。",
                          {"requirement_ids": [row["id"]]})
