# 为什么有这个文件：正文写完后，用字符串规则核对技术废标有没有被写反。
# 它解决什么问题：缺席不算未响应；否定、放宽或前后承诺冲突才拦住导出。模型写「已响应」不改状态。

from __future__ import annotations

import re

from icg.domain.technical_clause_extract import _matter_key, _same
from icg.domain.technical_clause_role import classify_constraint

_SENTENCE = re.compile(r"[^。！？\n]+")
_MEASURE = re.compile(r"(\d+)\s*(小时|分钟|天|次)")
_NEG = re.compile(r"不承诺|不予承诺|不保证|无法保证|不做|不提供")
_WORK_HOURS = re.compile(r"工作时间|下一工作日|工作日")
_TIME_UNIT = {"分钟": 1, "小时": 60, "天": 60 * 24}
# 这些套话在每条废标里都会出现，不能拿来判断某一条已经写进正文。
_BOILER = (
    "不满足则作废标处理",
    "否决其投标",
    "投标无效",
    "废标条件",
    "作废标处理",
)

_FAILED = "废标技术约束被写反或放宽，不能视为已全部响应。"
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
    """技术硬约束只查有没有被否定或放宽。没写到不算缺失。前后承诺不一致则待确认。"""
    sections = list(sections or [])
    l0_lines = _l0_lines(workflow)
    all_l1: list[str] = []
    for section in sections:
        all_l1.extend(_l1_lines(section.get("rows") or []))
    catalog = _catalog(l0_lines, all_l1)
    missing: list[dict] = []
    owned: dict[str, list[dict]] = {}
    for section in sections:
        key = str(section.get("key") or "")
        title = str(section.get("title") or "")
        body = section.get("body") or ""
        owned[key] = []
        for line, level in catalog:
            if not _violates(line, body):
                continue
            _add(owned[key], {"level": level, "text": line, "section": title})
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


def _catalog(l0_lines: list[str], l1_lines: list[str]) -> list[tuple[str, str]]:
    """同一句只查一次。侧车 L0 优先于本章 L1。"""
    catalog: list[tuple[str, str]] = [(line, "L0") for line in l0_lines]
    seen = set(l0_lines)
    for line in l1_lines:
        if line in seen:
            continue
        seen.add(line)
        catalog.append((line, "L1"))
    return catalog


def _l0_lines(workflow: dict | None) -> list[str]:
    kept: list[str] = []
    seen: list[str] = []
    raw_lines = ((workflow or {}).get("technical_sidecars") or {}).get("rejection_lines") or []
    for raw in raw_lines:
        text = str(raw or "").strip()
        if not text:
            continue
        classified = classify_constraint(text)
        if classified["kind"] != "tech_hard" or classified["level"] not in ("L0", "L1"):
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
        if not isinstance(item, dict):
            continue
        text = str(item.get("extracted_summary") or item.get("text") or "").strip()
        if not text:
            continue
        classified = classify_constraint(text, item)
        if classified["kind"] != "tech_hard" or classified["level"] != "L1":
            continue
        key = _matter_key(text)
        if key and any(_same(key, item_key) for item_key in seen):
            continue
        if key:
            seen.append(key)
        kept.append(text)
    return kept


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


def _violates(constraint: str, body: str) -> bool:
    """事项被否定，或时限被放宽成工作时间、下一工作日，或写成更长的时限。"""
    grams = _grams(constraint)
    if not grams:
        return False
    for sentence in _SENTENCE.findall(body or ""):
        if not any(fragment in sentence for fragment in grams):
            continue
        if _NEG.search(sentence) or _WORK_HOURS.search(sentence):
            return True
        if _weaker_measure(constraint, sentence):
            return True
    return False


def _weaker_measure(constraint: str, sentence: str) -> bool:
    """同一事项上，正文给出的最短时限仍长于约束，或次数少于约束。"""
    constraint_times = _time_minutes(constraint)
    sentence_times = _time_minutes(sentence)
    if constraint_times and sentence_times and min(sentence_times) > min(constraint_times):
        return True
    constraint_counts = _counts(constraint)
    sentence_counts = _counts(sentence)
    if constraint_counts and sentence_counts and min(sentence_counts) < min(constraint_counts):
        return True
    return False


def _time_minutes(text: str) -> list[int]:
    found: list[int] = []
    for number, unit in _MEASURE.findall(text or ""):
        scale = _TIME_UNIT.get(unit)
        if scale:
            found.append(int(number) * scale)
    return found


def _counts(text: str) -> list[int]:
    return [int(number) for number, unit in _MEASURE.findall(text or "") if unit == "次"]


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
