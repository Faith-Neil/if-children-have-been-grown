# 为什么有这个文件：技术分册按公司教程抽取条款，不把封面、资质和报价写进响应矩阵。
# 它解决什么问题：主观分里用顿号、逗号、分号分开的要点各成一条，规格书按编号逐条抽取，同一件事只留一行。

from __future__ import annotations

import re
from dataclasses import dataclass, field

from icg.domain.domain import new_id

SPEC_LINE = re.compile(r"^(?:★\s*)?(\d+(?:\.\d+){0,3})[\s.、．]+(\S.{0,80})$")
LIST_SPLIT = re.compile(r"[、，,；;]")
LIST_HINT = re.compile(r"应包含|包括|服务方案|评分内容|详细评分")
SKIP_TITLE = re.compile(r"定义|封面|目录|报价|价格|客观分|资质|资格|证书|社保|发票|照片")
PLAIN_SKIP = re.compile(r"^(封面|目录|目\s*录)$")


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


def split_subjective(line: str) -> list[str]:
    if not LIST_SPLIT.search(line) or not LIST_HINT.search(line) or SKIP_TITLE.search(line):
        return []
    points = []
    for index, part in enumerate(LIST_SPLIT.split(line)):
        text = _point(part, index == 0)
        if 2 <= len(text) <= 40 and not SKIP_TITLE.search(text):
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
            if SKIP_TITLE.search(title):
                skip_number = number
                skip_plain = False
                continue
            if skip_number:
                continue
            skip_plain = False
            found.append(TechnicalClause(text=title, page=page, quote=line, kind="spec", number=number))
            continue
        if PLAIN_SKIP.match(line) or line.startswith("目录"):
            skip_plain = True
            continue
        if skip_number is not None:
            continue
        if skip_plain and not split_subjective(line):
            continue
        skip_plain = False
        for point in split_subjective(line):
            found.append(TechnicalClause(text=point, page=page, quote=line, kind="scoring"))
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
