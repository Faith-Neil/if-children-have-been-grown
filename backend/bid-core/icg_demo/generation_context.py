# 为什么有这个文件：把整章写作实际使用的条款、证据和已确认事实集中组装，并保存来源快照。
# 它解决什么问题：生成与改写不能使用不同输入、模板默认承诺或未核对资料；模型不能悄悄删除变量或修改事实来源。

from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from .domain import DomainError, iso_time
from .input_snapshot import project_input_fingerprint
from .sla import TOKEN as SLA_TOKEN, UNIT_ALIASES, public_sla, resolve_variables, sla_facts, sla_issues, unit_code

FACT_TOKEN = re.compile(r"\{\{fact:([A-Za-z0-9_.:-]+)\}\}")
FACT_UNIT_ALIASES = {**UNIT_ALIASES, "个月": "month"}
FACT_UNIT_PATTERN = "|".join(re.escape(item) for item in sorted(
    (*FACT_UNIT_ALIASES, *FACT_UNIT_ALIASES.values()), key=len, reverse=True))
FACT_UNIT_SUFFIX = re.compile(r"\s*(" + FACT_UNIT_PATTERN + r")(?![A-Za-z_])")
FACT_NUMBER_UNIT = re.compile(r"[+-]?(?:\d+(?:\.\d+)?|\.\d+)\s*(" + FACT_UNIT_PATTERN + r")")
SHANGHAI = timezone(timedelta(hours=8))


def project_facts(state, project_id):
    workflow = state.workflows.get(project_id, {})
    facts = [{"unit": "", "required": False, "source_type": "parsed", "sla_var_key": None, **fact}
             for fact in workflow.get("facts", {}).values()] + sla_facts(state, project_id)
    return [{**fact, "label": fact["key"], "variable_token":
             "{{sla:" + fact["sla_var_key"] + "}}" if fact.get("sla_var_key") else "{{fact:" + fact["id"] + "}}"}
            for fact in facts]


def chapter_plan(workflow, chapter_id):
    saved = workflow.get("writing_plan", {}).get("chapters", {}).get(chapter_id, {})
    return {"id": chapter_id, "fact_ids": list(saved.get("fact_ids", [])),
            "writing_points": saved.get("writing_points", ""), "target_length": saved.get("target_length"),
            "confirmed_by": saved.get("confirmed_by"), "confirmed_by_name": saved.get("confirmed_by_name"),
            "confirmed_at": saved.get("confirmed_at"), "confirmed_input_fingerprint": saved.get("confirmed_input_fingerprint")}


def writing_source_fingerprint(state, project_id, chapter_id=None):
    """方案只绑定来源和写作配置；提交正文不会要求再次确认相同方案。"""
    workflow = state.workflows.get(project_id, {})
    project = state.projects[project_id]
    if chapter_id is None:
        chapters = [c.id for c in state.chapters.values() if c.project_id == project_id]
        return hashlib.sha256(json.dumps([writing_source_fingerprint(state, project_id, identity)
                                         for identity in sorted(chapters)]).encode()).hexdigest()
    chapter = state.chapters[chapter_id]
    plan = chapter_plan(workflow, chapter_id)
    facts = [f for f in project_facts(state, project_id) if f["required"] or f["id"] in plan["fact_ids"]]
    requirements = [r for r in workflow.get("requirements", {}).values() if r["chapter_id"] == chapter_id]
    evidence_ids = {identity for r in requirements for identity in r["evidence_ids"]}
    file_ids = {r["source"]["file_id"] for r in requirements if r.get("source")}
    file_ids.update(f["source"]["file_id"] for f in facts if f.get("source") and f["source"].get("file_id"))
    from .project_access import chapter_edit, writable
    team = state.project_teams.get(project_id, {})
    payload = {
        "project": {"name": project.name, "tender_number": project.tender_number,
                    "deadline": project.deadline, "sensitive": project.sensitive},
        "files": [{k: v for k, v in item.items() if k not in ("content", "pages")}
                  for identity, item in workflow.get("files", {}).items() if identity in file_ids],
        "requirements": requirements,
        "facts": facts,
        "conflicts": [item for item in workflow.get("conflicts", {}).values()
                      if set(item["fact_ids"]) & {f["id"] for f in facts}],
        "sla": workflow.get("sla"),
        "library": [item for identity, item in state.library.items() if identity in evidence_ids],
        "sla_templates": [item for item in state.sla_templates.values()
                          if item["company_id"] == project.company_id and workflow.get("sla")
                          and item["id"] == workflow["sla"]["template_id"]],
        "chapter": {"id": chapter_id, "title": chapter.title, "volume": chapter.volume,
                    "assignee_id": chapter.assignee_id, "owner_id": team.get("owners", {}).get(chapter.volume),
                    "owner_is_writable": writable(state, project_id, team.get("owners", {}).get(chapter.volume))},
        "plan": {k: plan[k] for k in ("fact_ids", "writing_points", "target_length")},
        "confirmer_can_edit": chapter_edit(state, chapter, plan["confirmed_by"]) if plan["confirmed_by"] else False,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def plan_is_current(state, project_id, chapter_id=None):
    workflow = state.workflows.get(project_id, {})
    if chapter_id is None:
        chapters = [c for c in state.chapters.values() if c.project_id == project_id]
        return bool(chapters and all(plan_is_current(state, project_id, c.id) for c in chapters))
    plan = chapter_plan(workflow, chapter_id)
    return bool(plan["confirmed_at"] and not workflow.get("writing_plan", {}).get("chapters", {}).get(chapter_id, {}).get("confirmation_pending")
                and plan["confirmed_input_fingerprint"]
                == writing_source_fingerprint(state, project_id, chapter_id))


def public_plan(workflow, state=None, project_id=None):
    plan = workflow.get("writing_plan", {})
    return {"confirmed_by": plan.get("confirmed_by"), "confirmed_at": plan.get("confirmed_at"),
            "confirmed_by_name": plan.get("confirmed_by_name"),
            "chapters": [{**deepcopy(value), "is_current": plan_is_current(state, project_id, identity) if state else False}
                         for identity, value in plan.get("chapters", {}).items()]}


def _source(workflow, source):
    if source is None:
        return None
    record = workflow.get("files", {}).get(source.get("file_id"))
    return {**deepcopy(source), **({"filename": record["filename"], "sha256": record["sha256"],
                                  "pagination": record["pagination"]} if record else {})}


def _source_valid(workflow, source):
    if source is None:
        return True  # 手工事实可以没有招标原文；不会伪造页码。
    record = workflow.get("files", {}).get(source.get("file_id"))
    page = source.get("page")
    return bool(record and record["status"] == "parsed" and isinstance(page, int) and not isinstance(page, bool)
                and 1 <= page <= len(record.get("pages", []))
                and source.get("quote") and source["quote"] in record["pages"][page - 1])


def _date(value):
    try:
        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=SHANGHAI)
        return moment.astimezone(SHANGHAI).date()
    except (ValueError, TypeError) as error:
        raise DomainError(422, "INVALID_DATE", "资料有效期和项目截止时间格式无效，请先核对来源。") from error


def build_generation_context(state, project_id, chapter, now):
    """返回供前端查看的清单和阻断项；只有 ready 时才允许发给模型。"""
    workflow = state.workflows.get(project_id, {})
    project = state.projects[project_id]
    plan = chapter_plan(workflow, chapter.id)
    confirmed = plan
    issues = []
    def add(code, message, **details):
        issues.append({"code": code, "message": message, **details})
    if not workflow.get("parse_confirmed"):
        add("PARSE_NOT_CONFIRMED", "请先确认解析结果。")
    if not plan_is_current(state, project_id, chapter.id):
        add("PLAN_STALE" if confirmed.get("confirmed_at") else "PLAN_NOT_CONFIRMED",
            "本章方案尚未确认或来源已经变化，请由有本章权限的编写人或负责人重新确认方案。")
    from .project_access import writable
    if not writable(state, project_id, state.project_teams.get(project_id, {}).get("owners", {}).get(chapter.volume)):
        add("VOLUME_OWNER_REQUIRED", "本册尚未指定负责人，不能确认或生成写作方案。")
    for issue in sla_issues(state, project_id):
        add(issue["code"], issue["message"])
    selected = set(plan["fact_ids"])
    facts, omitted = [], []
    all_facts = project_facts(state, project_id)
    known_ids = {item["id"] for item in all_facts}
    for identity in selected - known_ids:
        add("FACT_NOT_FOUND", "方案引用的事实不属于本项目或已经删除。", fact_id=identity)
    for fact in all_facts:
        used = fact["required"] or fact["id"] in selected
        usable = fact["status"] == "confirmed" and _source_valid(workflow, fact.get("source"))
        if not used or not usable:
            reason = ("本章未选择此可选事实" if not used else "事实尚未确认" if fact["status"] != "confirmed" else "事实来源已失效")
            omitted.append({"kind": "fact", "id": fact["id"], "label": fact["key"], "reason": reason})
            if used:
                add("FACT_NOT_READY", fact["key"] + "：" + reason, fact_id=fact["id"])
            continue
        variable = "{{sla:" + fact["sla_var_key"] + "}}" if fact.get("sla_var_key") else "{{fact:" + fact["id"] + "}}"
        facts.append({**deepcopy(fact), "variable": variable, "source": _source(workflow, fact.get("source"))})
    requirements, evidence_by_id = [], {}
    reference_date = _date(project.deadline) if project.deadline else datetime.fromtimestamp(now, SHANGHAI).date()
    for row in workflow.get("requirements", {}).values():
        if row["chapter_id"] != chapter.id or row["status"] == "rejected":
            continue
        if row["status"] != "confirmed" or row["volume"] != chapter.volume or not _source_valid(workflow, row.get("source")):
            add("REQUIREMENT_NOT_READY", "本章条款尚未确认、分册不匹配或原文来源无效。", requirement_id=row["id"])
            continue
        requirements.append({"id": row["id"], "text": row["text"], "response": row["response"],
                             "status": row["status"], "source": _source(workflow, row["source"]),
                             "evidence_ids": list(row["evidence_ids"])})
        for identity in row["evidence_ids"]:
            evidence = state.library.get(identity)
            if (evidence is None or evidence["company_id"] != project.company_id
                    or evidence["status"] != "confirmed" or evidence["type"] == "history"
                    or evidence.get("project_id") not in (None, project_id)):
                add("EVIDENCE_NOT_USABLE", "本章引用证据不存在、未确认或不属于本公司/本项目。", evidence_id=identity)
                continue
            if evidence.get("valid_until") and _date(evidence["valid_until"]) < reference_date:
                add("EVIDENCE_EXPIRED", "本章证据有效期不能覆盖投标截止时间。", evidence_id=identity)
                continue
            item = evidence_by_id.setdefault(identity, {k: deepcopy(evidence.get(k)) for k in
                        ("id", "name", "revision", "type", "valid_until", "status", "content")})
            item.setdefault("requirement_ids", []).append(row["id"])
    for index, fact in enumerate(facts):
        if any(other["key"] == fact["key"] and (other["value"], other["unit"]) != (fact["value"], fact["unit"])
               for other in facts[:index]):
            add("FACT_CONFLICT", "本章同名事实存在不同取值或单位，请到事实表处理。", fact_id=fact["id"])
    snapshot = {"scope": "whole_chapter", "created_at": iso_time(now),
                "input_fingerprint": project_input_fingerprint(state, project_id),
                "project": {"id": project.id, "name": project.name},
                "chapter": {"id": chapter.id, "title": chapter.title, "volume": chapter.volume,
                            "base_revision": chapter.revision},
                "plan": {**plan, "is_current": plan_is_current(state, project_id, chapter.id), "confirmed_by": confirmed.get("confirmed_by"), "confirmed_at": confirmed.get("confirmed_at"),
                         "confirmed_by_name": confirmed.get("confirmed_by_name")},
                "requirements": requirements, "evidence": list(evidence_by_id.values()), "facts": facts,
                "omitted_inputs": omitted, "official_content": chapter.content}
    return {"source_scope": "whole_chapter", "input_snapshot": snapshot, "ready": not issues, "issues": issues}


def require_ready(context):
    if not context["ready"]:
        first = context["issues"][0]
        raise DomainError(409, first["code"], first["message"], {"issues": context["issues"]})


def render_model_input(snapshot):
    lines = [snapshot["chapter"]["title"], "本内容为待人工核对候选，不能自动成为正式承诺。",
             "项目：" + snapshot["project"]["name"],
             "写作要点：" + (snapshot["plan"]["writing_points"] or "未补充"),
             "字数目标（人工参考）：" + str(snapshot["plan"]["target_length"] or "未指定")]
    for row in snapshot["requirements"]:
        lines += ["招标要求：" + row["text"], "响应：" + (row["response"].strip() or "【待补】请填写经核对的响应")]
        if any(word in row["text"] for word in ("资质", "证书", "证明", "业绩", "授权")) and not row["evidence_ids"]:
            lines.append("【待补】本条款缺少已核对证据，不得编造证明。")
    if not snapshot["requirements"]:
        lines.append("【待补】请先在响应矩阵关联本章节条款。")
    for item in snapshot["evidence"]:
        lines += [f"已确认可引用证据：{item['name']}（标识 {item['id']}，记录版本 {item['revision']}，有效期 {item['valid_until'] or '未登记'}）", item["content"]]
    if snapshot["facts"]:
        lines.append("以下为本章可用事实；正文引用时须保留变量，不能把变量改成手写取值：")
    for fact in snapshot["facts"]:
        value = fact["value"] + (" " + fact["unit"] if fact["unit"] else "")
        source = fact["source"]
        lines.append(f"{fact['key']}：{fact['variable']}；核对取值：{value}；" +
                     (f"来源：{source.get('filename', source['file_id'])} 第{source['page']}页：{source['quote']}" if source else "来源：已确认项目事实，无原文页码"))
    if snapshot["official_content"].strip():
        lines += ["当前已提交正文（所有事实变量必须保留）：", snapshot["official_content"]]
    content = "\n".join(lines)
    if len(content) > 100_000:
        raise DomainError(413, "GENERATION_CONTEXT_TOO_LARGE", "本章输入超过演示模型容量，请缩小本章条款或证据范围；不会悄悄截断资料。")
    return content


def refuse_source_change(instruction, snapshot):
    verbs = re.search(r"(?:修改|更改|改成|改为|调整|设为|设置为|替换|改写|换成|change|replace|update|set)\s*", instruction, re.I)
    if not verbs:
        return
    source_named = any(fact["key"] in instruction or fact["variable"] in instruction for fact in snapshot["facts"])
    explicit = re.search(r"(?:项目事实|事实取值|源值|承诺取值|承诺值|SLA值)", instruction, re.I)
    # “改写本章”属于正常文字编辑；指令点名来源字段并要求改变取值才阻断。
    value_change = re.search(r"(?:改成|改为|设为|设置为|换成|取值|数值|数字|改动|修改|更改|调整|change|replace|update|set)", instruction, re.I)
    if (source_named or explicit) and value_change:
        raise DomainError(409, "FACT_SOURCE_CHANGE_REQUIRED", "助手不能修改项目事实或服务承诺取值；请到项目事实或服务承诺矩阵修改来源，重新确认方案后再生成。",
                          {"reason": "data_source_value", "data_source_tabs": ["facts", "matrix"]})


def resolve_fact_variables(state, project_id, text, *, allowed_ids=None):
    facts = {fact["id"]: fact for fact in project_facts(state, project_id)}
    workflow = state.workflows.get(project_id, {})
    def replace(match):
        fact = facts.get(match.group(1))
        if (fact is None or fact["status"] != "confirmed" or not _source_valid(workflow, fact.get("source"))
                or (allowed_ids is not None and fact["id"] not in allowed_ids)):
            raise DomainError(409, "FACT_VARIABLE_INVALID", "正文事实变量不存在、未确认、来源失效或未纳入本章方案：" + match.group(1))
        if fact.get("sla_var_key"):
            raise DomainError(409, "FACT_VARIABLE_INVALID", "服务承诺须使用其专用变量，不能改用普通事实变量绕过单位核对。")
        value, unit = fact["value"], fact.get("unit", "")
        # 解析事实常把数字和单位一起保存，例如value="12个月"、unit=""。
        # 只识别完整的数字+字典单位，不从普通地点/名称文本猜单位。
        embedded = FACT_NUMBER_UNIT.fullmatch(value.strip())
        embedded_code = FACT_UNIT_ALIASES.get(embedded.group(1), embedded.group(1)) if embedded else None
        if embedded_code and unit and embedded_code != unit_code(unit):
            raise DomainError(409, "FACT_VARIABLE_UNIT_MISMATCH", "已确认事实的取值和单位字段矛盾，请先核对事实表：" + fact["key"])
        suffix = FACT_UNIT_SUFFIX.match(text[match.end():])
        expected_unit = embedded_code or unit_code(unit)
        suffix_code = FACT_UNIT_ALIASES.get(suffix.group(1), suffix.group(1)) if suffix else None
        if expected_unit and suffix and suffix_code != expected_unit:
            raise DomainError(409, "FACT_VARIABLE_UNIT_MISMATCH", "正文事实变量后的单位与已确认事实不同：" + fact["key"])
        if embedded_code and suffix:
            raise DomainError(409, "FACT_VARIABLE_UNIT_DUPLICATED", "事实取值已包含单位，请删除正文变量后的重复单位：" + fact["key"])
        own_suffix = unit and re.match(r"\s*" + re.escape(unit), text[match.end():])
        return value if embedded_code or not unit or suffix or own_suffix or value.rstrip().endswith(unit) else value + " " + unit
    result = FACT_TOKEN.sub(replace, text)
    if re.search(r"\{\{\s*fact\s*:", result):
        raise DomainError(409, "FACT_VARIABLE_INVALID", "正文事实变量格式不完整，请从已确认事实重新插入。")
    return resolve_variables(state, project_id, result)


def validate_model_output(state, project_id, content, snapshot):
    from .parsing import LocalTextParser
    if not isinstance(content, str) or not content.strip() or len(content) > 100_000:
        raise DomainError(502, "MODEL_OUTPUT_INVALID", "模型返回内容为空或超过容量，未保存候选。")
    LocalTextParser._validate_text(content)
    resolve_fact_variables(state, project_id, content, allowed_ids={fact["id"] for fact in snapshot["facts"]})
    for issue in sla_issues(state, project_id, [SimpleNamespace(id=snapshot["chapter"]["id"], content=content)]):
        if issue["code"] == "SLA_TEXT_MISMATCH":
            raise DomainError(409, issue["code"], issue["message"])
    allowed_sla = {fact["sla_var_key"] for fact in snapshot["facts"] if fact.get("sla_var_key")}
    if any(match.group(1) not in allowed_sla for match in SLA_TOKEN.finditer(content)):
        raise DomainError(409, "FACT_VARIABLE_INVALID", "模型引用了未纳入本章方案的服务承诺事实。")
    original_tokens = {match.group(0) for pattern in (FACT_TOKEN, SLA_TOKEN) for match in pattern.finditer(snapshot["official_content"])}
    if any(token not in content for token in original_tokens):
        raise DomainError(409, "FACT_VARIABLE_LOST", "模型删除了正式正文中的事实变量，请保留变量后重新生成。")
    # 可确定的“字段名：原取值”替换单独阻断；不声称覆盖所有自然语言语义。
    for fact in snapshot["facts"]:
        label = re.escape(fact["key"])
        value = re.escape(fact["value"])
        if re.search(label + r"\s*[:：为是]\s*" + value + r"(?![\w.])", content) and fact["variable"] not in content:
            raise DomainError(409, "FACT_LITERAL_REPLACEMENT", "模型把事实变量改成了手写取值：" + fact["key"])
