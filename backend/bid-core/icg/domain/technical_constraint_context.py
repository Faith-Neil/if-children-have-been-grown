# 为什么有这个文件：技术节提示按废标级别组装短上下文。
# 它解决什么问题：信用中国、失信、资格和装订否决不进每节项目硬约束。

from __future__ import annotations

from dataclasses import dataclass

from icg.domain.technical_clause_extract import _matter_key, _same
from icg.domain.technical_clause_role import classify_constraint, is_bid_packaging, is_section_constraint_row

# 风险提示只留开头，长截图的后半段不进本节提示。
_TIP_CLIP = 160
_TIP_CAP = 8
_PROJECT_CAP = 8
_NON_TECH_MARKERS = (
    "信用中国",
    "资格",
    "资质",
    "商务",
    "价格",
    "保证金",
    "营业执照",
    "黑名单",
    "包装",
)


@dataclass(frozen=True)
class ConstraintContext:
    """L0 技术硬约束、L1 本章硬约束、L0 非技术风险提示。"""

    project: tuple[str, ...]
    section: tuple[str, ...]
    tips: tuple[str, ...]


def text_is_non_tech(text: str) -> bool:
    blob = str(text or "")
    if not blob:
        return False
    if is_bid_packaging(blob):
        return True
    return any(marker in blob for marker in _NON_TECH_MARKERS)


def row_is_non_tech(item: dict) -> bool:
    if item.get("requirement_type") == "qualification":
        return True
    blob = f"{item.get('text') or ''} {item.get('extracted_summary') or ''}"
    return text_is_non_tech(blob)


def build_constraint_context(
    rows: list[dict],
    workflow: dict | None,
    task: dict | None = None,
) -> ConstraintContext:
    """组装本节提示用的三条清单。只注入 tech_hard；非技术进提示；说不清的不进正文。"""
    section: list[str] = []
    tips: list[str] = []
    seen: list[str] = []
    tipped: list[str] = []
    for item in rows or []:
        text = _shown(item)
        if not text:
            continue
        classified = classify_constraint(text, item)
        if classified["kind"] == "non_tech_risk":
            _add_tip(tips, tipped, text)
            continue
        if (
            classified["kind"] == "tech_hard"
            and classified["level"] in ("L0", "L1")
            and is_section_constraint_row(item)
            and _keep_matter(text, seen)
        ):
            section.append(text)
    candidates: list[str] = []
    for raw in _sidecar_lines(workflow):
        text = str(raw or "").strip()
        if not text:
            continue
        classified = classify_constraint(text)
        if classified["kind"] == "non_tech_risk":
            _add_tip(tips, tipped, text)
            continue
        if classified["kind"] != "tech_hard" or classified["level"] not in ("L0", "L1"):
            continue
        if not _keep_matter(text, seen):
            continue
        candidates.append(text)
    project = _choose_project(candidates, _linked_texts(task, workflow))
    return ConstraintContext(tuple(project), tuple(section), tuple(tips))


def _shown(item: dict) -> str:
    return str(item.get("extracted_summary") or item.get("text") or "").strip()


def _sidecar_lines(workflow: dict | None) -> list:
    return ((workflow or {}).get("technical_sidecars") or {}).get("rejection_lines") or []


def _keep_matter(text: str, seen: list[str]) -> bool:
    key = _matter_key(text)
    if key and any(_same(key, item) for item in seen):
        return False
    if key:
        seen.append(key)
    return True


def _clip_tip(text: str) -> str:
    if len(text) <= _TIP_CLIP:
        return text
    return text[:_TIP_CLIP]


def _add_tip(tips: list[str], seen: list[str], text: str) -> None:
    if not _keep_matter(text, seen):
        return
    if len(tips) >= _TIP_CAP:
        return
    tips.append(_clip_tip(text))


def _linked_texts(task: dict | None, workflow: dict | None) -> list[str]:
    if not task:
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
    texts: list[str] = []
    for rid in ids:
        row = requirements.get(rid)
        if not isinstance(row, dict) or row_is_non_tech(row):
            continue
        text = _shown(row)
        if text:
            texts.append(text)
    return texts


def _overlaps(line: str, linked: list[str]) -> bool:
    key = _matter_key(line)
    if not key:
        return False
    return any(_same(key, _matter_key(text)) for text in linked)


def _choose_project(candidates: list[str], linked: list[str]) -> list[str]:
    # 挂载原文对得上才收窄；对不上时仍用短全局列表，避免措辞不一致把技术废标整段拿掉。
    if linked:
        matched = [line for line in candidates if _overlaps(line, linked)]
        if matched:
            return matched[:_PROJECT_CAP]
    return candidates[:_PROJECT_CAP]
