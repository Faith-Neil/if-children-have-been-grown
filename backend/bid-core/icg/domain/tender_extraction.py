# 为什么有这个文件：从招标文件原文中按“章节 → 条目”抽取需要响应的条款和关键项目事实。
# 它解决什么问题：原先把每一个非空行都当成一条条款，真实招标文件（上百页、含合同条款与格式附件）
# 会产生上千条噪声，人工根本核不完；同时多行条目被拆散，★ 条款的后半句丢失。
#
# 做法（不依赖向量检索，见 docs/decisions/2026-10-28-kb-control-plane-and-pipelines.md 第 4 节）：
# 1. 识别标题层级，建章节树（第X章 / 一、/（一）/ 1. / 1.1 …）；
# 2. 按章节标题判断类别：投标人须知、资格要求、评分办法、技术/采购需求、商务要求、合同条款、文件格式；
# 3. 只在需要响应的章节里按编号条目抽取（续行并入同一条），合同条款与格式附件不抽；
# 4. ★/▲/废标/无效投标/否决等实质性条目无论在哪一章都抽，保证不漏；
# 5. 每条记录原文页码和首行原句（逐字取自原文，可校验），完整条目文字另存。
# 没有可识别章节结构的短文本（如粘贴的需求清单）退回逐行抽取，行为与原先一致。

from __future__ import annotations

import re
from dataclasses import dataclass, field

MANDATORY = re.compile(r"[★▲]|废标|无效投标|无效响应|否决投标|实质性(要求|条款|响应)|不得偏离|必须满足|不允许偏离")
SCORE = re.compile(r"(\d+(\.\d+)?)\s*分")

# 标题：编号体系从高到低。只认行首，且标题行不长（正文里的“一、”不算）。
HEADING_PATTERNS: list[tuple[int, re.Pattern]] = [
    (1, re.compile(r"^第[零一二三四五六七八九十百0-9]+(部分|篇|卷|册|章)\s*\S")),
    (2, re.compile(r"^第[零一二三四五六七八九十百0-9]+节\s*\S")),
    (2, re.compile(r"^[零一二三四五六七八九十百]+[、．.]\s*\S")),
    (3, re.compile(r"^[（(][零一二三四五六七八九十百]+[)）]\s*\S")),
]
MAX_HEADING_CHARS = 40

# 条目起点（同一节内的编号项）
ITEM_START = re.compile(
    r"^([0-9]{1,2}(\.[0-9]{1,2}){0,3}[．.、)）]|[（(][0-9]{1,2}[)）]|[①-⑳]|[a-zA-Z][．.、)）]|[-•●·▪]\s|[★▲])")

SECTION_KINDS: list[tuple[str, tuple[str, ...]]] = [
    ("format", ("投标文件格式", "响应文件格式", "文件格式", "格式附件", "附件格式", "投标函格式", "格式范本", "投标文件组成")),
    ("contract", ("合同条款", "合同主要条款", "通用条款", "专用条款", "合同文本", "合同格式", "政府采购合同")),
    ("scoring", ("评分", "评标办法", "评审办法", "评标方法", "评审标准", "评分标准", "综合评分", "评审因素")),
    ("qualification", ("资格", "资质要求", "投标人条件", "供应商条件", "合格投标人", "资格审查")),
    ("technical", ("技术要求", "技术规格", "技术参数", "采购需求", "服务要求", "需求说明", "项目需求", "建设内容", "功能要求", "性能要求", "服务内容", "实施要求")),
    ("business", ("商务要求", "商务条款", "付款", "交付", "质保", "售后", "培训", "验收", "报价要求")),
    ("notice", ("投标人须知", "供应商须知", "须知前附表", "前附表", "招标公告", "采购公告", "投标邀请")),
]
RESPONSIVE_KINDS = {"qualification", "scoring", "technical", "business", "notice", "other"}
# 须知类章节只抽“必须响应”的条目（含实质性标记或明确的“应/须/必须”），其余为程序性说明。
DUTY = re.compile(r"(须|必须|应当|应|不得|需提供|须提供|提供.{0,12}(证明|材料|复印件|原件)|具备|具有)")

FACT_KEYS = {
    "招标编号": ("招标编号", "项目编号", "采购编号", "采购项目编号"),
    "项目名称": ("项目名称", "采购项目名称"),
    "采购人": ("采购人", "招标人", "采购单位"),
    "投标截止时间": ("投标截止时间", "响应文件提交截止时间", "递交截止时间", "提交投标文件截止时间"),
    "开标时间": ("开标时间",),
    "预算金额": ("预算金额", "采购预算", "项目预算", "最高限价", "招标控制价"),
    "投标保证金": ("投标保证金", "保证金金额"),
    "服务期限": ("服务期限", "服务期", "合同期限", "履约期限"),
    "交付期": ("交付期", "交货期", "工期", "实施周期"),
    "质保期": ("质保期", "质量保证期", "免费维保期"),
    "服务地点": ("服务地点", "交付地点", "实施地点", "交货地点"),
    "响应时间": ("响应时间",),
}
FACT_LINE = re.compile(r"^\s*([\u4e00-\u9fa5]{2,14})\s*[:：]\s*(.{1,120})$")


@dataclass
class Section:
    title: str
    level: int
    page: int
    kind: str = "other"
    path: list[str] = field(default_factory=list)
    lines: list[tuple[int, str]] = field(default_factory=list)


@dataclass(frozen=True)
class ExtractedRequirement:
    text: str          # 完整条目（续行已并入）
    quote: str         # 首行原句，逐字取自原文第 page 页
    page: int
    section_kind: str
    section_path: tuple[str, ...]
    mandatory: bool
    score: float | None

    @property
    def category(self) -> str:
        if self.mandatory:
            return "mandatory"
        if self.section_kind == "scoring":
            return "scoring"
        return "business" if self.volume == "business" else "technical"

    @property
    def volume(self) -> str:
        business_words = ("商务", "资质", "资格", "报价", "业绩", "授权", "证书", "营业执照", "财务", "信誉", "社保", "纳税", "保证金", "付款")
        if self.section_kind in ("qualification", "business"):
            return "business"
        if self.section_kind == "technical":
            return "technical"
        return "business" if any(w in self.text for w in business_words) else "technical"


@dataclass(frozen=True)
class ExtractedFact:
    key: str
    value: str
    page: int
    quote: str


def heading_level(line: str) -> int | None:
    text = line.strip()
    if not text or len(text) > MAX_HEADING_CHARS or text.endswith(("。", "；", ";")):
        return None
    for level, pattern in HEADING_PATTERNS:
        if pattern.match(text):
            return level
    return None


def classify(path: list[str]) -> str:
    """从最近的标题往上找，第一个命中的类别为准（“第三章 评标办法 › 一、资格审查”算资格）。"""
    for title in reversed(path):
        for kind, words in SECTION_KINDS:
            if any(w in title for w in words):
                return kind
    return "other"


def segment(pages: list[str]) -> list[Section]:
    root = Section(title="", level=0, page=1)
    sections = [root]
    stack: list[Section] = [root]
    for page_no, text in enumerate(pages, start=1):
        for raw in text.splitlines():
            line = raw.strip()
            if not line:
                continue
            level = heading_level(line)
            if level is not None:
                while stack and stack[-1].level >= level:
                    stack.pop()
                path = [s.title for s in stack if s.title] + [line]
                section = Section(title=line, level=level, page=page_no, kind=classify(path), path=path)
                sections.append(section)
                stack.append(section)
                continue
            stack[-1].lines.append((page_no, line))
    return sections


def _items(section: Section) -> list[list[tuple[int, str]]]:
    items: list[list[tuple[int, str]]] = []
    for page, line in section.lines:
        starts = bool(ITEM_START.match(line)) or bool(MANDATORY.match(line))
        if starts or not items:
            items.append([(page, line)])
        else:
            items[-1].append((page, line))
    return items


def _requirement(section: Section, item: list[tuple[int, str]]) -> ExtractedRequirement:
    page, first = item[0]
    text = "".join(part for _, part in item) if len(item) > 1 and not any(ITEM_START.match(p) for _, p in item[1:]) \
        else "\n".join(part for _, part in item)
    score = SCORE.search(text)
    return ExtractedRequirement(text=text[:2000], quote=first, page=page, section_kind=section.kind,
                                section_path=tuple(section.path), mandatory=bool(MANDATORY.search(text)),
                                score=float(score.group(1)) if score and section.kind == "scoring" else None)


def extract_requirements(pages: list[str]) -> tuple[list[ExtractedRequirement], dict]:
    """返回 (条款, 摘要)。摘要说明结构识别与各类章节的抽取数量，供页面向人展示“抽了什么、跳过了什么”。"""
    sections = segment(pages)
    structured = sum(1 for s in sections if s.level) >= 3
    results: list[ExtractedRequirement] = []
    skipped: dict[str, int] = {}
    for section in sections:
        if not section.lines:
            continue
        if not structured:
            # 无章节结构：逐行（保持原有短文本行为）
            for page, line in section.lines:
                results.append(_requirement(section, [(page, line)]))
            continue
        for item in _items(section):
            req = _requirement(section, item)
            if req.mandatory:
                results.append(req)
            elif section.kind not in RESPONSIVE_KINDS:
                skipped[section.kind] = skipped.get(section.kind, 0) + 1
            elif section.kind in ("notice", "other") and not DUTY.search(req.text):
                skipped[section.kind] = skipped.get(section.kind, 0) + 1
            else:
                results.append(req)
    by_kind: dict[str, int] = {}
    for req in results:
        by_kind[req.section_kind] = by_kind.get(req.section_kind, 0) + 1
    summary = {"structured": structured, "sections": sum(1 for s in sections if s.level),
               "extracted": len(results), "mandatory": sum(1 for r in results if r.mandatory),
               "by_section_kind": by_kind, "skipped_items": skipped}
    return results, summary


def extract_facts(pages: list[str]) -> list[ExtractedFact]:
    facts: list[ExtractedFact] = []
    for page_no, text in enumerate(pages, start=1):
        for raw in text.splitlines():
            line = raw.strip()
            match = FACT_LINE.match(line)
            if not match:
                continue
            label, value = match.group(1), match.group(2).strip().rstrip("。；;")
            for key, aliases in FACT_KEYS.items():
                if label in aliases and value:
                    facts.append(ExtractedFact(key=key, value=value, page=page_no, quote=line))
                    break
    return facts


def is_fact_line(line: str) -> bool:
    match = FACT_LINE.match(line.strip())
    return bool(match and any(match.group(1) in aliases for aliases in FACT_KEYS.values()))
