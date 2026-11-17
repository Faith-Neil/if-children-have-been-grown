# 为什么有这个文件：正文写完后，用字符串规则核对技术废标有没有被写到。
# 它解决什么问题：模型自己写「已响应」不能把状态改成通过；信用中国这类提示不要求写进正文。

from __future__ import annotations

import re

from icg.domain.technical_clause_extract import _matter_key, _same
from icg.domain.technical_constraint_context import row_is_non_tech, text_is_non_tech

_REJECTION_WORD = re.compile(r"废标|否决|无效")
_CITE = re.compile(r"\[标:([^\]】]{2,80})\]")
_SENTENCE = re.compile(r"[^。！？\n]+")
_MEASURE = re.compile(r"(\d+)\s*(小时|分钟|天|次)")
_NEG = re.compile(r"不承诺|不予承诺|不保证|无法保证|不做|不提供")
# 这些套话在每条废标里都会出现，不能拿来判断某一条已经写进正文。
_BOILER = (
    "不满足则作废标处理",
    "否决其投标",
    "投标无效",
    "废标条件",
    "作废标处理",
)

_FAILED = "废标技术约束未在正文覆盖，不能视为已全部响应。"
_CONFIRM = "同一事项的承诺互相矛盾，须人工确认，不能视为已全部响应。"


def notice_for(check: dict | None) -> str:
    """文案只看校验状态。调用方塞进来的 notice 不算。"""
    status = (check or {}).get("status") or ""
    if status == "failed":
        return _FAILED
    if status == "needs_confirm":
        return _CONFIRM
    return ""


def completion_message(base: str | None, check: dict | None) -> str | None:
    """有阻断时在原句后面加上不能视为已全部响应。通过或没有校验结果时保持原句。"""
    note = notice_for(check)
    if not note:
        return base
    text = base or ""
    return f"{text} {note}".strip()


def evaluate_volume(workflow: dict | None, sections: list[dict] | None) -> dict:
    """卷级 L0 要在某一节正文里出现；本节 L1 和挂到本节的 L0 必须出现在这一节。"""
    sections = list(sections or [])
    l0_lines = _l0_lines(workflow)
    l1_by_key: dict[str, list[str]] = {}
    all_l1: list[str] = []
    for section in sections:
        lines = _l1_lines(section.get("rows") or [])
        l1_by_key[str(section.get("key") or "")] = lines
        all_l1.extend(lines)
    missing: list[dict] = []
    for line in l0_lines:
        if not _checkable(line):
            continue
        if any(_addresses(line, section.get("body") or "") for section in sections):
            continue
        _add(missing, {"level": "L0", "text": line, "section": ""})
    owned: dict[str, list[dict]] = {}
    for section in sections:
        key = str(section.get("key") or "")
        title = str(section.get("title") or "")
        body = section.get("body") or ""
        owned[key] = []
        for line in l1_by_key.get(key) or []:
            if _checkable(line) and not _addresses(line, body):
                _add(owned[key], {"level": "L1", "text": line, "section": title})
        for line in _linked_l0(section.get("task"), workflow, l0_lines):
            if _checkable(line) and not _addresses(line, body):
                _add(owned[key], {"level": "L0", "text": line, "section": title})
        for item in owned[key]:
            _add(missing, item)
    conflicts = _conflicts(_unique([*l0_lines, *all_l1]), sections)
    status = _status(missing, conflicts)
    views: dict[str, dict] = {}
    for section in sections:
        key = str(section.get("key") or "")
        title = str(section.get("title") or "")
        fought = [item for item in conflicts if title and title in (item.get("sections") or [])]
        if owned.get(key):
            view_status = "failed"
        elif fought:
            view_status = "needs_confirm"
        else:
            view_status = "passed"
        view = {"status": view_status, "missing": owned.get(key) or [], "conflicts": fought}
        view["notice"] = notice_for(view)
        views[key] = view
    result = {"status": status, "missing": missing, "conflicts": conflicts, "sections": views}
    result["notice"] = notice_for(result)
    return result


def _status(missing: list[dict], conflicts: list[dict]) -> str:
    if missing:
        return "failed"
    if conflicts:
        return "needs_confirm"
    return "passed"


def _add(items: list[dict], item: dict) -> None:
    if item not in items:
        items.append(item)


def _unique(lines: list[str]) -> list[str]:
    kept: list[str] = []
    seen: list[str] = []
    for line in lines:
        key = _matter_key(line)
        if key and any(_same(key, item) for item in seen):
            continue
        if key:
            seen.append(key)
        kept.append(line)
    return kept


def _l0_lines(workflow: dict | None) -> list[str]:
    kept: list[str] = []
    seen: list[str] = []
    raw_lines = ((workflow or {}).get("technical_sidecars") or {}).get("rejection_lines") or []
    for raw in raw_lines:
        text = str(raw or "").strip()
        if not text or text_is_non_tech(text) or _REJECTION_WORD.search(text) is None:
            continue
        key = _matter_key(text)
        if key and any(_same(key, item) for item in seen):
            continue
        if key:
            seen.append(key)
        kept.append(text)
    return kept


def _l1_lines(rows: list[dict]) -> list[str]:
    kept: list[str] = []
    seen: list[str] = []
    for item in rows or []:
        if not isinstance(item, dict) or row_is_non_tech(item):
            continue
        hard = (
            bool(item.get("is_rejection_criterion")) and item.get("requirement_type") != "qualification"
        ) or item.get("clause_role") == "rejection_constraint"
        if not hard:
            continue
        text = str(item.get("extracted_summary") or item.get("text") or "").strip()
        if not text:
            continue
        key = _matter_key(text)
        if key and any(_same(key, item_key) for item_key in seen):
            continue
        if key:
            seen.append(key)
        kept.append(text)
    return kept


def _linked_l0(task: dict | None, workflow: dict | None, l0_lines: list[str]) -> list[str]:
    if not isinstance(task, dict):
        return []
    ids = [
        *(task.get("rejection_requirement_ids") or []),
        *(task.get("constraint_ids") or []),
    ]
    if not ids:
        return []
    requirements = (workflow or {}).get("requirements") or {}
    if not isinstance(requirements, dict):
        return []
    linked: list[str] = []
    for rid in ids:
        row = requirements.get(rid)
        if not isinstance(row, dict) or row_is_non_tech(row):
            continue
        text = str(row.get("extracted_summary") or row.get("text") or "").strip()
        if text:
            linked.append(text)
    if not linked:
        return []
    kept: list[str] = []
    for line in l0_lines:
        key = _matter_key(line)
        if any(_same(key, _matter_key(text)) for text in linked):
            kept.append(line)
    return kept


def _checkable(line: str) -> bool:
    return bool(_grams(line))


def _boiler(fragment: str) -> bool:
    return any(fragment in phrase for phrase in _BOILER)


def _grams(text: str) -> list[str]:
    key = _matter_key(text)
    found: list[str] = []
    for index in range(0, max(0, len(key) - 3)):
        fragment = key[index:index + 4]
        if re.fullmatch(r"[\u4e00-\u9fff]{4}", fragment) is None or _boiler(fragment):
            continue
        if fragment not in found:
            found.append(fragment)
    return found


def _addresses(constraint: str, body: str) -> bool:
    """四字事项片段，或 [标:] 引用与事项键重叠。正文里的「已响应」三个字本身不算覆盖。"""
    text = body or ""
    key = _matter_key(constraint)
    for cite in _CITE.findall(text):
        if _same(_matter_key(cite), key):
            return True
    return any(fragment in text for fragment in _grams(constraint))


def _promise_token(sentence: str) -> str | None:
    measures = [f"{number}{unit}" for number, unit in _MEASURE.findall(sentence)]
    negated = _NEG.search(sentence) is not None
    if not measures and not negated:
        return None
    if not measures:
        return "否定"
    core = "+".join(sorted(set(measures)))
    return f"否定{core}" if negated else core


def _conflicts(lines: list[str], sections: list[dict]) -> list[dict]:
    found: list[dict] = []
    for line in lines:
        grams = _grams(line)
        if not grams:
            continue
        by_section: dict[str, list[str]] = {}
        for section in sections:
            title = str(section.get("title") or "")
            tokens: list[str] = []
            for sentence in _SENTENCE.findall(section.get("body") or ""):
                if not any(fragment in sentence for fragment in grams):
                    continue
                token = _promise_token(sentence)
                if token and token not in tokens:
                    tokens.append(token)
            if tokens:
                by_section[title] = tokens
        values = sorted({token for tokens in by_section.values() for token in tokens})
        if len(values) <= 1:
            continue
        found.append({
            "text": line,
            "sections": [title for title, tokens in by_section.items() if tokens],
            "values": values,
        })
    return found
