# 为什么有这个文件：技术分册按节写正文，并在导出内部稿时照招标样表填偏离表。
# 它解决什么问题：确认目录不会自动生成；没有样表时不自造偏离表；一节失败不改掉其他节。

from __future__ import annotations

import re
from typing import Any, Callable

from icg.domain.domain import DomainError
from icg.domain.matrix import critical

HEADING = re.compile(r"^(\d+(?:\.\d+)*)\s+(\S.*)$")
SAMPLE_TITLE = re.compile(r"偏离表|偏差表")
BOOK = re.compile(r"《[^》]{1,40}》")
LABEL = {"comply": "无偏离", "exceed": "正偏离", "deviate": "负偏离"}
TABLE_LABEL = {"comply": "无偏离", "exceed": "正偏离", "deviate": "偏离"}
NO_SAMPLE = "这份招标文件没有提供偏离表格式。"
SECTION_SYSTEM = (
    "按本节挂接的招标要求组织技术响应正文；结构按该节实际需要安排，不要套固定六段模板。"
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
    # 矩阵确认不再是生成闸门；有可写响应即可落节。
    if row.get("response_origin") in ("", "retrieval_failed", "draft_failed", "no_evidence"):
        return False
    return bool(str(row.get("response") or "").strip())


def assert_ready(state: Any, project_id: str, workflow: dict) -> None:
    """确认目录是进入生成的唯一强制闸门；矩阵确认不挡。"""
    if not workflow.get("plan_confirmed") or not workflow.get("technical_outline"):
        raise DomainError(409, "REQUIREMENT_NOT_READY", "目录还没确认。")
    if workflow.get("technical_retrieval") == "running":
        raise DomainError(409, "REQUIREMENT_NOT_READY", "历史检索还在进行，请稍后再生成。")


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
        f"针对「{title}」的技术响应。",
        explain,
        point,
        "执行步骤：接收本次要求 → 按响应要点执行 → 留下记录。",
        "| 步骤 | 做法 |",
        "| --- | --- |",
        "| 接收 | 按本次条款 |",
        "| 执行 | 按响应要点 |",
        "| 记录 | 留下记录 |",
        "只结合本次招标条款；服务案例只保留脱敏框架，不写客户名称。",
    ])


def produce_section(title: str, row: dict, model: Any, *, knowledge: str = "",
                    task: dict | None = None, requirements: list[dict] | None = None) -> str:
    rows = requirements or ([row] if row else [])
    primary = rows[0] if rows else (row or {})
    if _section_writer is not None:
        text = _section_writer(title, primary)
    elif _local_model(model):
        req_block = "\n".join(
            f"- [{item.get('risk_level') or 'medium'}] {item.get('extracted_summary') or item.get('text') or ''}"
            for item in rows
        )
        points = "\n".join(f"- {point}" for point in (task or {}).get("response_points") or [])
        rejection = [
            item for item in rows
            if item.get("is_rejection_criterion") and item.get("requirement_type") != "qualification"
        ]
        reject_block = "\n".join(
            f"- 废标约束：{item.get('extracted_summary') or item.get('text') or ''}" for item in rejection
        )
        point = str(primary.get("response") or "")
        reason = str(primary.get("deviation_reason") or "")
        label = LABEL.get(primary.get("response_type") or "", "无偏离")
        user = (
            f"章节任务：{title}\n"
            f"必须覆盖的招标要求：\n{req_block or '（无）'}\n"
            f"响应要点：\n{points or reason or point or '（按要求逐条响应）'}\n"
            f"项目级/本章废标硬约束：\n{reject_block or '（无技术类废标）'}\n"
            f"偏离口径：{label}。"
            + (f"\n\n企业知识检索：\n{knowledge}" if knowledge else "\n\n企业知识检索：无命中；无依据处标【待确认】，禁止编造企业能力。")
        )
        text = model.suggest(SECTION_SYSTEM, user)
    else:
        text = stand_in(title, primary)
        if rows and len(rows) > 1:
            extra = "\n".join(
                f"针对「{clip}」：按招标要求落实并保留记录。"
                for item in rows[1:3]
                for clip in [str(item.get("extracted_summary") or item.get("text") or "")[:40]]
            )
            text = f"{text}\n\n{extra}".strip()
        if knowledge:
            text = f"{text}\n\n（已参考企业知识库检索结果，正式证据仍须可追溯。）"
        elif not knowledge:
            text = f"{text}\n\n【待确认】本节企业知识库无命中依据，具体能力参数须人工核对后补全。"
    text = scrub(str(text or ""), primary)
    if len(str(text or "").strip()) < 40:
        raise RuntimeError("本节不完整")
    return text


def _leaves(outline: dict) -> list[dict]:
    """按确认目录顺序取挂有任务或条款的叶子节点。"""
    return [
        heading for heading in outline.get("headings") or []
        if heading.get("task_id") or heading.get("requirement_id")
    ]


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
    for heading in _leaves(outline):
        row = rows.get(heading.get("requirement_id"))
        body = section_body(content, heading.get("number") or "", heading.get("title") or "")
        if row and inconsistent(body, row):
            found.append(heading.get("title") or "")
    return found


def _leaf_key(heading: dict) -> str:
    return str(heading.get("task_id") or heading.get("requirement_id") or heading.get("number") or "")


def _assemble(outline: dict, bodies: dict[str, str], reviews: set[str]) -> str:
    lines: list[str] = []
    for heading in outline.get("headings") or []:
        lines.append(f"{heading['number']} {heading['title']}")
        key = _leaf_key(heading)
        if key and (heading.get("task_id") or heading.get("requirement_id")):
            body = bodies.get(key) or "待补"
            lines.append(body)
            if key in reviews and "需要核对" not in body.splitlines():
                lines.append("需要核对")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def write_volume(state: Any, project_id: str, workflow: dict, section: str | None, model: Any,
                 *, knowledge_base: Any = None) -> dict:
    """按确认目录任务叶子写正文。目录顺序不改。失败的节保留原正文。先检索本标，公司库只作可引用证据，并记审计。"""
    assert_ready(state, project_id, workflow)
    from icg.domain.technical_rag import knowledge_prompt_block, retrieve_for_section, section_query
    outline = workflow["technical_outline"]
    chapter = state.chapters.get(outline.get("chapter_id") or "")
    if chapter is None:
        raise DomainError(404, "NOT_FOUND", "没有服务方案这一章。")
    company_id = getattr(state.projects.get(project_id), "company_id", "") or ""
    rows = {row.get("id"): row for row in _clauses(workflow)}
    tasks = workflow.get("response_tasks") or {}
    headings = _leaves(outline)
    if section:
        headings = [item for item in headings if item.get("title") == section]
        if not headings:
            raise DomainError(404, "NOT_FOUND", "没有这一节。")
    current = chapter.content or ""
    bodies = {
        _leaf_key(item): section_body(current, item.get("number") or "", item.get("title") or "")
        for item in _leaves(outline)
    }
    failed: list[str] = []
    audits: list[dict] = []
    for heading in headings:
        key = _leaf_key(heading)
        title = heading.get("title") or ""
        task = tasks.get(heading.get("task_id") or "") if heading.get("task_id") else None
        req_ids = list(heading.get("requirement_ids") or [])
        if not req_ids and heading.get("requirement_id"):
            req_ids = [heading["requirement_id"]]
        if task:
            req_ids = list(task.get("requirement_ids") or req_ids)
        req_rows = [rows[rid] for rid in req_ids if rid in rows]
        primary = req_rows[0] if req_rows else rows.get(heading.get("requirement_id"))
        if primary is None:
            bodies[key] = "待补\n【待确认】本节未挂接招标要求。"
            audits.append({"section": title, "task_id": key, "skipped": "no_requirement"})
            continue
        # 即使矩阵检索失败，仍应用模型/替身写实质框架，缺依据标待确认，禁止整节空「待补」冒充完成。
        query = section_query(title, primary, task=task, requirements=req_rows)
        chunks, rag_audit = retrieve_for_section(knowledge_base, company_id, query, workflow)
        rag_audit["section"] = title
        rag_audit["task_id"] = heading.get("task_id")
        rag_audit["requirement_ids"] = req_ids
        audits.append(rag_audit)
        knowledge = knowledge_prompt_block(chunks)
        try:
            bodies[key] = produce_section(
                title, primary, model, knowledge=knowledge, task=task, requirements=req_rows,
            )
            if task is not None:
                task["generation_status"] = "generated"
                task["response_status"] = "generated" if chunks else "needs_confirm"
        except Exception:
            failed.append(title)
            if not bodies.get(key):
                bodies[key] = (
                    f"【待确认】「{title}」自动生成失败，请按下列要求人工补写。\n"
                    + "\n".join(f"- {row.get('extracted_summary') or row.get('text') or ''}" for row in req_rows[:8])
                )
            if task is not None:
                task["generation_status"] = "failed"
                task["response_status"] = "gap"
    workflow["technical_rag_audit"] = audits[-20:]
    reviews: set[str] = set()
    for item in _leaves(outline):
        ids = list(item.get("requirement_ids") or [])
        if not ids and item.get("requirement_id"):
            ids = [item["requirement_id"]]
        row = rows.get(ids[0]) if ids else None
        if row and inconsistent(bodies.get(_leaf_key(item)) or "", row):
            reviews.add(_leaf_key(item))
    chapter.content = _assemble(outline, bodies, reviews)
    from icg.domain.technical_quality import apply_quality_markers, evaluate_quality
    quality = evaluate_quality(workflow, chapter.content)
    chapter.content = apply_quality_markers(chapter.content, quality.get("review_titles") or [], outline)
    quality = evaluate_quality(workflow, chapter.content)
    workflow["technical_quality"] = quality
    chapter.revision = int(getattr(chapter, "revision", 1) or 1) + 1
    if not failed and not section:
        workflow["needs_regeneration"] = [
            item for item in (workflow.get("needs_regeneration") or []) if item != chapter.id
        ]
    return {
        "failed": failed,
        "chapter_id": chapter.id,
        "rag_audit": audits,
        "quality": quality,
    }


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
    for heading in _leaves(outline):
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
