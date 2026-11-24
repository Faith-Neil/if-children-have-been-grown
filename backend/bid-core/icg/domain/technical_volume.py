# 为什么有这个文件：技术分册按节写正文，并在导出内部稿时照招标样表填偏离表。
# 它解决什么问题：确认目录不会自动生成；没有样表时不自造偏离表；一节失败不改掉其他节。

from __future__ import annotations

import json
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable

from icg.domain.domain import DomainError
from icg.domain.matrix import critical
from icg.domain.technical_constraint_context import build_constraint_context, row_is_non_tech
from icg.domain.writing_knowledge_prompt import (
    CAPABILITY_GAP_LINE,
    HISTORY_HEADING,
    MATERIALS_HEADING,
    history_foreign_names,
    mask_foreign_names,
)

HEADING = re.compile(r"^(\d+(?:\.\d+)*)\s+(\S.*)$")
SAMPLE_TITLE = re.compile(r"偏离表|偏差表")
BOOK = re.compile(r"《[^》]{1,40}》")
LABEL = {"comply": "无偏离", "exceed": "正偏离", "deviate": "负偏离"}
TABLE_LABEL = {"comply": "无偏离", "exceed": "正偏离", "deviate": "偏离"}
NO_SAMPLE = "这份招标文件没有提供偏离表格式。"
SECTION_SYSTEM = (
    "按服务方案写本节，每节按自己的事情写，不要套同一张卡片。"
    "禁止把「服务内容」「服务频率」「服务模式」「实施步骤」「交付物」当作必写的五段标题。"
    "一级章写本项目要解决什么、下面几节各管什么，并点出业主和系统名。"
    "叶子节写具体做法，并给出一张 markdown 表，列名是事项、周期、交付。"
    "正文写出「本项目」，并写明业主与系统。没有依据时不要编造业主、系统或参数。"
    "历史材料只作写法参考，不能把别的项目写成正在服务的系统。"
    "本标业主、系统、期限和 SLA 以招标与项目事实为准。"
    "禁止把招标原文复述或改写成正文。约束句保留对应 [标:]。"
    "本标事实不要写成【待补】。"
    "正文不写偏离标签，偏离只留在偏离表。"
    "正文不写保证金、信用中国、否决投标，也不写报价和营业执照。"
    "没有依据的能力、人员、参数标【待确认】，禁止虚构参数。"
    "废标硬约束必须遵守，不得改写成能力表述，也不得写成已响应废标。"
)
SLA_HINT = re.compile(r"7\s*[×*xX]\s*24|响应时限|到场时限|故障响应")
SLA_TITLES = ("运维", "巡检", "故障", "保障", "响应", "服务级别")

# 节流事件。SSE 一帧是 `event: <event>` 加一行 `data:` JSON，两边的 event 相同。
# section_id 是目录叶子的 task_id，否则 requirement_id，否则编号。
# sections.fanout    concurrency（同时生成的上限，不是本次节数）、section_ids
# section.started    section_id、title
# section.delta      section_id、text（本次新增，不是累计全文）
# section.done       section_id、text（scrub 之后要落盘的整节正文）
# section.failed     section_id、message
# section.cancelled  section_id（这一节不改原文）
# volume.done        chapter_id、revision、failed、replay（重放没有 delta）
# volume.cancelled   断开或取消后整次不写入章节
# volume.failed      message
# session.started    job_id（生成会话的任务编号，订阅从这里开始重放）
# session.live       之前的事件是重放的积压，之后是实时事件
# task.patched       task_id、generation_status（generating/generated/failed），可带 stage（retrieve/deviate/write_section）、
#                    section_title、response_status、response_types（requirement_id → comply/exceed/deviate/not_applicable）；覆盖视图按任务合并
SECTION_STREAM_CONCURRENCY = 3
_SECTION_EVENTS = (
    "session.started",
    "session.live",
    "sections.fanout",
    "section.started",
    "section.delta",
    "section.done",
    "section.failed",
    "section.cancelled",
    "volume.done",
    "volume.cancelled",
    "volume.failed",
    "task.patched",
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


def _section_points(title: str, task: dict | None, workflow: dict | None) -> list[str]:
    """本节响应要点。项目级 SLA 只留给运维/故障类章节，避免每节粘同一段时限。"""
    raw = [str(point).strip() for point in (task or {}).get("response_points") or [] if str(point).strip()]
    promises = {
        str(value).strip()
        for value in ((workflow or {}).get("technical_promises") or {}).values()
        if str(value).strip()
    }
    title_ok = any(word in (title or "") for word in SLA_TITLES)
    kept: list[str] = []
    for point in raw:
        if not title_ok and (point in promises or SLA_HINT.search(point)):
            continue
        kept.append(point)
    return kept


def _shown_clause(item: dict) -> str:
    return str(item.get("extracted_summary") or item.get("text") or "").strip()


def format_section_sse(event: dict) -> str:
    """把一节事件写成 SSE 帧。未知 event 直接拒绝，避免把别的 JSON 冒充节流。"""
    kind = str(event.get("event") or "")
    if kind not in _SECTION_EVENTS:
        raise ValueError(kind)
    return f"event: {kind}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"


def _model_streams(model: Any) -> bool:
    """节流只要模型提供 stream_suggest 就逐段输出。stream_enabled 只约束普通 suggest 的请求体，from_env 默认为假，不能挡住这一路。"""
    return callable(getattr(model, "stream_suggest", None))


def _cancelled(cancel: Any) -> bool:
    return cancel is not None and cancel.is_set()


def _stop_if_cancelled(cancel: Any) -> None:
    if _cancelled(cancel):
        from icg.infra.openai_model import ModelCancelled
        raise ModelCancelled("cancelled")


def _complete_section(model: Any, user: str, *, on_delta: Callable[[str], None] | None, cancel: Any) -> str:
    from icg.infra.openai_model import SECTION_CALL, AuditIoLabel, call_with_profile

    if on_delta is not None and _model_streams(model):
        from icg.infra.model_fallback import call_model

        def guard(piece: str) -> None:
            _stop_if_cancelled(cancel)
            on_delta(piece)

        with AuditIoLabel("SECTION"):
            return call_model(
                model, SECTION_SYSTEM, user, on_delta=guard, cancel=cancel, profile=SECTION_CALL,
            ).text
    with AuditIoLabel("SECTION"):
        text = call_with_profile(model.suggest, SECTION_SYSTEM, user, profile=SECTION_CALL)
    _stop_if_cancelled(cancel)
    if on_delta is not None:
        on_delta(text)
    return text


def strip_model_thinking(text: str) -> str:
    """去掉 Thinking Process 前缀。空行后的段落是正文；没有空行就从第一行非空文字开始。不用五段标题当起点。"""
    raw = str(text or "")
    marker = "Thinking Process:"
    at = raw.find(marker)
    if at < 0:
        return raw
    rest = raw[at + len(marker):]
    parts = re.split(r"\n[ \t]*\n", rest, maxsplit=1)
    if len(parts) == 2 and parts[1].strip():
        return parts[1].lstrip()
    lines = rest.splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)
    return "\n".join(lines)


def _bullet_block(lines: list[str]) -> str:
    kept = [str(line).strip() for line in lines if str(line).strip()]
    if not kept:
        return "（无）"
    return "\n".join(f"- {line}" for line in kept)


def _requirement_ids(rows: list[dict], task: dict | None) -> list[str]:
    found: list[str] = []
    for item in rows:
        rid = str(item.get("id") or "").strip()
        if rid and rid not in found:
            found.append(rid)
    for rid in (task or {}).get("requirement_ids") or []:
        text = str(rid or "").strip()
        if text and text not in found:
            found.append(text)
    return found


def _tender_rows(rows: list[dict]) -> list[dict]:
    """招标原文只留要写的技术句。废标全文和商务包装不进这一块。"""
    kept: list[dict] = []
    for item in rows:
        if row_is_non_tech(item):
            continue
        if item.get("is_rejection_criterion"):
            continue
        if item.get("clause_role") == "rejection_constraint":
            continue
        if item.get("requirement_type") in ("rejection_item", "other_constraint"):
            continue
        kept.append(item)
    return kept


def _section_user(title: str, rows: list[dict], task: dict | None, workflow: dict | None,
                  knowledge: str) -> str:
    """五块固定标签，空块写（无），不删标签。"""
    cover = _tender_rows(rows)
    graded = build_constraint_context(rows, workflow, task)
    ids = _requirement_ids(rows, task)
    points = _section_points(title, task, workflow)
    tender = _bullet_block(
        f"[{item.get('risk_level') or 'medium'}] {_shown_clause(item)}" for item in cover
    )
    evidence = knowledge.strip() if str(knowledge or "").strip() else CAPABILITY_GAP_LINE
    from icg.domain.technical_digest import rejection_lines, scoring_criteria

    task_body = "\n".join([
        f"标题：{title}",
        "要求编号：" + ("、".join(ids) if ids else "（无）"),
        "挂载要点：",
        _bullet_block(points),
        "评分标准：",
        _bullet_block(scoring_criteria(rows)),
        "本章硬约束：",
        _bullet_block(list(graded.section)),
        "废标清单（全文不得违反）：",
        _bullet_block(rejection_lines(workflow)),
    ])
    rules = (
        "不虚构能力、参数或资质。没有依据时标待确认。"
        "不得把废标写成已响应废标。"
        "正文不写偏离标签。"
    )
    return "\n".join([
        "项目级约束",
        _bullet_block(list(graded.project)),
        "本章任务",
        task_body,
        "招标原文",
        tender,
        "知识库",
        evidence,
        "生成规则",
        rules,
    ])


def produce_section(title: str, row: dict, model: Any, *, knowledge: str = "",
                    task: dict | None = None, requirements: list[dict] | None = None,
                    workflow: dict | None = None, on_delta: Callable[[str], None] | None = None,
                    cancel: Any = None, foreign_names: list[str] | None = None) -> str:
    rows = requirements or ([row] if row else [])
    primary = rows[0] if rows else (row or {})
    emitted = False
    if _section_writer is not None:
        text = _section_writer(title, primary)
    elif _local_model(model):
        user = _section_user(title, rows, task, workflow, knowledge)
        text = _complete_section(model, user, on_delta=on_delta, cancel=cancel)
        emitted = on_delta is not None
    else:
        text = stand_in(title, primary)
        if rows and len(rows) > 1:
            extra = "\n".join(
                f"针对「{clip}」：按招标要求落实并保留记录。"
                for item in rows[1:3]
                for clip in [str(item.get("extracted_summary") or item.get("text") or "")[:40]]
            )
            text = f"{text}\n\n{extra}".strip()
        has_company = HISTORY_HEADING in (knowledge or "") or MATERIALS_HEADING in (knowledge or "")
        if has_company:
            text = f"{text}\n\n（已参考企业历史标书或权威资料，正式证据仍须可追溯。）"
        else:
            text = f"{text}\n\n【待确认】本节缺少企业能力依据，能力参数须人工核对，不得用招标原文代替。"
    if on_delta is not None and not emitted:
        _stop_if_cancelled(cancel)
        on_delta(text)
    text = scrub(str(text or ""), primary)
    if foreign_names:
        text = mask_foreign_names(text, foreign_names)
    text = strip_model_thinking(text)
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


def select_section(headings: list[dict], section: str) -> list[dict]:
    """section 先按节键（任务编号）匹配，同名小节不会被一起重写；匹配不到再按标题。"""
    by_key = [item for item in headings if _leaf_key(item) == section]
    return by_key or [item for item in headings if item.get("title") == section]


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


def _apply_one(patch: dict, bodies: dict[str, str], failed: list[str], audits: list[dict]) -> None:
    if patch.get("cancelled"):
        if patch.get("audit"):
            audits.append(patch["audit"])
        return
    if patch.get("audit") is not None:
        audits.append(patch["audit"])
    if patch.get("skipped") or patch.get("failed"):
        if patch.get("failed"):
            failed.append(patch["title"])
            if not bodies.get(patch["key"]):
                bodies[patch["key"]] = patch["body"]
        else:
            bodies[patch["key"]] = patch["body"]
    else:
        bodies[patch["key"]] = patch["body"]
    task = patch.get("task")
    if isinstance(task, dict) and patch.get("task_patch"):
        task.update(patch["task_patch"])


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _draft_one(heading: dict, rows: dict, tasks: dict, model: Any, workflow: dict, knowledge_base: Any,
               company_id: str, emit: Callable[[dict], None] | None, cancel: Any) -> dict:
    """写一节。只返回这一节的正文和任务补丁，不改共享的 bodies。"""
    from icg.domain.technical_rag import knowledge_prompt_block, rag_summary, retrieve_for_section, section_query
    from icg.infra.openai_model import ModelCancelled

    key = _leaf_key(heading)
    title = heading.get("title") or ""
    if emit is not None and _cancelled(cancel):
        emit({"event": "section.cancelled", "section_id": key})
        return {"key": key, "title": title, "cancelled": True}
    if emit is not None:
        emit({"event": "section.started", "section_id": key, "title": title})
    task = tasks.get(heading.get("task_id") or "") if heading.get("task_id") else None
    req_ids = list(heading.get("requirement_ids") or [])
    if not req_ids and heading.get("requirement_id"):
        req_ids = [heading["requirement_id"]]
    if task:
        req_ids = list(task.get("requirement_ids") or req_ids)
    req_rows = [rows[rid] for rid in req_ids if rid in rows]
    primary = req_rows[0] if req_rows else rows.get(heading.get("requirement_id"))
    if primary is None:
        body = "待补\n【待确认】本节未挂接招标要求。"
        if emit is not None:
            emit({"event": "section.done", "section_id": key, "text": body})
        return {
            "key": key, "title": title, "body": body, "skipped": True,
            "audit": {"section": title, "task_id": key, "skipped": "no_requirement"},
        }
    def patch_task(change: dict | None) -> None:
        if emit is not None and task is not None and change:
            emit({"event": "task.patched", "task_id": heading["task_id"], "section_title": title, **change})

    def response_type_map() -> dict[str, str]:
        return {
            str(row["id"]): str(row["response_type"])
            for row in req_rows
            if row.get("id") and row.get("response_type")
        }

    patch_task({"generation_status": "generating", "stage": "retrieve"})
    # 即使矩阵检索失败，仍用模型或替身写实质框架，缺依据标待确认，禁止整节空「待补」冒充完成。
    query = section_query(title, points=list((task or {}).get("response_points") or []))
    chunks, rag_audit = retrieve_for_section(knowledge_base, company_id, query, workflow)
    rag_audit["section"] = title
    rag_audit["task_id"] = heading.get("task_id")
    rag_audit["requirement_ids"] = req_ids
    rag_audit["stage"] = "retrieve"
    if _cancelled(cancel):
        if emit is not None:
            emit({"event": "section.cancelled", "section_id": key})
        return {"key": key, "title": title, "cancelled": True, "audit": rag_audit}

    from icg.domain.technical_section_stages import forbid_silent_deviate_only

    patch_task({"stage": "deviate", "response_types": response_type_map()})
    forbid_silent_deviate_only("write_section")

    foreign_names = history_foreign_names(chunks, workflow)
    knowledge = knowledge_prompt_block(chunks, workflow)

    patch_task({"stage": "write_section", "response_types": response_type_map()})

    def on_delta(piece: str) -> None:
        _stop_if_cancelled(cancel)
        if emit is not None:
            emit({"event": "section.delta", "section_id": key, "text": piece})

    try:
        body = produce_section(
            title, primary, model, knowledge=knowledge, task=task, requirements=req_rows,
            workflow=workflow, on_delta=on_delta if emit is not None else None,
            cancel=cancel if emit is not None else None, foreign_names=foreign_names,
        )
    except ModelCancelled:
        if emit is not None:
            emit({"event": "section.cancelled", "section_id": key})
        return {"key": key, "title": title, "cancelled": True, "audit": rag_audit}
    except Exception:
        if emit is not None:
            emit({"event": "section.failed", "section_id": key, "message": "本节生成失败"})
        fallback = (
            f"【待确认】「{title}」自动生成失败，请按下列要求人工补写。\n"
            + "\n".join(f"- {row.get('extracted_summary') or row.get('text') or ''}" for row in req_rows[:8])
        )
        task_patch = {
            "generation_status": "failed", "response_status": "gap", "rag": rag_summary(rag_audit, searched_at=_now_iso()),
            "failure_reason": "模型生成失败，可单节重试。",
        } if task is not None else None
        patch_task(task_patch)
        return {
            "key": key, "title": title, "failed": True, "body": fallback, "audit": rag_audit,
            "task": task, "task_patch": task_patch,
        }
    if emit is not None:
        emit({"event": "section.done", "section_id": key, "text": body})
    company_hits = int(rag_audit.get("history_hits") or 0) + int(rag_audit.get("material_hits") or 0)
    task_patch = {
        "generation_status": "generated",
        "response_status": "generated" if company_hits else "needs_confirm",
        "rag": rag_summary(rag_audit, searched_at=_now_iso()), "failure_reason": "",
        "confirmed_by": None, "confirmed_at": None,
    } if task is not None else None
    patch_task(task_patch)
    return {"key": key, "title": title, "body": body, "audit": rag_audit, "task": task, "task_patch": task_patch}


def write_volume(state: Any, project_id: str, workflow: dict, section: str | None, model: Any,
                 *, knowledge_base: Any = None, on_event: Callable[[dict], None] | None = None,
                 cancel: Any = None) -> dict:
    """按确认目录任务叶子写正文。目录顺序不改。失败的节保留原正文。先检索本标，公司库只作可引用证据，并记审计。
    on_event 收到节流事件。多节同时生成时，进行中的模型调用不超过 SECTION_STREAM_CONCURRENCY。
    cancel 置位后，还没写完的节保留原正文。"""
    assert_ready(state, project_id, workflow)
    outline = workflow["technical_outline"]
    chapter = state.chapters.get(outline.get("chapter_id") or "")
    if chapter is None:
        raise DomainError(404, "NOT_FOUND", "没有服务方案这一章。")
    company_id = getattr(state.projects.get(project_id), "company_id", "") or ""
    rows = {row.get("id"): row for row in _clauses(workflow)}
    tasks = workflow.get("response_tasks") or {}
    headings = _leaves(outline)
    if section:
        headings = select_section(headings, section)
        if not headings:
            raise DomainError(404, "NOT_FOUND", "没有这一节。")
    current = chapter.content or ""
    bodies = {
        _leaf_key(item): section_body(current, item.get("number") or "", item.get("title") or "")
        for item in _leaves(outline)
    }
    failed: list[str] = []
    audits: list[dict] = []
    emit_lock = threading.Lock()

    def emit(event: dict) -> None:
        if on_event is None:
            return
        with emit_lock:
            on_event(event)

    if on_event is not None and headings:
        emit({
            "event": "sections.fanout",
            "concurrency": SECTION_STREAM_CONCURRENCY,
            "section_ids": [_leaf_key(item) for item in headings],
        })

    def draft(heading: dict) -> dict:
        listener = emit if on_event is not None else None
        return _draft_one(
            heading, rows, tasks, model, workflow, knowledge_base, company_id, listener, cancel,
        )

    if on_event is not None and len(headings) > 1:
        cap = min(SECTION_STREAM_CONCURRENCY, len(headings))
        with ThreadPoolExecutor(max_workers=cap) as pool:
            futures = [pool.submit(draft, heading) for heading in headings]
            drafted: dict[str, dict] = {}
            for future in as_completed(futures):
                patch = future.result()
                drafted[patch["key"]] = patch
        patches = [drafted[_leaf_key(item)] for item in headings]
    else:
        patches = [draft(heading) for heading in headings]
    for patch in patches:
        _apply_one(patch, bodies, failed, audits)
    workflow["technical_rag_audit"] = audits[-20:]
    if model is not None:
        name = str(
            getattr(model, "display_name", "")
            or getattr(model, "model", "")
            or getattr(model, "name", "")
            or ""
        ).strip()
        if name:
            workflow["writer_model"] = {
                "name": name,
                "is_real": bool(getattr(model, "is_real_model", False) or getattr(model, "is_real", False)),
                "is_local": bool(getattr(model, "is_local", False) or getattr(model, "is_local_model", False)),
            }
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
    check_sections = []
    for item in _leaves(outline):
        key = _leaf_key(item)
        task = tasks.get(item.get("task_id") or "") if item.get("task_id") else None
        req_ids = list(item.get("requirement_ids") or [])
        if not req_ids and item.get("requirement_id"):
            req_ids = [item["requirement_id"]]
        if isinstance(task, dict):
            req_ids = list(task.get("requirement_ids") or req_ids)
        check_sections.append({
            "key": key,
            "title": item.get("title") or "",
            "body": bodies.get(key) or "",
            "task": task if isinstance(task, dict) else None,
            "rows": [rows[rid] for rid in req_ids if rid in rows],
        })
    from icg.domain.technical_constraint_check import evaluate_volume
    checked = evaluate_volume(workflow, check_sections)
    workflow["constraint_check"] = {
        "status": checked["status"],
        "missing": checked["missing"],
        "conflicts": checked["conflicts"],
        "notice": checked["notice"],
    }
    for item in check_sections:
        task = item["task"]
        if not isinstance(task, dict):
            continue
        view = checked["sections"].get(item["key"]) or {}
        task["constraint_check"] = {
            "status": view.get("status") or "passed",
            "missing": view.get("missing") or [],
            "conflicts": view.get("conflicts") or [],
            "notice": view.get("notice") or "",
        }
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
        "constraint_check": workflow.get("constraint_check"),
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
