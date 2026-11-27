# 为什么有这个文件：技术分册按节写正文，并在导出内部稿时照招标样表填偏离表。
# 它解决什么问题：确认目录不会自动生成；没有样表时不自造偏离表；一节失败不改掉其他节。

from __future__ import annotations

import json
import os
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
SAMPLE_TITLE = re.compile(r"偏离(?:说明)?表|偏差(?:说明)?表")
BOOK = re.compile(r"《[^》]{1,40}》")
LABEL = {"comply": "无偏离", "exceed": "正偏离", "deviate": "负偏离"}
TABLE_LABEL = {"comply": "无偏离", "exceed": "正偏离", "deviate": "偏离"}
NO_SAMPLE = "这份招标文件没有提供偏离表格式。"
FALLBACK_DEVIATION_SAMPLE = {
    "title": "技术偏离表",
    "headers": ["序号", "招标条款", "投标响应简述", "偏离说明", "投标文件对应章节号"],
    "mode": "all",
    "scope": "technical",
    "attachment": True,
    "file_id": "",
    "fallback": True,
}
SECTION_SYSTEM = (
    "按服务方案写本节，每节按自己的事情写，不要套同一张卡片。"
    "禁止把「服务内容」「服务频率」「服务模式」「实施步骤」「交付物」当作必写的五段标题。"
    "一级章写本项目要解决什么、下面几节各管什么，并点出业主和系统名。"
    "叶子节写具体做法，并按本节业务给出专属结构化 markdown 表格，列名必须贴合本节业务"
    "（如巡检节用「巡检项/深度/频次/输出物」，应急节用「故障场景/定级/响应动作/恢复目标」），"
    "严禁全书千篇一律套用「事项/周期/交付物」三列。"
    "除全书第一节外，严禁以「本项目旨在」「本项目面向」「本项目聚焦于」「本节阐述」开篇；"
    "直接写本节承诺的第一句事实。"
    "正文写出「本项目」，并写明业主与系统。没有依据时不要编造业主、系统或参数。"
    "历史材料只作写法参考，不能把别的项目写成正在服务的系统。"
    "本标业主、系统、期限和 SLA 以招标与项目事实为准，SLA 数字必须与全局项目事实逐字一致，"
    "不得用历史标书或经验值（如 30 分钟）替换本标承诺（如 15 分钟）。"
    "禁止把招标原文复述或改写成正文。约束句保留对应 [标:]。"
    "本标事实不得留空或用占位符代替。"
    "通用交付物名（报告、审批单、承诺书、记录表等）直接按规范命名起草，严禁挖成【待补】；"
    "仅客观私有事实缺口（真实人名、证书编号、历史案例编号、分支地址）输出 [待人工补充：具体项]。"
    "正文不写偏离标签，偏离只留在偏离表。"
    "正文不写保证金、信用中国、否决投标，也不写报价和营业执照。"
    "没有依据的能力、人员、参数写 [待人工补充：具体项]，禁止虚构参数。"
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
def _stream_concurrency() -> int:
    """章内并发生成上限。本地 30B 并发过高会把意图拆解/摘要等轻调用挤到超时降级，默认 2，可用 ICG_SECTION_CONCURRENCY 覆盖，限 1~4。"""
    try:
        value = int(os.environ.get("ICG_SECTION_CONCURRENCY", "2"))
    except ValueError:
        value = 2
    return max(1, min(4, value))
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
                # 表头本身可能写成「招标文件项目详细需求偏离说明表条款…」，
                # 含竖线时必须先按表头处理，不能被 SAMPLE_TITLE 误判成下一张样表标题。
                if "|" in follow:
                    # 表头后仍可能紧跟「逐条填写/只列出偏离项」说明，不能因为先看到表头就停止扫描。
                    window.append(follow)
                    continue
                if SAMPLE_TITLE.search(follow):
                    break
                window.append(follow)
            for follow in window:
                if "|" in follow:
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
                "scope": "business" if (("商务" in line or "报价" in line) and "技术" not in line) else "technical",
                "attachment": ("附件" in line or (index > 0 and "附件" in lines[index - 1]) or bool(re.match(r"^[一二三四五六七八九十]+[、.．]", line.strip()))),
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
    """写作后确定性边界：不做“凡书名号不在招标原文就挖空”的暴力替换。

    常规交付物、报告、标准协议名（如《巡检报告》《服务承诺书》）是模型应直接起草的规范名称；
    外项目实体由 foreign_names 遮罩成通用“相关机构”，真实私有事实缺口按 Prompt 使用
    `[待人工补充：具体项]`。这里只做语义等价的泛化词替换，避免产生缺宾语病句。
    """
    source = f"{row.get('text') or ''}{row.get('response') or ''}"
    if "其他项目" not in source:
        text = text.replace("其他项目", "同类项目")
    return text


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


def build_section_blueprint(heading: dict, rows: list[dict], task: dict | None, weight: str) -> dict:
    """叶子节写作规划卡：目标字数、必覆要点、禁重边界、表格与故障案例配额。
    目录确认后为每个叶子节确定性生成，模型写作与检索配额都按卡执行。"""
    title = str(heading.get("title") or "")
    points = list((task or {}).get("response_points") or [])
    target = {"core": 2600, "normal": 1600, "brief": 900}.get(weight, 1600)
    from icg.domain.technical_rag import wants_fault_cases
    case_ok = wants_fault_cases(title, points)
    scores = [
        str(row.get("score_item") or "").strip()
        for row in rows
        if row.get("section_kind") == "scoring" and str(row.get("score_item") or "").strip()
    ]
    return {
        "section_key": str(heading.get("task_id") or heading.get("requirement_id") or heading.get("number") or ""),
        "title": title,
        "target_words": target,
        "weight": weight,
        "scoring_hooks": sorted(set(scores))[:4],
        "must_cover": [str(p)[:80] for p in points[:6]],
        "forbidden_overlap": "相邻节已写的机制与承诺不得复述，只写本节职责内做法",
        "assigned_tables": "按本节业务生成专属结构化表格（列名贴业务，禁用千篇一律的事项/周期/交付物三列）",
        "assigned_cases": ["fault_cases"] if case_ok else [],
    }


def _section_weight(rows: list[dict], task: dict | None) -> str:
    """按章节权重分档：高分核心节 core、普通支撑节 normal、简明承诺节 brief。"""
    scores = [
        float(row["score"]) for row in rows
        if isinstance(row.get("score"), (int, float)) and row.get("section_kind") == "scoring"
    ]
    top = max(scores) if scores else 0.0
    if top >= 5 or len(rows) >= 6:
        return "core"
    points = list((task or {}).get("response_points") or [])
    if not scores and len(rows) <= 2 and len(points) <= 2:
        return "brief"
    return "normal"


def _section_profile(weight: str):
    from icg.infra.openai_model import SECTION_BRIEF_CALL, SECTION_CALL, SECTION_CORE_CALL
    return {"core": SECTION_CORE_CALL, "brief": SECTION_BRIEF_CALL}.get(weight, SECTION_CALL)


_CLOSE_END = re.compile(r"(?:[。！？；;]|[)）\]】」”]|\|)\s*$")
_CONTINUE_SYSTEM = (
    "你是投标服务方案续写助手。上一节正文写到一半被截断。"
    "只输出尚未写完的剩余内容：先把截断的那一行补完整，再把本节自然收尾。"
    "严禁重复已写出的任何句子，严禁输出小节标题，严禁输出思考过程或解释。"
)


def _unclosed_tail(text: str) -> bool:
    tail = str(text or "").rstrip()
    if not tail:
        return False
    last = tail.splitlines()[-1].strip()
    if last.startswith("|") and not last.endswith("|"):
        return True
    return not _CLOSE_END.search(tail)


def _trim_broken_tail(text: str) -> str:
    tail = str(text or "").rstrip()
    if not tail:
        return tail
    lines = tail.splitlines()
    last = lines[-1].strip()
    if last.startswith("|") and not last.endswith("|"):
        lines.pop()
    return "\n".join(lines).rstrip()


def _finish_reason(model: Any) -> str:
    """本地 OpenAI 兼容端点透出的 finish_reason；WithFallback 时看主/备实际提供方。"""
    for candidate in (model, getattr(model, "primary", None), getattr(model, "fallback", None)):
        value = str(getattr(candidate, "last_finish_reason", "") or "")
        if value:
            return value
    return ""


def _trim_unfinished_sentence(text: str) -> str:
    """续写失败时不把半句逗号尾巴交付导出：优先删除末尾未闭合短行，长行退到最近句读。"""
    tail = _trim_broken_tail(text)
    if not tail or _CLOSE_END.search(tail):
        return tail
    lines = tail.splitlines()
    last = lines[-1].strip() if lines else ""
    if last and len(last) <= 120:
        lines.pop()
        trimmed = "\n".join(lines).rstrip()
        if trimmed:
            return trimmed
    cut = max(tail.rfind(mark) for mark in ("。", "！", "？", "；", ";"))
    return tail[:cut + 1].rstrip() if cut >= max(0, len(tail) - 500) else tail


def _merge_continuation(body: str, extra: str) -> str:
    extra = str(extra or "").lstrip()
    if not extra:
        return body
    tail = body[-80:]
    cut = 0
    for size in range(min(60, len(tail), len(extra)), 2, -1):
        if extra.startswith(tail[-size:]):
            cut = size
            break
    if cut:
        return body.rstrip() + "\n" + extra[cut:].lstrip()
    return body.rstrip() + "\n" + extra


def _model_streams(model: Any) -> bool:
    """节流只要模型提供 stream_suggest 就逐段输出。stream_enabled 只约束普通 suggest 的请求体，from_env 默认为假，不能挡住这一路。"""
    return callable(getattr(model, "stream_suggest", None))


def _cancelled(cancel: Any) -> bool:
    return cancel is not None and cancel.is_set()


def _stop_if_cancelled(cancel: Any) -> None:
    if _cancelled(cancel):
        from icg.infra.openai_model import ModelCancelled
        raise ModelCancelled("cancelled")


def _complete_section(model: Any, user: str, *, on_delta: Callable[[str], None] | None, cancel: Any,
                      profile: Any = None) -> str:
    from icg.infra.openai_model import SECTION_CALL, AuditIoLabel, call_with_profile
    profile = profile or SECTION_CALL

    if on_delta is not None and _model_streams(model):
        from icg.infra.model_fallback import call_model

        def guard(piece: str) -> None:
            _stop_if_cancelled(cancel)
            on_delta(piece)

        with AuditIoLabel("SECTION"):
            return call_model(
                model, SECTION_SYSTEM, user, on_delta=guard, cancel=cancel, profile=profile,
            ).text
    with AuditIoLabel("SECTION"):
        text = call_with_profile(model.suggest, SECTION_SYSTEM, user, profile=profile)
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
                  knowledge: str, *, path: str = "", neighbors: str = "",
                  running_summary: str = "") -> str:
    """五段多源隔离 Prompt。固定标签：项目级约束→本章任务→招标原文→知识库→生成规则，空块写（无）。

    与旧版差异：1. 前置「写作定位 + 全局项目事实」两段；2. 废标只注入 L0 全局技术约束（项目级约束）
    与本节关联 L1（本章硬约束），资格/商务/包装类废标不再全量灌入每节；3. 知识库内公司资料是唯一
    技术事实源，历史标书仅作写法参考；4. 缺事实强制 [待人工补充] 占位，禁止编造。
    """
    cover = _tender_rows(rows)
    graded = build_constraint_context(rows, workflow, task)
    ids = _requirement_ids(rows, task)
    points = _section_points(title, task, workflow)
    tender = _bullet_block(
        f"[{item.get('risk_level') or 'medium'}] {_shown_clause(item)}" for item in cover
    )
    evidence = knowledge.strip() if str(knowledge or "").strip() else CAPABILITY_GAP_LINE
    from icg.domain.technical_digest import scoring_criteria
    from icg.domain.technical_fact_sheet import prompt_fact_sheet_json

    fact_sheet = prompt_fact_sheet_json(workflow)
    fact_block = json.dumps(fact_sheet, ensure_ascii=False, indent=2) if fact_sheet else "（未固化，业主/工期/SLA 以本标要求为准）"

    location_body = "\n".join([
        f"当前章节路径：{path or title}",
        f"相邻章节边界（本节勿大段重复其内容）：{neighbors or '（无）'}",
        f"已生成前文关键承诺摘要：{running_summary or '（无）'}",
    ])
    task_body = "\n".join([
        f"标题：{title}",
        "要求编号：" + ("、".join(ids) if ids else "（无）"),
        "挂载要点：",
        _bullet_block(points),
        "评分标准：",
        _bullet_block(scoring_criteria(rows)),
        "本章硬约束：",
        _bullet_block(list(graded.section)),
    ])
    rules = (
        "不虚构能力、参数或资质。资料库查不到的具体工具名/参数/人数标 [待人工补充：说明]，禁止编造型号或指标。"
        "针对每个评分细则给出实质性落地举措（优先结构化表格），评分加分项在本节开篇亮出显性量化承诺。"
        "故障案例提炼为「典型故障场景→根因定位→标准化处置→预防措施」的应急预案，不得原样贴成流水账；"
        "非应急故障类章节不得引用故障案例。"
        "历史标书仅借结构与话术，严禁照抄旧客户名、旧工期、旧金额或旧型号。"
        "全局事实中的 current_year 是当前日期基准年份；排期、重保计划和培训计划不得使用早于 current_year 的年份，也不得照搬招标文件历史模板年份。"
        "评分对照表只许使用招标原文评分表和全局事实 scoring_rules 中明确给出的分值、区间与规则；严禁自行发明权重、计算系数、公式或加分条件。"
        "不得把废标写成已响应废标。正文不写偏离标签。"
    )
    blueprint = ((workflow or {}).get("writing_blueprints") or {}).get(str((task or {}).get("task_id") or ""), {})
    if not blueprint:
        blueprint = {}
    blueprint_body = ""
    if blueprint:
        hooks = "、".join(blueprint.get("scoring_hooks") or []) or "（无）"
        must = "；".join(blueprint.get("must_cover") or []) or "（无）"
        blueprint_body = "\n".join([
            "本节写作规划卡（必须执行）：",
            f"目标篇幅：约 {blueprint.get('target_words') or 1600} 字",
            f"评分钩子：{hooks}",
            f"必覆要点：{must}",
            f"表格要求：{blueprint.get('assigned_tables') or ''}",
            f"边界：{blueprint.get('forbidden_overlap') or ''}",
        ])
    parts = [
        "写作定位",
        location_body,
        "全局项目事实（全书唯一事实基准，本节口径必须与其一致）",
        fact_block,
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
    ]
    if blueprint_body:
        parts[2:2] = [blueprint_body]
    return "\n".join(parts)


def produce_section(title: str, row: dict, model: Any, *, knowledge: str = "",
                    task: dict | None = None, requirements: list[dict] | None = None,
                    workflow: dict | None = None, on_delta: Callable[[str], None] | None = None,
                    cancel: Any = None, foreign_names: list[str] | None = None,
                    path: str = "", neighbors: str = "", running_summary: str = "") -> str:
    rows = requirements or ([row] if row else [])
    primary = rows[0] if rows else (row or {})
    emitted = False
    if _section_writer is not None:
        text = _section_writer(title, primary)
    elif _local_model(model):
        user = _section_user(
            title, rows, task, workflow, knowledge,
            path=path, neighbors=neighbors, running_summary=running_summary,
        )
        weight = _section_weight(rows, task)
        profile = _section_profile(weight)
        text = _complete_section(model, user, on_delta=on_delta, cancel=cancel, profile=profile)
        emitted = on_delta is not None
        truncated = _unclosed_tail(text) or _finish_reason(model) == "length"
        if truncated and not _cancelled(cancel):
            base = _trim_broken_tail(text)
            continue_user = (
                "本节标题：" + title + "\n\n以下是被截断的正文末尾，请从这里接着写完：\n\n" + base[-600:]
            )
            try:
                extra = _complete_section(model, continue_user, on_delta=None, cancel=cancel, profile=profile)
                extra = strip_model_thinking(extra)
                if not str(extra or "").strip():
                    raise RuntimeError("empty continuation")
                text = _merge_continuation(base, extra)
            except Exception:
                text = _trim_unfinished_sentence(base)
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
            text = f"{text}\n\n[待人工补充：企业能力依据] 本节能力参数须人工核对，不得用招标原文代替。"
    if on_delta is not None and not emitted:
        _stop_if_cancelled(cancel)
        on_delta(text)
    text = scrub(str(text or ""), primary)
    if foreign_names:
        text = mask_foreign_names(text, foreign_names)
    text = strip_model_thinking(text)
    from icg.domain.export_sanitizer import strip_duplicate_title
    text = strip_duplicate_title(text, title)
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


def _top_key(heading: dict) -> str:
    """一级章归属键：编号首段（1.2.3 → 1）。无编号退回节键。"""
    number = str(heading.get("number") or "").strip()
    return number.split(".")[0] if number else _leaf_key(heading)


def _breadcrumb(heading: dict, outline: dict) -> str:
    """完整章节面包屑：按编号前缀逐级拼（如 第四章 售后服务方案 / 4.2 故障分级）。"""
    number = str(heading.get("number") or "").strip()
    if not number:
        return str(heading.get("title") or "")
    by_number = {str(h.get("number") or ""): h for h in outline.get("headings") or []}
    parts: list[str] = []
    segs = number.split(".")
    for index in range(1, len(segs) + 1):
        ancestor = by_number.get(".".join(segs[:index]))
        if ancestor:
            parts.append(f"{ancestor.get('number')} {ancestor.get('title')}".strip())
    return " / ".join(parts) if parts else str(heading.get("title") or "")


def _neighbors(heading: dict, leaves: list[dict]) -> str:
    """相邻叶子节标题，用于提示本节不要重复前后节已写内容。"""
    key = _leaf_key(heading)
    keys = [_leaf_key(item) for item in leaves]
    try:
        index = keys.index(key)
    except ValueError:
        return ""
    parts: list[str] = []
    if index > 0:
        parts.append(f"上节「{leaves[index - 1].get('title') or ''}」")
    if index < len(leaves) - 1:
        parts.append(f"下节「{leaves[index + 1].get('title') or ''}」")
    return "，".join(parts)


_COMMIT_LINE = re.compile(r"每|响应|SLA|承诺|巡检|备份|驻场|时限|到场|演练|备件|升级|恢复|切换|值守")
_RUNNING_SUMMARY_CAP = 150


# 摘要套话过滤：开篇过渡句不含事实要点，不得进 running_summary。
_SUMMARY_BOILERPLATE = re.compile(
    r"^(本项目旨在|本项目为|本项目面向|本节阐述|本节聚焦|针对本项目|针对本次|我司将|本项目需解决|本章|综上所述|为了更好地)"
)
# 事实要点行：含具体数字承诺或工具/机制/团队名词的行优先。
_SUMMARY_FACT_LINE = re.compile(r"\d|SLA|响应|巡检|备份|驻场|演练|恢复|切换|值守|工具|平台|机制|团队|分工|流程|演练")
_SUMMARY_STRIP_PREFIX = re.compile(r"^(本项目|我们|我司)(将|会|需|拟)?")


def _chapter_running_summary(group: list[dict], patches: dict[str, dict]) -> str:
    """一级章写完后提炼 ≤150 字的已承诺事实要点摘要，传给后续一级章保持全书口径一致。
    跳过开篇套话，优先含数字承诺/机制名词的紧凑事实行，跨节句级去重。"""
    bits: list[str] = []
    seen: set[str] = set()
    for heading in group:
        patch = patches.get(_leaf_key(heading)) or {}
        body = str(patch.get("body") or "")
        best = ""
        fallback = ""
        for line in body.splitlines():
            text = line.strip().lstrip("|-*#> ").strip()
            if len(text) < 8 or text.startswith(("|", "#", "（", "【")):
                continue
            if re.match(r"^\d+(\.\d+)*\s*\S{0,10}$", text):
                continue
            if not _COMMIT_LINE.search(text):
                continue
            if _SUMMARY_BOILERPLATE.match(text):
                continue
            # 截到句读，保留紧凑要点
            cut = re.split(r"[。；;]", text)[0].strip()
            if len(cut) < 8:
                continue
            if not fallback:
                fallback = cut
            if _SUMMARY_FACT_LINE.search(cut) and re.search(r"\d", cut):
                best = cut
                break
        pick = best or fallback
        if pick and pick not in seen:
            seen.add(pick)
            bits.append(pick[:46])
        if len(bits) >= 3:
            break
    return "；".join(bits)[:_RUNNING_SUMMARY_CAP]


def select_section(headings: list[dict], section: str) -> list[dict]:
    """section 先按节键（任务编号）匹配，同名小节不会被一起重写；匹配不到再按标题。"""
    by_key = [item for item in headings if _leaf_key(item) == section]
    return by_key or [item for item in headings if item.get("title") == section]


def preamble(content: str, outline: dict) -> str:
    """第一个目录标题之前的引言；正文里还没有目录标题时返回空串。"""
    first = next(iter(outline.get("headings") or []), None)
    if not first:
        return ""
    marker = f"{first.get('number')} {first.get('title')}"
    lines = (content or "").splitlines()
    index = next((i for i, line in enumerate(lines) if line.strip() == marker), None)
    return "\n".join(lines[:index]).strip() if index else ""


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
               company_id: str, emit: Callable[[dict], None] | None, cancel: Any,
               plan_ctx: dict | None = None) -> dict:
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
    ctx = plan_ctx or {}
    section_points = list((task or {}).get("response_points") or [])
    query = section_query(title, points=section_points)
    chunks, rag_audit = retrieve_for_section(
        knowledge_base, company_id, query, workflow,
        breadcrumb=ctx.get("path") or "", points=section_points, model=model,
        section_key=key,
    )
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
    if foreign_names and isinstance(workflow, dict):
        collected = workflow.setdefault("foreign_entity_names", [])
        for name in foreign_names:
            if name not in collected:
                collected.append(name)
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
            path=ctx.get("path") or "", neighbors=ctx.get("neighbors") or "",
            running_summary=ctx.get("running_summary") or "",
        )
    except ModelCancelled:
        if emit is not None:
            emit({"event": "section.cancelled", "section_id": key})
        return {"key": key, "title": title, "cancelled": True, "audit": rag_audit}
    except Exception:
        if emit is not None:
            emit({"event": "section.failed", "section_id": key, "message": "本节生成失败"})
        fallback = (
            f"[待人工补充：本节正文]「{title}」自动生成失败，请按下列要求人工补写。\n"
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
    on_event 收到节流事件。多节同时生成时，进行中的模型调用不超过章内并发上限（ICG_SECTION_CONCURRENCY，默认 2）。
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
    # 写作规划卡：全书叶子节一次生成，检索配额与写作指令都按卡执行
    blueprints = dict(workflow.get("writing_blueprints") or {})
    for item in headings:
        key = _leaf_key(item)
        if key in blueprints:
            continue
        item_task = tasks.get(item.get("task_id") or "") if item.get("task_id") else None
        item_rids = list(item.get("requirement_ids") or [])
        if not item_rids and item.get("requirement_id"):
            item_rids = [item["requirement_id"]]
        if isinstance(item_task, dict):
            item_rids = list(item_task.get("requirement_ids") or item_rids)
        item_rows = [rows[rid] for rid in item_rids if rid in rows]
        blueprints[key] = build_section_blueprint(item, item_rows, item_task, _section_weight(item_rows, item_task))
    workflow["writing_blueprints"] = blueprints
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
            "concurrency": _stream_concurrency(),
            "section_ids": [_leaf_key(item) for item in headings],
        })

    all_leaves = _leaves(outline)

    def draft(heading: dict, plan_ctx: dict | None = None) -> dict:
        listener = emit if on_event is not None else None
        return _draft_one(
            heading, rows, tasks, model, workflow, knowledge_base, company_id, listener, cancel,
            plan_ctx=plan_ctx,
        )

    # 一级章间串行 + 章内并发：每完成一个一级章提炼 running_summary 传给后续章节，保证全书口径一致
    groups: list[tuple[str, list[dict]]] = []
    for item in headings:
        top = _top_key(item)
        if groups and groups[-1][0] == top:
            groups[-1][1].append(item)
        else:
            groups.append((top, [item]))

    summaries = dict(workflow.get("chapter_summaries") or {})
    top_order = [top for top, _ in groups]
    stored_parts = [str(summaries.get(top) or "").strip() for top in sorted(summaries, key=lambda k: top_order.index(k) if k in top_order else 99)]

    def _summary_before(top: str) -> str:
        parts: list[str] = []
        for earlier_top, _ in groups:
            if earlier_top == top:
                break
            text = str(summaries.get(earlier_top) or "").strip()
            if text:
                parts.append(text)
        if not parts and stored_parts:
            parts = stored_parts
        return "；".join(parts)[:400]

    patches: list[dict] = []
    for top, group in groups:
        running_summary = _summary_before(top)
        def ctx_for(item: dict) -> dict:
            return {
                "path": _breadcrumb(item, outline),
                "neighbors": _neighbors(item, all_leaves),
                "running_summary": running_summary,
            }

        if on_event is not None and len(group) > 1:
            cap = min(_stream_concurrency(), len(group))
            with ThreadPoolExecutor(max_workers=cap) as pool:
                futures = {pool.submit(draft, item, ctx_for(item)): item for item in group}
                drafted: dict[str, dict] = {}
                for future in as_completed(futures):
                    patch = future.result()
                    drafted[patch["key"]] = patch
            group_patches = [drafted[_leaf_key(item)] for item in group]
        else:
            group_patches = [draft(item, ctx_for(item)) for item in group]
        patches.extend(group_patches)
        if not section:
            patch_map = {patch["key"]: patch for patch in group_patches}
            summary = _chapter_running_summary(group, patch_map)
            if summary:
                summaries[top] = summary
    if not section:
        workflow["chapter_summaries"] = summaries
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
    intro = preamble(current, outline)
    chapter.content = (f"{intro}\n\n" if intro else "") + _assemble(outline, bodies, reviews)
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
    from icg.domain.technical_verifier import verify_sections
    verified = verify_sections(workflow, check_sections)
    workflow["technical_verify"] = verified["summary"]
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
        warnings = verified["sections"].get(item["key"]) or []
        if warnings:
            task["verify_warnings"] = warnings
        elif "verify_warnings" in task:
            task.pop("verify_warnings", None)
    chapter.revision = int(getattr(chapter, "revision", 1) or 1) + 1
    if not failed and not section:
        workflow["needs_regeneration"] = [
            item for item in (workflow.get("needs_regeneration") or []) if item != chapter.id
        ]
    return {
        "task_ids": [item["task_id"] for item in headings if item.get("task_id")],
        "failed": failed,
        "chapter_id": chapter.id,
        "rag_audit": audits,
        "quality": quality,
        "constraint_check": workflow.get("constraint_check"),
    }


_CLAUSE_FRAGMENT_START = re.compile(
    r"^(?:[a-z]{1,4}(?=[\u4e00-\u9fff])|件|为|在|但仍|仅|才能|月|标活动|息中心|质量以|服务中|保障|协商|升级|做相应|加\d)"
)
_CLAUSE_FRAGMENT_END = re.compile(r"(?:\*|内|中|的|、|，|：|;|；)$")
_TOKEN = re.compile(r"[A-Za-z0-9]+|[\u4e00-\u9fff]{2,}")
_TOKEN_STOP = {
    "项目", "服务", "要求", "招标", "投标", "文件", "内容", "提供", "进行", "相关", "本方", "甲方", "乙方",
    "昆明", "航空", "有限公司", "数据库", "一体机",
}


def _plain_text(text: str) -> str:
    from icg.domain.export_sanitizer import normalize_markdown_noise, strip_internal_markers
    out = strip_internal_markers(normalize_markdown_noise(str(text or "")))
    out = out.replace("<br>", " ").replace("\t", " ")
    out = re.sub(r"[`_]+", "", out)
    out = re.sub(r"\s+", " ", out)
    return out.strip()


def _bigrams(text: str) -> set[str]:
    compact = re.sub(r"\s+", "", str(text or ""))
    return {compact[index:index + 2] for index in range(len(compact) - 1)}


def _overlap(query: str, candidate: str) -> float:
    left = _bigrams(query)
    right = _bigrams(candidate)
    if not left or not right:
        return 0.0
    return len(left & right) / min(len(left), len(right))


def _sentence_parts(text: str) -> list[str]:
    raw = re.split(r"(?<=[。；;])|\n", str(text or ""))
    return [part.strip() for part in raw if part.strip()]


def _strip_list_prefix(text: str) -> str:
    out = str(text or "").strip()
    out = re.sub(r"^[\s>\-+•●]+", "", out)
    out = re.sub(r"^\|?", "", out).strip()
    out = re.sub(r"^\d+(?:\.\d+)+\s*", "", out)
    out = re.sub(r"^(?:\(?\d+\)?[、.．]|[一二三四五六七八九十]+[、.．]|\([一二三四五六七八九十]+\))\s*", "", out)
    return out.strip()


def _fragmentary_clause(text: str) -> bool:
    value = str(text or "").strip()
    if not value:
        return True
    if len(value) <= 8:
        return True
    return bool(_CLAUSE_FRAGMENT_START.search(value) or _CLAUSE_FRAGMENT_END.search(value))


def complete_clause_text(row: dict) -> str:
    """偏离表条款列的完整句修复：模型抽取有时只保留半句/词片，优先回溯 source.quote
    中与该片段最匹配的完整句子；取不到原文时不编造，保留原片段。"""
    text = _plain_text(row.get("extracted_summary") or row.get("text") or "")
    quote = _plain_text((row.get("source") or {}).get("quote") or "")
    if not quote:
        return text
    candidates = []
    for part in _sentence_parts(quote):
        cleaned = _strip_list_prefix(_plain_text(part.replace("|", " ")))
        if len(cleaned) >= 6 and cleaned not in candidates:
            candidates.append(cleaned)
    if not candidates:
        return text or quote[:200]
    probes = [text]
    if len(text) >= 6:
        probes.extend([text[-10:], text[-6:]])
    best = ""
    best_score = -1.0
    for candidate in candidates:
        score = _overlap(text, candidate)
        for probe in probes[1:]:
            if probe and probe in candidate:
                score += 0.35
        if text and text in candidate:
            score += 0.5
        if score > best_score:
            best, best_score = candidate, score
    if _fragmentary_clause(text) and best:
        return best[:200]
    if text and len(text) >= 12 and best_score < 0.18:
        return text[:200]
    return (best or text or quote)[:200]


def _query_tokens(text: str) -> set[str]:
    tokens = set()
    for token in _TOKEN.findall(str(text or "")):
        token = token.strip().lower()
        if len(token) < 2 or token in _TOKEN_STOP:
            continue
        tokens.add(token)
    return tokens


def _response_units(body: str) -> list[dict]:
    """正文候选单元。text 用于匹配，response 用于填表；表格行优先取动作/指标列，
    不把「故障场景」误拼成“我司数据库实例崩溃”这种病句。"""
    units: list[dict] = []
    raw_lines = (body or "").splitlines()
    for line_index, raw in enumerate(raw_lines):
        line = raw.strip()
        if not line or line.startswith(("#", "---")) or re.match(r"^\d+(?:\.\d+)*\s+\S{1,30}$", line):
            continue
        if line.startswith("|") and line.endswith("|") and not re.match(r"^\|?\s*:?-{2,}", line):
            # 下一行是 Markdown 表格分隔线时，本行是表头，不得当作响应句。
            next_line = raw_lines[line_index + 1].strip() if line_index + 1 < len(raw_lines) else ""
            if re.match(r"^\|?\s*:?-{2,}", next_line):
                continue
            cells = [_strip_list_prefix(_plain_text(cell)) for cell in line.strip("|").split("|")]
            cells = [cell for cell in cells if cell and set(cell) != {"-"} and "待人工补充" not in cell]
            headerish = sum(1 for cell in cells if cell in {"故障场景", "响应动作", "恢复目标", "服务内容", "服务要求", "依据来源", "交付物", "评分项", "分值"})
            if len(cells) >= 2 and headerish < 2:
                text = "；".join(cells)
                if len(cells) >= 3 and len(cells[0]) <= 42 and re.search(r"故障|异常|场景|崩溃|宕机|旺季|无法|不可", cells[0]):
                    scenario = cells[0] if cells[0].endswith("场景") else cells[0] + "场景"
                    response = f"针对{scenario}，" + "；".join(cells[2:] or cells[1:])
                else:
                    response = "；".join(cells[1:] if len(cells) >= 3 and len(cells[0]) <= 18 else cells)
                units.append({"text": text, "response": response})
            continue
        line = _strip_list_prefix(line)
        for part in _sentence_parts(line):
            text = _strip_list_prefix(part)
            # 冒号结尾只是引导句，响应列不能截成“……：。”。
            if len(text) >= 10 and not text.startswith(("（", "【")) and not text.rstrip("。；; ").endswith(("：", ":")):
                units.append({"text": text, "response": text})
    return units

_ANCHOR_PATTERN = re.compile(
    r"一级故障|二级故障|三级故障|巡检|热线|电话|硬件更换|故障硬件|赔偿|人为|驻场|重保|授权函|保密|咨询|每月|季度|40分钟|2小时|15分钟|24小时|DBA|Exadata"
)


def _anchors(text: str) -> set[str]:
    found = set(_ANCHOR_PATTERN.findall(text or ""))
    # 表格定级列常只写“二级/三级”，语义上等同于“二级故障/三级故障”。
    blob = str(text or "")
    for level in ("一级故障", "二级故障", "三级故障"):
        short = level.replace("故障", "")
        if level in found or short in blob:
            found.add(level)
    return found


def _anchor_mismatch(clause: str, candidate: str) -> bool:
    """关键锚点冲突时宁可走条款兜底，也不能把二级违约答成一级违约。"""
    q = _anchors(clause)
    if not q:
        return False
    c = _anchors(candidate)
    for level in ("一级故障", "二级故障", "三级故障"):
        if level in q and level not in c and any(other in c for other in ("一级故障", "二级故障", "三级故障")):
            return True
    strong = {"巡检", "热线", "授权函"}
    if q & strong and not (q & strong & c):
        return True
    # 故障硬件/硬件更换是组合语义：正文常写“硬件故障更换”“备件调度与现场更换”，
    # 不能要求与条款字面完全同序。
    if ("硬件更换" in clause or "故障硬件" in clause) and not (("硬件" in candidate or "部件" in candidate or "备件" in candidate) and "更换" in candidate):
        return True
    # 违约/赔偿与巡检频次是语义锚点，不能被“非人为硬件更换”或错误频次蒙混。
    if "赔偿" in clause and "赔偿" not in candidate:
        return True
    if "违约金" in clause and "违约金" not in candidate and "赔偿" not in candidate:
        return True
    if "人为" in clause and ("人为" not in candidate or "非人为" in candidate):
        return True
    if ("热线" in clause or "电话" in clause) and not ("热线" in candidate or "电话" in candidate or "回电" in candidate):
        return True
    if ("热线" in clause or "电话" in clause) and re.search(r"(?:7\s*[×*xX]\s*24|每周\s*7\s*天|每天\s*24\s*小时|24\s*小时电话)", clause) and not re.search(r"(?:7\s*[×*xX]\s*24|7\s*天.*24\s*小时|24\s*小时.*热线|全天候|热线支持)", candidate):
        return True
    if "咨询" in clause and not re.search(r"咨询|顾问|优化建议|管理建议|改进建议", candidate):
        return True
    if "每季度" in clause and "每季度" not in candidate and "季度" not in candidate:
        return True
    if "每月" in clause and "每月" not in candidate:
        return True
    return False


def _match_response_unit(clause: str, units: list[str]) -> str:
    q_tokens = _query_tokens(clause)
    q_numbers = set(re.findall(r"\d+(?:\.\d+)?", clause))
    best = ""
    best_score = 0.0
    for unit in units:
        plain = _plain_text(unit.get("text") or "")
        if len(plain) < 10 or _anchor_mismatch(clause, plain):
            continue
        score = _overlap(clause, plain)
        c_tokens = _query_tokens(plain)
        if q_tokens and c_tokens:
            common = q_tokens & c_tokens
            score += min(0.32, 0.08 * len(common))
            if any(len(token) >= 3 for token in common):
                score += 0.08
        c_numbers = set(re.findall(r"\d+(?:\.\d+)?", plain))
        if q_numbers and q_numbers & c_numbers:
            score += 0.12
        # 关键责任动词比“涵盖/覆盖”类总述更能证明精准响应。
        for phrase in ("免费更换", "热线支持", "季度巡检", "授权函", "直接经济损失"):
            if phrase in clause and phrase in plain:
                score += 0.45
        if "免费更换" in clause and "免费更换" not in plain and re.search(r"涵盖|覆盖|包括", plain):
            score -= 0.35
        if re.search(r"\d|SLA|响应|巡检|驻场|到场|恢复|演练|机制|团队|交付|报告", plain):
            score += 0.04
        # 条款已明确故障等级时，混入其他等级的“总起句”不能压倒表格里的单级精准响应。
        q_levels = {level for level in ("一级故障", "二级故障", "三级故障") if level in clause}
        if q_levels:
            other_levels = [level for level in ("一级故障", "二级故障", "三级故障") if level not in q_levels and level in plain]
            score -= 0.22 * len(other_levels)
        if plain.startswith(("本项目针对", "本节", "综上")):
            score -= 0.08
        if score > best_score:
            best, best_score = str(unit.get("response") or plain), score
    return best if best_score >= 0.16 else ""


def _truncate_complete_sentence(text: str, limit: int = 160) -> str:
    """按完整句号/分号边界截断；宁可略长，也不能在词语、编号或引号中间切断。"""
    value = str(text or "")
    if len(value) <= limit:
        return value
    enders = [match.end() for match in re.finditer(r"[。；;！？]", value)]
    inside = [end for end in enders if end <= limit]
    if inside:
        return value[:inside[-1]]
    after = [end for end in enders if end <= limit + 80]
    if after:
        return value[:after[0]]
    return value


def _shape_response_sentence(text: str, clause: str) -> str:
    picked = _strip_list_prefix(_plain_text(text))
    picked = re.sub(r"^(?:特别说明|注|承诺事实声明|项目事实唯一性确认)[:：]?", "", picked).strip()
    if len(picked) > 160:
        picked = _truncate_complete_sentence(picked, 160).strip()
    if not picked:
        return ""
    if picked.startswith("本项目"):
        picked = "我司" + picked[3:]
    elif picked.startswith("本方案"):
        picked = "我司方案" + picked[3:]
    elif not picked.startswith(("我司", "我们", "我公司")):
        if re.match(r"^\d+\s*(?:分钟|小时|天|日)", picked):
            picked = "我司在" + picked
        elif re.match(r"^(?:文件|系统|合同|项目过程|服务过程|纸质|电子)", picked):
            picked = "我司在" + picked
        elif "→" in picked and not picked.startswith(("我司按", "按")):
            picked = "我司按“" + picked.rstrip("。；; ") + "”流程执行"
        else:
            picked = "我司" + picked
    picked = re.sub(r"^我司(一|二|三|四|五|六|七|八|九|十)+[、.．]", "我司", picked)
    if picked.endswith(("；", ";")):
        picked = picked[:-1] + "。"
    elif not picked.endswith(("。", "！", "？")):
        picked += "。"
    return picked


def _fallback_clause_response(clause: str) -> str:
    raw_short = _strip_list_prefix(clause)
    short = raw_short[:58].rstrip("，。；; ")
    if len(raw_short) > 58:
        short += "等要求"
    if not short:
        short = "对应招标条款"
    return f"我司已针对“{short}”制定专项响应措施，明确执行流程、责任分工、时限要求与交付记录，详见对应章节正文。"


def _content_response_detail(content: str, heading: dict, row: dict) -> tuple[str, str]:
    """返回（响应, matched/fallback/unavailable），供兜底池只收集真正未命中的条款。"""
    if not content:
        return "待生成后回填", "unavailable"
    body = section_body(content, str(heading.get("number") or ""), str(heading.get("title") or ""))
    if not body.strip() or body.strip() == "待补":
        return "待生成后回填", "unavailable"
    clause = complete_clause_text(row)
    picked = _match_response_unit(clause, _response_units(body))
    if not picked:
        # 目录挂载偶发偏节时，先在整章正文找同一事实句；找不到再走条款兜底，避免错配成无关SLA。
        picked = _match_response_unit(clause, _response_units(content))
    if not picked:
        return _fallback_clause_response(clause), "fallback"
    shaped = _shape_response_sentence(picked, clause)
    if shaped:
        return shaped, "matched"
    return _fallback_clause_response(clause), "fallback"


def _content_response(content: str, heading: dict, row: dict) -> str:
    """响应列按“单条条款→本节正文最匹配句/表格行”精准提炼。"""
    return _content_response_detail(content, heading, row)[0]

def _cell(header: str, heading: dict, row: dict, sample: dict, *, content: str = "", response_map: dict[str, str] | None = None) -> str:
    if sample.get("scope") == "technical" and "商务" in header and "技术" not in header:
        return ""
    if "页码" in header or ("章节" in header and ("号" in header or "对应" in header)):
        # 偏离表页码/章节列都指向本标章节号（排版后页码由人工填），
        # 招标文件 source.page 只留在内部响应追溯表，不进偏离表。
        number = str(heading.get("number") or "").strip()
        if not number:
            return ""
        return f"详见第 {number} 节" if "章节" in header else f"详见第 {number} 节（排版后填页码）"
    if "条款" in header or "要求" in header or "规格" in header:
        # 样表条款列常写成「招标文件项目详细需求偏离说明表条款的序号及内容」，
        # 必须先按条款列填充，不能被其中“偏离”两字带偏到偏离列。
        return complete_clause_text(row)
    if "偏离说明" in header:
        # 五列样表只有合并的「偏离说明」列，不能只写原因而省掉偏离结论；
        # 否则评委看到的是空偏离列。核心项资料不足仍严禁负偏离。
        label = "无偏离" if ((row.get("response_type") or "comply") == "comply" or (critical(row) and row.get("response_type") == "deviate")) else TABLE_LABEL.get(row.get("response_type") or "", "")
        reason = str(row.get("deviation_reason") or "").strip()
        if critical(row) and row.get("response_type") == "deviate":
            return "无偏离（资料缺口，须人工确认）"
        return label + (f"：{reason}" if reason and label != "无偏离" else "")
    if "说明" in header or "理由" in header:
        if critical(row) and row.get("response_type") == "deviate":
            return "资料缺口，按无偏离填报，须人工确认。"
        if row.get("response_type") == "comply":
            return ""
        return str(row.get("deviation_reason") or "")
    if "偏离" in header:
        # 核心实质性条款严禁负偏离：资料不足默认无偏离并附人工确认标记（说明列）
        if critical(row) and row.get("response_type") == "deviate":
            return "无偏离"
        return TABLE_LABEL.get(row.get("response_type") or "comply", "无偏离")
    if "响应" in header or "投标" in header:
        rid = str(row.get("id") or "")
        if response_map and rid in response_map:
            return response_map[rid]
        return _content_response(content, heading, row)
    if "序号" in header:
        return str(heading.get("_table_ordinal") or heading.get("number") or "")
    return str(heading.get("title") or "")


def _deviation_clause_key(text: str) -> str:
    value = re.sub(r"\s+", "", text or "")
    value = re.sub(r"[，。；;：:、（）()\[\]【】“”\"']", "", value)
    value = re.sub(r"^(?:\d+(?:\.\d+)*|[一二三四五六七八九十]+)[、.．]?", "", value)
    return value


def _is_deviation_ineligible(row: dict, clause: str) -> bool:
    """偏离表只保留可响应的投标服务条款；招标人义务、过渡句、评分低分档不构成响应行。"""
    text = clause.strip()
    if not text:
        return True
    if re.search(r"(?:招标人|招标方|甲方|业主)(?:不得|应当|须|应)", text):
        return True
    if re.search(r"(?:如下表|如下)[:：]?$", text) or text in {"项目建设目标将覆盖以下服务范围：", "目前公司使用数据库整体情况如下表："}:
        return True
    if re.search(r"加\s*(?:0-10|10-20|5)\s*分", text):
        return True
    # 评分表表名、公式与档位碎片不是可响应技术条款；付款协定属于商务条款。
    if re.search(r"\bF[123]\b|×\s*A[123]|方案服务得分|商务资质得分", text):
        return True
    if re.match(r"^\d*[、.．]?\s*(?:方案服务评分表|方案服务评分对照表|商务资质评分表)\s*$", text):
        return True
    if re.search(r"含[)）]?[-—~][\d.]+\s*次.*加\s*\d+(?:-\d+)?\s*分", text):
        return True
    if re.search(r"支付情况|支付乙方服务费|付款", text):
        return True
    return False


def _deviation_entries(sample: dict, workflow: dict) -> list[tuple[dict, dict, str]]:
    """偏离表候选条款：统一完成程序条款、不可响应行、状态与标准化条款去重。"""
    outline = workflow.get("technical_outline") or {}
    rows = {row.get("id"): row for row in _clauses(workflow)}
    emitted: set[str] = set()
    emitted_clauses: set[str] = set()
    entries: list[tuple[dict, dict, str]] = []
    from icg.domain.technical_constraint_context import row_is_non_tech
    from icg.domain.technical_clause_cleaning import row_excluded_from_technical
    for heading in _leaves(outline):
        requirement_ids = list(heading.get("requirement_ids") or [])
        if not requirement_ids and heading.get("requirement_id"):
            requirement_ids = [heading.get("requirement_id")]
        for rid in requirement_ids:
            row = rows.get(rid)
            if row is None or row.get("status") == "rejected" or str(rid) in emitted:
                continue
            clause_text = complete_clause_text(row)
            if sample.get("scope") == "technical" and (row_is_non_tech(row) or row_excluded_from_technical(row)):
                continue
            if sample.get("scope") == "technical" and _is_deviation_ineligible(row, clause_text):
                continue
            if sample.get("mode") == "deviations" and not critical(row) and row.get("response_type") not in ("exceed", "deviate"):
                continue
            clause_key = _deviation_clause_key(clause_text)
            if sample.get("scope") == "technical" and clause_key and clause_key in emitted_clauses:
                continue
            emitted.add(str(rid))
            if clause_key:
                emitted_clauses.add(clause_key)
            entries.append((heading, row, clause_text))
    return entries


def table_rows(sample: dict, workflow: dict, *, content: str = "", model: Any = None) -> list[list[str]]:
    from icg.domain.writing_knowledge_prompt import mask_foreign_names
    entries = _deviation_entries(sample, workflow)
    foreign = list(workflow.get("foreign_entity_names") or [])

    # 先跑确定性主干。只有落入通用兜底模板的条款进入 LLM 兜底池，高置信度命中不重复调用模型。
    deterministic: dict[str, str] = {}
    fallback_pool: list[dict] = []
    for heading, row, clause_text in entries:
        rid = str(row.get("id") or "")
        response, source = _content_response_detail(content, heading, row)
        deterministic[rid] = response
        if source == "fallback":
            fallback_pool.append({
                "id": rid,
                "clause": clause_text,
                "section_key": _leaf_key(heading),
                "section_number": str(heading.get("number") or ""),
                "section_title": str(heading.get("title") or ""),
                "body": section_body(content, str(heading.get("number") or ""), str(heading.get("title") or "")),
            })

    llm_responses: dict[str, str] = {}
    if fallback_pool and model is not None:
        from icg.domain.technical_deviation_llm import refine_deviation_fallbacks
        llm_responses, audit = refine_deviation_fallbacks(
            model, workflow, content, fallback_pool, max_workers=_stream_concurrency(),
        )
        workflow["technical_deviation_llm_audit"] = audit
    response_map = {**deterministic, **llm_responses}

    filled = []
    for heading, row, _clause_text in entries:
        row_heading = {**heading, "_table_ordinal": len(filled) + 1}
        cells = [
            _cell(header, row_heading, row, sample, content=content, response_map=response_map).replace("|", "／").replace("\n", " ")
            for header in sample["headers"]
        ]
        if foreign:
            cells = [mask_foreign_names(cell, foreign) for cell in cells]
        filled.append(cells)
    return filled


def markdown_table(sample: dict, workflow: dict, *, content: str = "", model: Any = None) -> str:
    headers = sample["headers"]
    lines = [
        f"## {sample['title']}",
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in table_rows(sample, workflow, content=content, model=model):
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


def export_parts(workflow: dict, title: str, content: str, *, model: Any = None) -> dict:
    """偏离表只在导出时按当时矩阵与最终正文填写，不写回服务方案正文。

    无论招标书是否抽出样表，都稳定产出独立《技术偏离表.docx》；未抽到样表时使用
    标准 5 列兜底模板。样表若为正文内嵌格式，仍同时附在正文末尾。
    """
    samples = find_samples(workflow)
    inline = [sample for sample in samples if not sample["attachment"]]
    attached = [sample for sample in samples if sample["attachment"]]
    if not attached:
        attached = [dict(FALLBACK_DEVIATION_SAMPLE)]
    from icg.domain.export_sanitizer import inject_scoring_scorecard, sanitize_markdown
    from icg.domain.technical_fact_sheet import prompt_fact_sheet_json
    markdown = chapter_markdown(title, content)
    fact_prompt = prompt_fact_sheet_json(workflow)
    markdown = inject_scoring_scorecard(markdown, fact_prompt.get("scoring_rules"))
    if inline:
        markdown += "\n\n" + "\n\n".join(markdown_table(sample, workflow, content=content, model=model) for sample in inline)
    attachment = "\n\n".join(markdown_table(sample, workflow, content=content, model=model) for sample in attached)
    return {
        "markdown": sanitize_markdown(markdown),
        "attachment": sanitize_markdown(attachment),
        "note": "" if samples else NO_SAMPLE + "已按标准五列模板导出。",
    }
