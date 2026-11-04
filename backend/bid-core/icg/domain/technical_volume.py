# 为什么有这个文件：技术分册按节写正文，并在导出内部稿时照招标样表填偏离表。
# 它解决什么问题：确认目录不会自动生成；没有样表时不自造偏离表；一节失败不改掉其他节。

from __future__ import annotations

import re
from typing import Any, Callable

from icg.domain.domain import DomainError
from icg.domain.matrix import critical

PARTS = ("响应说明", "服务目标", "具体措施", "工作流程", "交付物与记录", "本项目结合点")
WRITE_ORDER = ("服务内容", "服务方式", "质量管理", "应急", "实施计划", "培训", "保密", "质保")
HEADING = re.compile(r"^(\d+(?:\.\d+)*)\s+(\S.*)$")
SAMPLE_TITLE = re.compile(r"偏离表|偏差表")
BOOK = re.compile(r"《[^》]{1,40}》")
LABEL = {"comply": "无偏离", "exceed": "正偏离", "deviate": "负偏离"}
TABLE_LABEL = {"comply": "无偏离", "exceed": "正偏离", "deviate": "偏离"}
NO_SAMPLE = "这份招标文件没有提供偏离表格式。"
SECTION_SYSTEM = (
    "只写这一节的六段：响应说明、服务目标、具体措施、工作流程、交付物与记录、本项目结合点。"
    "用文字步骤和表格。不要流程图，不要架构图，不要凑页。"
    "偏离表述和数字与给出的矩阵一致。其他客户或其他项目名称写成【待补】。"
    "服务案例只写脱敏框架，不写真实客户、人员、报价或证书。"
)

_section_writer: Callable[..., str] | None = None


def bind_section_writer(fn: Callable[..., str] | None):
    global _section_writer
    previous = _section_writer
    _section_writer = fn
    return previous


def reset_section_writer(previous: Callable[..., str] | None) -> None:
    global _section_writer
    _section_writer = previous


def _clauses(workflow: dict) -> list[dict]:
    return [row for row in (workflow.get("requirements") or {}).values() if row.get("technical_clause")]


def _pages(record: dict) -> list[str]:
    lines: list[str] = []
    for page in record.get("pages") or []:
        text = page if isinstance(page, str) else str(page.get("text") or "")
        lines.extend(text.splitlines())
    return lines


def find_samples(workflow: dict) -> list[dict]:
    """只认招标文件和技术规范书里的技术偏离表。商务偏离表、报价偏离表跳过。"""
    samples = []
    for record in (workflow.get("files") or {}).values():
        if record.get("file_role") not in ("tender", "tech_spec"):
            continue
        lines = _pages(record)
        for index, line in enumerate(lines):
            if not _deviation_sample(line):
                continue
            headers = None
            window = []
            for follow in lines[index + 1:index + 8]:
                if SAMPLE_TITLE.search(follow):
                    break
                window.append(follow)
            for follow in window:
                if "|" in follow and "偏离表" not in follow:
                    headers = [part.strip() for part in follow.split("|") if part.strip()]
                    break
            if not headers:
                continue
            nearby = "\n".join(window)
            if "偏离项" in nearby or "只列" in nearby:
                mode = "deviations"
            elif "逐条" in nearby:
                mode = "all"
            else:
                mode = "unspecified"
            samples.append({
                "title": line.strip(),
                "headers": headers,
                "mode": mode,
                "scope": "technical" if ("商务" in line and "技术" in line) else "",
                "attachment": "附件" in line or (index > 0 and "附件" in lines[index - 1]),
                "file_id": record.get("id") or "",
            })
    return samples


def _deviation_sample(line: str) -> bool:
    """偏离表、偏差表都认。只有商务或报价、没有技术的表跳过。"""
    if not SAMPLE_TITLE.search(line):
        return False
    commercial = "商务" in line or "报价" in line
    return "技术" in line or not commercial


def deviation_note(workflow: dict) -> str:
    if not workflow.get("technical_outline"):
        return ""
    return "" if find_samples(workflow) else NO_SAMPLE


def writable(row: dict) -> bool:
    if row.get("status") != "confirmed":
        return False
    if row.get("response_origin") in ("", "retrieval_failed", "draft_failed"):
        return False
    return bool(str(row.get("response") or "").strip())


def assert_ready(state: Any, project_id: str, workflow: dict) -> None:
    if not workflow.get("plan_confirmed") or not workflow.get("technical_outline"):
        raise DomainError(409, "REQUIREMENT_NOT_READY", "目录还没确认。")
    if workflow.get("technical_retrieval") != "done":
        raise DomainError(409, "REQUIREMENT_NOT_READY", "历史检索还没结束。")
    pending = [
        row for row in _clauses(workflow)
        if row.get("response_origin") == "history" and row.get("response_type") == "comply" and row.get("status") != "confirmed"
    ]
    if pending:
        raise DomainError(409, "REQUIREMENT_NOT_READY", "有历史依据的无偏离行还没确认。")


def _local_model(model: Any) -> bool:
    if not (model and getattr(model, "is_real_model", False) and getattr(model, "is_local", None) is not False):
        return False
    url = getattr(model, "base_url", "") or ""
    if not url:
        return True
    from icg.infra.openai_model import is_public_model_url
    return not is_public_model_url(url)


def scrub(text: str, row: dict) -> str:
    source = f"{row.get('text') or ''}{row.get('response') or ''}"
    if "其他项目" not in source:
        text = text.replace("其他项目", "【待补】")

    def replace(match: re.Match) -> str:
        name = match.group(0)
        return name if name in source else "【待补】"

    return BOOK.sub(replace, text)


def stand_in(title: str, row: dict) -> str:
    label = LABEL.get(row.get("response_type") or "", "无偏离")
    reason = str(row.get("deviation_reason") or "").strip()
    point = str(row.get("response") or "").strip() or "按本次招标条款执行。"
    explain = f"{label}。{reason}" if reason else f"{label}。{point}"
    return "\n".join([
        "响应说明",
        explain,
        "服务目标",
        f"按本次招标文件完成「{title}」。",
        "具体措施",
        point,
        "工作流程",
        "1. 接收本次要求。",
        "2. 按响应要点执行。",
        "3. 留下记录。",
        "| 步骤 | 做法 |",
        "| --- | --- |",
        "| 接收 | 按本次条款 |",
        "| 执行 | 按响应要点 |",
        "| 记录 | 留下记录 |",
        "交付物与记录",
        "留下本次服务记录。",
        "本项目结合点",
        f"只结合本次招标条款「{title}」。服务案例只保留脱敏框架，不写客户名称。",
    ])


def _complete(text: str) -> bool:
    return all(part in text for part in PARTS)


def produce_section(title: str, row: dict, model: Any) -> str:
    if _section_writer is not None:
        text = _section_writer(title, row)
    elif _local_model(model):
        point = str(row.get("response") or "")
        reason = str(row.get("deviation_reason") or "")
        label = LABEL.get(row.get("response_type") or "", "无偏离")
        text = model.suggest(SECTION_SYSTEM, f"小节：{title}\n本次条款：{row.get('text') or ''}\n矩阵：{label}。{reason or point}")
    else:
        text = stand_in(title, row)
    text = scrub(str(text or ""), row)
    if not _complete(text):
        raise RuntimeError("本节不完整")
    return text


def _level3(outline: dict) -> list[dict]:
    grouped: dict[str, list[dict]] = {}
    current = ""
    for heading in outline.get("headings") or []:
        if heading.get("level") == 2:
            current = heading.get("title") or ""
            grouped.setdefault(current, [])
        elif heading.get("level") == 3:
            grouped.setdefault(current, []).append(heading)
    ordered = []
    seen = set()
    for name in WRITE_ORDER:
        ordered.extend(grouped.get(name) or [])
        seen.add(name)
    for name, items in grouped.items():
        if name not in seen:
            ordered.extend(items)
    return ordered


def section_body(content: str, number: str, title: str) -> str:
    lines = (content or "").splitlines()
    marker = f"{number} {title}"
    start = next((index + 1 for index, line in enumerate(lines) if line.strip() == marker), None)
    if start is None:
        return ""
    end = next((index for index in range(start, len(lines)) if HEADING.match(lines[index].strip())), len(lines))
    kept = [line for line in lines[start:end] if line.strip() != "需要核对"]
    return "\n".join(kept).strip()


def inconsistent(body: str, row: dict) -> bool:
    if not body.strip() or body.strip() == "待补":
        return False
    label = LABEL.get(row.get("response_type") or "")
    if not label:
        return False
    head = body.split("服务目标", 1)[0]
    names = [name for name in ("无偏离", "正偏离", "负偏离") if name in head]
    if any(name != label for name in names) or label not in names:
        return True
    source = f"{row.get('text') or ''} {row.get('response') or ''} {row.get('deviation_reason') or ''}"
    source_numbers = set(re.findall(r"\d+", source))
    body_numbers = [number for number in re.findall(r"\d+", body) if int(number) >= 10]
    extras = [number for number in body_numbers if number not in source_numbers]
    return len(set(body_numbers)) >= 2 and len(set(extras)) >= 1


def review_titles(workflow: dict, content: str) -> list[str]:
    outline = workflow.get("technical_outline") or {}
    rows = {row.get("id"): row for row in _clauses(workflow)}
    found = []
    for heading in outline.get("headings") or []:
        if heading.get("level") != 3:
            continue
        row = rows.get(heading.get("requirement_id"))
        body = section_body(content, heading.get("number") or "", heading.get("title") or "")
        if row and inconsistent(body, row):
            found.append(heading.get("title") or "")
    return found


def _assemble(outline: dict, bodies: dict[str, str], reviews: set[str]) -> str:
    lines: list[str] = []
    for heading in outline.get("headings") or []:
        lines.append(f"{heading['number']} {heading['title']}")
        if heading.get("level") == 3:
            body = bodies.get(heading.get("requirement_id") or "") or "待补"
            lines.append(body)
            if heading.get("requirement_id") in reviews and "需要核对" not in body.splitlines():
                lines.append("需要核对")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def write_volume(state: Any, project_id: str, workflow: dict, section: str | None, model: Any) -> dict:
    """按生成顺序写三级标题。目录顺序不改。失败的节保留原正文。"""
    assert_ready(state, project_id, workflow)
    outline = workflow["technical_outline"]
    chapter = state.chapters.get(outline.get("chapter_id") or "")
    if chapter is None:
        raise DomainError(404, "NOT_FOUND", "没有服务方案这一章。")
    rows = {row.get("id"): row for row in _clauses(workflow)}
    headings = _level3(outline)
    if section:
        headings = [item for item in headings if item.get("title") == section]
        if not headings:
            raise DomainError(404, "NOT_FOUND", "没有这一节。")
    current = chapter.content or ""
    bodies = {
        item.get("requirement_id"): section_body(current, item.get("number") or "", item.get("title") or "")
        for item in _level3(outline)
    }
    failed: list[str] = []
    for heading in headings:
        row = rows.get(heading.get("requirement_id"))
        identity = heading.get("requirement_id") or ""
        title = heading.get("title") or ""
        if row is None or not writable(row):
            bodies[identity] = "待补"
            continue
        try:
            bodies[identity] = produce_section(title, row, model)
        except Exception:
            failed.append(title)
            if not bodies.get(identity):
                bodies[identity] = "待补"
    reviews = {
        item.get("requirement_id")
        for item in _level3(outline)
        if (row := rows.get(item.get("requirement_id"))) and inconsistent(bodies.get(item.get("requirement_id")) or "", row)
    }
    chapter.content = _assemble(outline, bodies, reviews)
    chapter.revision = int(getattr(chapter, "revision", 1) or 1) + 1
    if not failed and not section:
        workflow["needs_regeneration"] = [
            item for item in (workflow.get("needs_regeneration") or []) if item != chapter.id
        ]
    return {"failed": failed, "chapter_id": chapter.id}


def _cell(header: str, heading: dict, row: dict, sample: dict) -> str:
    if sample.get("scope") == "technical" and "商务" in header and "技术" not in header:
        return ""
    if "页码" in header:
        return ""
    if "说明" in header or "理由" in header:
        if row.get("response_type") == "comply":
            return ""
        return str(row.get("deviation_reason") or "")
    if "偏离" in header:
        return TABLE_LABEL.get(row.get("response_type") or "", "")
    if "响应" in header or "投标" in header:
        return str(row.get("response") or "")
    if "序号" in header:
        return str(heading.get("number") or "")
    return str(heading.get("title") or "")


def table_rows(sample: dict, workflow: dict) -> list[list[str]]:
    outline = workflow.get("technical_outline") or {}
    rows = {row.get("id"): row for row in _clauses(workflow)}
    filled = []
    for heading in outline.get("headings") or []:
        if heading.get("level") != 3:
            continue
        row = rows.get(heading.get("requirement_id"))
        if row is None or not writable(row):
            continue
        if sample.get("mode") == "deviations" and not critical(row) and row.get("response_type") not in ("exceed", "deviate"):
            continue
        filled.append([_cell(header, heading, row, sample).replace("|", "／").replace("\n", " ") for header in sample["headers"]])
    return filled


def markdown_table(sample: dict, workflow: dict) -> str:
    headers = sample["headers"]
    lines = [
        f"## {sample['title']}",
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in table_rows(sample, workflow):
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def chapter_markdown(title: str, content: str) -> str:
    lines = [f"# {title}"]
    for line in (content or "").splitlines():
        matched = HEADING.match(line.strip())
        if matched:
            lines.append(f"{'#' * (matched.group(1).count('.') + 1)} {line.strip()}")
        else:
            lines.append(line)
    return "\n".join(lines)


def export_parts(workflow: dict, title: str, content: str) -> dict:
    """偏离表只在导出时按当时矩阵填写，不写回服务方案正文。"""
    samples = find_samples(workflow)
    inline = [sample for sample in samples if not sample["attachment"]]
    attached = [sample for sample in samples if sample["attachment"]]
    markdown = chapter_markdown(title, content)
    if inline:
        markdown += "\n\n" + "\n\n".join(markdown_table(sample, workflow) for sample in inline)
    attachment = "\n\n".join(markdown_table(sample, workflow) for sample in attached) if attached else ""
    return {"markdown": markdown, "attachment": attachment, "note": "" if samples else NO_SAMPLE}
