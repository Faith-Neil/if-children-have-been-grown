# 为什么有这个文件：给章节正文每个块（标题、段落、列表项、表格）一个跨版本不变的段落键，并记下每块的来源（APP-M2-T161，PRD v1.8 §5.11.2～5.11.10）。
# 它解决什么问题：
# 1. 原来各模块按“第几行”找段落，空行算不算、从 0 还是 1 数各不相同，改一段后后面的段落全部错位；
#    现在按导出用的同一套分块（docx_markdown.blocks）切块，新版本与上一版逐块比对，没改的块、改过的块都沿用原键，只有新增块拿新键。
# 2. 每块记来源：人工编写、对话助手写入、粘贴自对话助手、章节循环修正、系统生成；没改的块保留上一版的来源，改过的块取本次写入方式。
# 3. 键由“章节 + 首次出现的版本号 + 序号”决定，同一段历史无论何时重算都得到同样的键，因此旧版本缺记录时可以补算，不依赖额外存储。
# 正文仍以纯文本（Markdown）为准，导出、检查、选区改写读的都是同一份文字；段落键是正文旁边的一层结构，不改动文字。

from __future__ import annotations

from difflib import SequenceMatcher
from hashlib import sha1
from typing import Any

from icg.infra.docx_markdown import blocks as _blocks

SOURCE_LABELS = {
    "manual": "人工编写",
    "assistant": "对话助手写入",
    "assistant_pasted": "粘贴自对话助手",
    "chapter_loop": "章节循环修正",
    "system": "系统生成",
}
# 改过的块与原块相似度达到这个值才算“同一段改了几个字”，沿用原键；否则视为删旧加新。
SAME_PARAGRAPH_RATIO = 0.5


def split(content: str) -> list[dict[str, Any]]:
    """按导出分块切正文，去掉空行；每块带种类、起止行号（0 起，含两端）与原文。"""
    lines = content.splitlines()
    out = []
    for block in _blocks(content):
        start, end = block.lines
        text = "\n".join(lines[start:end + 1])
        if not text.strip():
            continue
        out.append({"kind": block.kind, "level": block.level, "line_start": start, "line_end": end,
                    "text": text, "hash": sha1(text.strip().encode("utf-8")).hexdigest()[:16]})
    return out


def version_source(version: dict) -> str:
    """一次写入的方式 → 本次改动块的来源。"""
    origin = version.get("version_origin") or ""
    source = version.get("source") or ""
    if source == "system_generated":
        return "system"
    if source == "chapter_loop":
        return "chapter_loop"
    if origin in ("assistant_edit", "ai_polish_accepted"):
        return "assistant"
    return "manual"


def _pasted_lines(version: dict) -> set[int]:
    return {int(p["paragraph_index"]) for p in version.get("paragraph_sources") or []
            if p.get("source") == "assistant_pasted" and isinstance(p.get("paragraph_index"), int)}


def _texts(paragraphs: list[dict], content: str) -> list[str]:
    lines = content.splitlines()
    return ["\n".join(lines[p["line_start"]:p["line_end"] + 1]) for p in paragraphs]


def assign(chapter_id: str, previous: list[dict] | None, previous_content: str, content: str, version: dict) -> list[dict]:
    """按上一版段落（及其正文）给新正文分键；previous 为 None 表示第一版。"""
    revision = int(version.get("revision") or 1)
    changed_source = version_source(version)
    pasted = _pasted_lines(version)
    blocks = split(content)
    keys: list[str | None] = [None] * len(blocks)
    sources: list[str | None] = [None] * len(blocks)
    previous = previous or []
    old_texts = _texts(previous, previous_content)
    matcher = SequenceMatcher(a=[p["hash"] for p in previous], b=[b["hash"] for b in blocks], autojunk=False)
    for tag, a0, a1, b0, b1 in matcher.get_opcodes():
        if tag == "equal":
            for offset in range(b1 - b0):
                keys[b0 + offset] = previous[a0 + offset]["key"]
                sources[b0 + offset] = previous[a0 + offset].get("source", "manual")
        elif tag == "replace":
            # 逐个配对：按顺序取最像的旧块，相似度够才沿用原键（改了几个字仍是同一段）
            free = list(range(a0, a1))
            for b in range(b0, b1):
                best, best_ratio = None, 0.0
                for a in free[:30]:   # 只看前 30 个候选，长章节大段替换时不至于逐对比较
                    pair = SequenceMatcher(a=old_texts[a], b=blocks[b]["text"], autojunk=False)
                    if pair.quick_ratio() < max(best_ratio, SAME_PARAGRAPH_RATIO):
                        continue
                    ratio = pair.ratio()
                    if ratio > best_ratio:
                        best, best_ratio = a, ratio
                if best is not None and best_ratio >= SAME_PARAGRAPH_RATIO:
                    keys[b] = previous[best]["key"]
                    free = [a for a in free if a > best]
    # 版本回退：回来的块沿用目标版本里的键与来源，段落追溯不断
    restore = version.get("rollback_paragraphs") or []
    if restore:
        taken = {k for k in keys if k}
        pool: dict[str, list[dict]] = {}
        for item in restore:
            pool.setdefault(item["hash"], []).append(item)
        for index, block in enumerate(blocks):
            if keys[index] is None and pool.get(block["hash"]):
                item = pool[block["hash"]].pop(0)
                if item["key"] not in taken:
                    keys[index], sources[index] = item["key"], item.get("source", "manual")
                    taken.add(item["key"])
    used = {k for k in keys if k}
    serial = 0
    out = []
    for index, block in enumerate(blocks):
        key = keys[index]
        if key is None:
            serial += 1
            key = f"pk-{chapter_id}-r{revision}-{serial}"
            while key in used:
                serial += 1
                key = f"pk-{chapter_id}-r{revision}-{serial}"
            used.add(key)
        source = sources[index]
        if source is None:
            covered = any(block["line_start"] <= line <= block["line_end"] for line in pasted)
            source = "assistant_pasted" if covered else changed_source
        out.append({"key": key, "kind": block["kind"], "level": block["level"],
                    "line_start": block["line_start"], "line_end": block["line_end"],
                    "hash": block["hash"], "source": source})
    return out


def ensure(chapter: Any) -> list[dict]:
    """补齐每个版本的段落表（只补缺的），返回最新版本的段落表。"""
    previous: list[dict] | None = None
    previous_content = ""
    for version in chapter.versions:
        paragraphs = version.get("paragraphs")
        content = version.get("content") or ""
        if not isinstance(paragraphs, list):
            paragraphs = assign(chapter.id, previous, previous_content, content, version)
            version["paragraphs"] = paragraphs
        previous, previous_content = paragraphs, content
    return previous or []


def current(chapter: Any) -> list[dict]:
    """当前正式正文的段落表；最新版本内容与正文不一致（旧数据）时按正文补算，来源记人工。"""
    latest = ensure(chapter)
    if chapter.versions and (chapter.versions[-1].get("content") or "") == chapter.content:
        return latest
    base = chapter.versions[-1].get("content") or "" if chapter.versions else ""
    return assign(chapter.id, latest, base, chapter.content, {"revision": chapter.revision})


def public(paragraphs: list[dict]) -> list[dict]:
    """接口返回：键、种类、行号、来源与中文来源名（正文已在 content 里，不重复给原文）。"""
    return [{**p, "source_label": SOURCE_LABELS.get(p.get("source"), SOURCE_LABELS["manual"])} for p in paragraphs]
