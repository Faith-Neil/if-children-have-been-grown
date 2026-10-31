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
from dataclasses import dataclass, field, replace

MANDATORY = re.compile(
    r"[★▲]|废标|无效投标|无效响应|无效标|否决|视为无效|作无效|按无效|无效处理|不予受理|不予接受"
    r"|实质性(要求|条款|响应)|不得偏离|必须满足|不允许偏离")
SCORE = re.compile(r"(\d+(\.\d+)?)\s*分(?![值项析别类钟配解布册包数])")
# 资格条目应涉及投标人自身条件；扫描件丢了“技术架构要求”之类的小节标题时，系统规格会落进资格章
QUAL_WORDS = re.compile(r"投标人|供应商|资质|资格|证书|营业执照|业绩|财务|审计|信誉|信用|社保|社会保障|纳税|税收|授权|联合体|注册|法人|分包|失信|违法|破产|停业|单位负责人|控股|标段|投标")

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
    r"^([0-9]{1,2}(\.[0-9]{1,2}){0,3}[．.、)）]|[（(][0-9]{1,2}[)）]|[①-⑳]|[a-zA-Z][．.、)）]|[-•●·▪]\s|[》➢>❖◆■□]|[★▲]|注[:：])")
# 规格类条目（扫描件常丢章节标题，靠内容判断）：项目符号开头或“支持/提供/具备…”开头、不带分值
SPEC = re.compile(r"^\s*([》➢>❖◆■□•●]\s*)?(支持|提供|具备|具有|满足|实现|需|须|应|能够|可)")
# 评审程序性条文：主语是评标委员会、或只是“见前附表”的指引，不是投标人要响应的条款
PROCEDURE = re.compile(r"评标委员会|见评标办法前附表|见本章|评分分值计算|得分=|按得分由高到低|中标候选人")
# 一段里连写的“（1）…；（2）…”条目
INLINE_ITEM = re.compile(r"[（(]([0-9]{1,2})[)）]")

# PDF 表格被展平成“一格一行”。表头格出现 ≥2 个即进入表格模式，按行重组。
TABLE_HEADER_CELLS = {"条款号", "条款名称", "编列内容", "评分因素", "评审因素", "评分项目", "评审项目", "分值", "权重",
                      "评分标准", "评审标准", "评分细则", "序号", "内容", "说明与要求"}
CLAUSE_NO = re.compile(r"^[0-9]{1,2}(\.[0-9]{1,2}){1,3}$")
SCORE_CELL = re.compile(r"^[0-9]{1,3}(\.[0-9]{1,2})?\s*分?$")
NUMBERED_TITLE = re.compile(r"^[0-9]{1,2}[．.、]\s*[\u4e00-\u9fa5]{2,12}$")

SECTION_KINDS: list[tuple[str, tuple[str, ...]]] = [
    ("format", ("投标文件格式", "响应文件格式", "文件格式", "格式附件", "附件格式", "投标函格式", "格式范本", "投标文件组成")),
    ("contract", ("合同条款", "合同主要条款", "通用条款", "专用条款", "合同文本", "合同格式", "政府采购合同")),
    ("scoring", ("评分", "评标办法", "评审办法", "评标方法", "评审标准", "评分标准", "综合评分", "评审因素")),
    ("qualification", ("供应商资格", "资格", "资质要求", "投标人条件", "供应商条件", "合格投标人", "资格审查")),
    ("technical", ("技术要求", "技术规格", "技术参数", "采购需求", "服务要求", "需求说明", "项目需求", "建设内容", "功能要求", "性能要求", "服务内容", "实施要求",
                   "招标要求", "人员要求", "维保要求", "运维要求", "服务标准", "业务功能", "平台功能", "系统功能", "功能需求", "其他要求",
                   "保密要求", "文档要求", "开发商要求", "公司人员要求")),
    ("business", ("商务要求", "商务条款", "付款方式", "验收标准", "付款", "交付", "质保", "售后", "培训", "验收", "报价要求")),
    ("notice", ("投标人须知", "供应商须知", "须知前附表", "前附表", "招标公告", "采购公告", "投标邀请")),
]
RESPONSIVE_KINDS = {"qualification", "scoring", "technical", "business", "notice", "other"}
# 须知类章节只抽“必须响应”的条目（含实质性标记或明确的“应/须/必须”），其余为程序性说明。
DUTY = re.compile(r"(须(?!知)|必须|应当|应|不得|需提供|须提供|提供.{0,12}(证明|材料|复印件|原件)|具备|具有)")

FACT_KEYS = {
    "招标编号": ("招标编号", "项目编号", "采购编号", "采购项目编号", "交易项目序列号", "招标项目编号"),
    "项目名称": ("项目名称", "采购项目名称", "招标项目名称"),
    "采购人": ("采购人", "招标人", "采购单位"),
    "投标截止时间": ("投标截止时间", "响应文件提交截止时间", "递交截止时间", "提交投标文件截止时间"),
    "开标时间": ("开标时间",),
    "预算金额": ("预算金额", "采购预算", "项目预算"),
    # 最高限价与预算常常相同但含义不同，分开记，避免误报冲突
    "最高限价": ("最高限价", "招标控制价", "最高投标限价"),
    "投标保证金": ("投标保证金", "保证金金额"),
    "投标有效期": ("投标有效期",),
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


@dataclass
class _Item:
    page: int
    quote: str            # 逐字取自第 page 页的一行（或一行中的一段）
    text: str
    score: float | None = None   # 表格里的分值格；None 表示从正文“xx分”推断
    label: str = ""              # 表格行的名称格（条款名称/评分因素）


def _is_header(line: str) -> bool:
    return line in TABLE_HEADER_CELLS


def _table_end(line: str) -> bool:
    return bool(NUMBERED_TITLE.match(line)) or (bool(ITEM_START.match(line)) and not CLAUSE_NO.match(line)
                                                 and not SCORE_CELL.match(line))


def _clause_table(lines: list[tuple[int, str]], i: int, out: list[_Item]) -> int:
    """须知前附表：条款号 / 条款名称 / 编列内容，一格一行。"""
    while i < len(lines) and CLAUSE_NO.match(lines[i][1]):
        i += 1
        if i >= len(lines):
            break
        label = lines[i][1]
        i += 1
        content: list[tuple[int, str]] = []
        while i < len(lines) and not CLAUSE_NO.match(lines[i][1]) and not _table_end(lines[i][1]):
            content.append(lines[i])
            i += 1
        if content:
            page, quote = content[0]
            out.append(_Item(page=page, quote=quote, label=label,
                             text=f"{label}：{''.join(part for _, part in content)}"))
    return i


def _score_table(lines: list[tuple[int, str]], i: int, out: list[_Item]) -> int:
    """评分表：评分因素 / 分值 / 评分标准，一格一行；下一行是分值格的那一行就是下一个评分因素。"""
    n = len(lines)
    while i + 1 < n and not SCORE_CELL.match(lines[i][1]) and SCORE_CELL.match(lines[i + 1][1]) \
            and not _table_end(lines[i][1]):
        factor_page, factor = lines[i]
        score_cell = lines[i + 1][1].rstrip("分").strip()
        score = float(score_cell)
        i += 2
        criteria: list[tuple[int, str]] = []
        while i < n and not _table_end(lines[i][1]) and not (i + 1 < n and SCORE_CELL.match(lines[i + 1][1])
                                                               and not SCORE_CELL.match(lines[i][1])):
            criteria.append(lines[i])
            i += 1
        page, quote = criteria[0] if criteria else (factor_page, factor)
        body = "".join(part for _, part in criteria)
        out.append(_Item(page=page, quote=quote, label=factor, score=score,
                         text=f"{factor}（{score_cell}分）：{body}" if body else factor))
    return i


def _split_inline(item: _Item, lines: list[tuple[int, str]]) -> list[_Item]:
    """“（1）…；（2）…”写在同一段时拆成多条；每段的原句取自它起始的那一行。"""
    joined = "".join(part for _, part in lines)
    numbers = [int(m.group(1)) for m in INLINE_ITEM.finditer(joined)]
    if len(numbers) < 2 or numbers[0] != 1 or numbers != list(range(1, len(numbers) + 1)):
        return [item]
    pieces: list[_Item] = []
    for page, line in lines:
        marks = list(INLINE_ITEM.finditer(line))
        if not marks:
            if pieces:
                pieces[-1].text += line
            continue
        if pieces and marks[0].start() > 0:
            pieces[-1].text += line[:marks[0].start()]
        for k, mark in enumerate(marks):
            end = marks[k + 1].start() if k + 1 < len(marks) else len(line)
            segment_text = line[mark.start():end]
            pieces.append(_Item(page=page, quote=segment_text.rstrip("；;，, "), text=segment_text))
    for piece in pieces:
        piece.text = piece.text.rstrip("；;，, ")
    return pieces


def _items(section: Section) -> list[_Item]:
    lines = section.lines
    items: list[_Item] = []
    groups: list[list[tuple[int, str]]] = []

    def flush() -> None:
        while groups:
            group = groups.pop(0)
            page, first = group[0]
            items.extend(_split_inline(_Item(page=page, quote=first, text="".join(p for _, p in group)), group))

    i = 0
    while i < len(lines):
        page, line = lines[i]
        if _is_header(line) and i + 1 < len(lines) and _is_header(lines[i + 1][1]):
            header: list[str] = []
            while i < len(lines) and _is_header(lines[i][1]):
                header.append(lines[i][1])
                i += 1
            # 表格标题行（“投标人须知前附表”）不是条款
            if groups and len(groups[-1]) == 1 and groups[-1][0][1].endswith(("前附表", "表")):
                groups.pop()
            flush()
            if "条款号" in header:
                i = _clause_table(lines, i, items)
            elif "分值" in header or "权重" in header:
                i = _score_table(lines, i, items)
            continue
        starts = bool(ITEM_START.match(line)) or bool(MANDATORY.match(line))
        if starts or not groups:
            groups.append([(page, line)])
        else:
            groups[-1].append((page, line))
        i += 1
    flush()
    return items


def _requirement(section: Section, item: _Item) -> ExtractedRequirement:
    text = item.text
    score = item.score
    if score is None and section.kind == "scoring":
        found = SCORE.search(text)
        score = float(found.group(1)) if found else None
    return ExtractedRequirement(text=text[:2000], quote=item.quote, page=item.page, section_kind=section.kind,
                                section_path=tuple(section.path), mandatory=bool(MANDATORY.search(text)),
                                score=score if section.kind == "scoring" else None)


def table_facts(pages: list[str]) -> list[ExtractedFact]:
    """前附表里“条款名称 → 编列内容”同样是项目事实（投标保证金、投标有效期…）。"""
    facts: list[ExtractedFact] = []
    for section in segment(pages):
        for item in _items(section):
            if not item.label or item.score is not None:
                continue
            for key, aliases in FACT_KEYS.items():
                if item.label in aliases:
                    value = item.text.split("：", 1)[1].strip().rstrip("。；;")
                    if value and len(value) <= 120:
                        facts.append(ExtractedFact(key=key, value=value, page=item.page, quote=item.quote))
                    break
    return facts


_NUMBER_PREFIX = re.compile(r"^\s*([0-9]{1,2}(\.[0-9]{1,2}){0,3}[．.、)）]?|[（(][0-9一二三四五六七八九十]{1,2}[)）])\s*")


def _label_only(text: str) -> bool:
    body = _NUMBER_PREFIX.sub("", text.strip(), count=1)
    return "\n" not in body and len(body) <= 12 and not re.search(r"[，。；;：:、]|分", body)


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
                results.append(_requirement(section, _Item(page=page, quote=line, text=line)))
            continue
        for item in _items(section):
            req = _requirement(section, item)
            if not req.mandatory and req.score is None and _label_only(req.text):
                skipped["label"] = skipped.get("label", 0) + 1  # “2.场景配置”这类小标题，不是条款
                continue
            if section.kind == "qualification" and not req.mandatory and not QUAL_WORDS.search(req.text):
                req = replace(req, section_kind="technical")
            if section.kind == "scoring" and req.score is None and not req.mandatory:
                if SPEC.match(req.text):
                    # 评分章下出现的规格条目：扫描件丢了“采购需求”章标题，按内容归为技术
                    req = replace(req, section_kind="technical")
                elif PROCEDURE.search(req.text) or " | " not in req.text:
                    # 评分章里不带分值的正文多是评审程序（评标委员会如何打分），不由投标人响应
                    skipped["procedure"] = skipped.get("procedure", 0) + 1
                    continue
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
    seen = {(f.key, f.value) for f in facts}
    for fact in table_facts(pages):
        if (fact.key, fact.value) not in seen:
            facts.append(fact)
            seen.add((fact.key, fact.value))
    return facts


def is_fact_line(line: str) -> bool:
    match = FACT_LINE.match(line.strip())
    return bool(match and any(match.group(1) in aliases for aliases in FACT_KEYS.values()))
