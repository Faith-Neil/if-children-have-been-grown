# 为什么有这个文件：技术分册只抽取技术服务方案里要响应的事项。
# 它解决什么问题：目录标题和技术评分按语义留下，不靠整行标题或顿号；开标、评标、报价和表格碎片不进矩阵。

from __future__ import annotations

import re
from dataclasses import dataclass, field

from icg.domain.domain import new_id

SPEC_LINE = re.compile(r"^(?:★\s*)?(\d+(?:\.\d+){0,3})[\s.、．]+(\S.{0,80})$")
LIST_SPLIT = re.compile(r"[、，,；;]")
LIST_HINT = re.compile(r"应包含|包括|服务方案|评分内容|详细评分|技术评分|服务内容")
SKIP_TITLE = re.compile(r"定义|封面|目录|报价|价格|客观分|资质|资格|证书|社保|发票|照片")
PLAIN_SKIP = re.compile(r"^(封面|目录|目\s*录)$")
CHAPTER_TITLE = re.compile(r"^(?:第[0-9一二三四五六七八九十]+[章节篇]\s*)?(技术服务方案|服务方案|技术方案)$")
DROP = re.compile(
    r"评标|开标|投标函|投标保证金|保证金|招标代理|废标条件|资格|报价|价格|联合体|定标|投诉|"
    r"纪律|资金来源|踏勘|样品|法定代表人|授权委托|关联企业|股东|股权|中标候选人|公示|"
    r"澄清|异议|履约担保|投标有效期|语言文字|计量单位|转包|分包|评标委员会|公共资源交易|"
    r"电子签名|解密|投标文件|招标文件的|是否接受|是否采用|项目概况|项目联系|联系电话|"
    r"资金落实|最高投标限价|招标公告|投标截止|开标一览|投标人须知|合同授予|标包|"
    r"中标通知|投标预备|否决其投标|评分标准|分值构成"
)
SERVICE = re.compile(
    r"服务|维保|巡检|故障|监控|备份|恢复|升级|补丁|优化|性能|培训|应急|保密|质保|保修|"
    r"值守|整改|交付|现场|健康|数据库|中间件|操作系统|虚拟化|可用性|安全|知识|验收|"
    r"运维|实施|响应时限|响应时间|日志|架构|切换|演练"
)


@dataclass
class TechnicalClause:
    text: str
    page: int
    quote: str
    kind: str
    number: str = ""
    sources: list[dict] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.sources:
            self.sources = [{"page": self.page, "quote": self.quote, "kind": self.kind}]


def _matter_key(text: str) -> str:
    body = re.sub(r"^★?\s*\d+(?:\.\d+)*\s*", "", text.strip())
    body = re.sub(r"[\s、，,；;。.（）()【】\[\]/]", "", body)
    if body.endswith("服务") and len(body) > 4:
        body = body[:-2]
    return body


def _same(left: str, right: str) -> bool:
    if not left or not right:
        return False
    if left == right:
        return True
    short, long = (left, right) if len(left) <= len(right) else (right, left)
    return len(short) >= 4 and short in long


def _point(part: str, first: bool) -> str:
    text = part.strip().strip("。．.）)】」")
    text = re.sub(r"等$", "", text).strip()
    if first and "的" in text:
        text = text.rsplit("的", 1)[-1].strip()
    text = re.sub(r"^(和|及|与|或)+", "", text).strip()
    return text


def _noise(text: str) -> bool:
    compact = re.sub(r"[\s|]+", "", text)
    if len(compact) < 2:
        return True
    if text.count("|") >= 2 or re.fullmatch(r"[\d\s.、|★]+", text):
        return True
    return False


def _service_title(text: str) -> str:
    """长句收成目录标题。评分要点本身已经很短时保持原词。"""
    title = re.sub(r"^[★\d.\s、．]+", "", text).strip(" |")
    title = re.split(r"[|。；;]", title)[0].strip()
    if len(title) <= 24:
        return title
    matched = SERVICE.search(title)
    if matched is None:
        return title[:24].strip()
    start = max(0, matched.start() - 6)
    return title[start:matched.end() + 8].strip("，,、的将应需为")[:24] or title[:24]


def _kept(text: str) -> bool:
    if _noise(text) or DROP.search(text) or SKIP_TITLE.search(text):
        return False
    return SERVICE.search(text) is not None


def split_subjective(line: str) -> list[str]:
    if not LIST_SPLIT.search(line) or DROP.search(line) or SKIP_TITLE.search(line):
        return []
    if not LIST_HINT.search(line) and not SERVICE.search(line):
        return []
    points = []
    for index, part in enumerate(LIST_SPLIT.split(line)):
        text = _point(part, index == 0)
        if 2 <= len(text) <= 40 and _kept(text):
            points.append(text)
    return points if len(points) >= 2 else []


def extract_technical_clauses(pages: list[str]) -> list[TechnicalClause]:
    lines: list[tuple[int, str]] = []
    for page_no, text in enumerate(pages, start=1):
        for raw in text.splitlines():
            line = raw.strip()
            if line:
                lines.append((page_no, line))
    found: list[TechnicalClause] = []
    skip_number: str | None = None
    skip_plain = False
    for page, line in lines:
        numbered = SPEC_LINE.match(line)
        if numbered:
            number, title = numbered.group(1), numbered.group(2).strip()
            if skip_number and not (number == skip_number or number.startswith(skip_number + ".")):
                skip_number = None
            if SKIP_TITLE.search(title) or DROP.search(title):
                skip_number = number
                skip_plain = False
                continue
            if skip_number:
                continue
            skip_plain = False
            if CHAPTER_TITLE.match(title) or not _kept(title):
                continue
            found.append(TechnicalClause(text=_service_title(title), page=page, quote=line, kind="spec", number=number))
            continue
        if CHAPTER_TITLE.match(line) or PLAIN_SKIP.match(line) or line.startswith("目录"):
            skip_plain = PLAIN_SKIP.match(line) is not None or line.startswith("目录")
            continue
        if skip_plain and not split_subjective(line):
            continue
        skip_plain = False
        points = split_subjective(line)
        if points:
            for point in points:
                found.append(TechnicalClause(text=point, page=page, quote=line, kind="scoring"))
            continue
        if _kept(line) and len(line) <= 80:
            found.append(TechnicalClause(text=_service_title(line), page=page, quote=line, kind="scoring"))
    return _merge(found)


def _merge(clauses: list[TechnicalClause]) -> list[TechnicalClause]:
    merged: list[TechnicalClause] = []
    for clause in clauses:
        key = _matter_key(clause.text)
        hit = next((item for item in merged if _same(_matter_key(item.text), key)), None)
        if hit is None:
            merged.append(clause)
            continue
        for source in clause.sources:
            if source not in hit.sources:
                hit.sources.append(source)
        if clause.kind == "scoring" and hit.kind != "scoring":
            hit.text = clause.text
            hit.kind = "scoring"
    return merged


def apply_technical_extract(workflow: dict, file_id: str, pages: list[str], new_ids: set[str]) -> dict:
    """把抽出的条款写入矩阵。同一件事已有一行时，只追加来源，不另起一行。"""
    clauses = extract_technical_clauses(pages)
    index = {row.get("matter_key"): row for row in workflow["requirements"].values() if row.get("technical_clause")}
    for clause in clauses:
        key = _matter_key(clause.text)
        source = {"file_id": file_id, "page": clause.page, "quote": clause.quote, "kind": clause.kind}
        hit = next((row for matter, row in index.items() if _same(str(matter), key)), None)
        if hit is not None:
            sources = hit.setdefault("sources", [])
            if source not in sources:
                sources.append(source)
            if clause.kind == "scoring" and hit.get("section_kind") != "scoring":
                hit["text"] = clause.text
                hit["section_kind"] = "scoring"
            continue
        row = {
            "id": new_id("req"),
            "text": clause.text,
            "category": "technical",
            "volume": "technical",
            "chapter_id": None,
            "status": "pending",
            "response": "",
            "reason": "",
            "evidence_ids": [],
            "source": {"file_id": file_id, "page": clause.page, "quote": clause.quote},
            "sources": [source],
            "references": [],
            "reference_status": "none",
            "section_path": [clause.number] if clause.number else [],
            "section_kind": clause.kind,
            "score": None,
            "technical_clause": True,
            "matter_key": key,
        }
        workflow["requirements"][row["id"]] = row
        index[key] = row
        new_ids.add(row["id"])
    return {"technical": True, "structured": True, "sections": 0, "extracted": len(clauses),
            "mandatory": 0, "by_section_kind": {}, "skipped_items": {}}
