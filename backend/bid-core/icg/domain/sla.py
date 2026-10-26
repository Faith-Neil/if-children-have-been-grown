# 为什么有这个文件：把服务承诺的招标要求、公司能力和项目取值放在同一处判定。
# 它解决什么问题：防止页面伪造满足、旧批准继续生效，或事实表与导出使用不同数字。

from __future__ import annotations

import re
from copy import deepcopy
from decimal import Decimal, InvalidOperation
from types import SimpleNamespace

from .domain import DomainError, Export, content_hash, iso_time, new_id

TOKEN = re.compile(r"\{\{\s*sla:([A-Za-z0-9_.-]+)\s*\}\}")
TEMPLATE_TOKEN = re.compile(r"\{\{\s*(?:sla:)?([A-Za-z0-9_.-]+)\s*\}\}")
KEY = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,99}$")
UNIT_ALIASES = {"分钟": "minute", "小时": "hour", "自然日": "calendar_day", "工作日": "working_day",
                "次/月": "per_month", "次/季": "per_quarter", "次/半年": "per_half_year", "次/年": "per_year",
                "人": "person", "个": "piece", "%": "percent", "课时": "class_hour", "月": "month"}
UNITS = {"", *UNIT_ALIASES.values()}
UNIT_LABELS = {code: label for label, code in UNIT_ALIASES.items()}
UNIT_SUFFIX = re.compile(r"\s*(" + "|".join(re.escape(item) for item in sorted(
    (*UNIT_ALIASES.keys(), *UNIT_ALIASES.values()), key=len, reverse=True)) + r")")
GROUPS = {"response", "onsite", "restore", "inspection", "resident", "report", "spare_parts",
          "training", "warranty", "delivery", "other"}
LABELS = {"satisfied": "满足", "not_satisfied": "不满足", "exceeds_capability": "超出能力",
          "missing": "未填写", "manual": "需人工判断", "not_required": "招标未要求", "unquantified": "招标未量化"}


def unit_code(value):
    return UNIT_ALIASES.get(value, value)


def number(value, value_type="decimal"):
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise DomainError(422, "INVALID_SLA_VALUE", "承诺值须为有限的非负数。")
    if len(str(value)) > 100:
        raise DomainError(422, "INVALID_SLA_VALUE", "承诺值过长。")
    try:
        result = Decimal(str(value))
    except InvalidOperation as error:
        raise DomainError(422, "INVALID_SLA_VALUE", "承诺值须为有限的非负数。") from error
    if not result.is_finite() or result < 0 or result > Decimal("1e15") or (result and result < Decimal("1e-12")):
        raise DomainError(422, "INVALID_SLA_VALUE", "承诺值须为有限非负数，非零值在万亿分之一到一千万亿之间。")
    if value_type == "integer" and result != result.to_integral_value():
        raise DomainError(422, "INVALID_SLA_VALUE", "此项承诺必须填写整数。")
    return result


def value_text(value):
    if value is None:
        return ""
    if isinstance(value, (int, float)):
        return format(Decimal(str(value)).normalize(), "f")
    return str(value)


def validate_value(value, value_type, *, nullable=False):
    if value is None and nullable:
        return
    if value_type == "text":
        if not isinstance(value, str) or not value.strip() or len(value) > 100:
            raise DomainError(422, "INVALID_SLA_VALUE", "文本承诺须填写1至100字。")
    else:
        number(value, value_type)


def converted(value, source_unit, target_unit):
    """只换算具有相同含义的时长；频次不同周期不能按总次数强行等价。"""
    source, target = unit_code(source_unit), unit_code(target_unit)
    if source == target:
        return number(value)
    factors = {"minute": Decimal(1), "hour": Decimal(60), "calendar_day": Decimal(1440)}
    if source in factors and target in factors:
        return number(value) * factors[source] / factors[target]
    return None


def _strict(left, right, direction):
    return left < right if direction == "lower_better" else left > right if direction == "higher_better" else left != right


def _worse(left, right, direction):
    return left > right if direction == "lower_better" else left < right if direction == "higher_better" else left != right


def judge_row(row):
    project, tender, capability = row.get("project_value"), row.get("tender_required_value"), row.get("best_committable_value")
    if project is None or project == "":
        return "missing", "请填写本项目承诺值。", False
    text_value = row["value_type"] == "text"
    direction = row["compare_direction"]
    normalized = project if text_value else number(project)
    tender_normalized = None
    if tender is not None:
        tender_normalized = tender if text_value else converted(tender, row.get("tender_unit", ""), row["project_unit"])
        if tender_normalized is not None and _worse(normalized, tender_normalized, direction):
            return "not_satisfied", "项目承诺劣于招标要求，不能用人工批准改为满足。", False
    capability_normalized = None
    if capability is not None:
        capability_normalized = capability if text_value else converted(capability, row["unit"], row["project_unit"])
    exceeds = capability_normalized is not None and _strict(normalized, capability_normalized, direction)
    if exceeds:
        return "exceeds_capability", "承诺严于公司能力极限，需负责人说明履约依据。", True
    if row.get("requirement_id") and tender is None:
        return "unquantified", "原条款没有登记数值要求，须负责人说明核对依据。", False
    if tender is not None and tender_normalized is None:
        return "manual", "单位含义不同，系统无法可靠换算，须负责人判断。", False
    if capability is None or capability_normalized is None:
        return "manual", "公司能力未知或无法可靠换算，须负责人说明依据；不能自动判为满足。", False
    if not row.get("requirement_id"):
        return "not_required", "尚未绑定招标来源；该承诺不代表招标要求。", False
    return "satisfied", "承诺不劣于已登记招标要求，且未超出公司能力。", False


def source_fingerprint(requirement):
    import json
    return content_hash(json.dumps({k: requirement.get(k) for k in ("id", "text", "source", "status")},
                                   sort_keys=True, ensure_ascii=False))


def row_fingerprint(template, row, requirement):
    import json
    payload = {"template": template, "definition": row["definition"],
               "values": {k: row.get(k) for k in ("project_value", "project_unit", "requirement_id",
                                                  "tender_required_value", "tender_unit")},
               "requirement": {k: requirement.get(k) for k in ("id", "text", "source", "status")} if requirement else None}
    return content_hash(json.dumps(payload, sort_keys=True, ensure_ascii=False))


def public_sla(state, project_id):
    workflow = state.workflows.get(project_id, {})
    selected = workflow.get("sla")
    if not selected:
        return None
    template = state.sla_templates.get(selected["template_id"])
    company = state.projects[project_id].company_id
    stale = (not template or template["company_id"] != company or template["status"] != "confirmed"
             or template["revision"] != selected["template_revision"])
    rows = []
    for saved in selected["values"].values():
        row = {**deepcopy(saved["definition"]), **{k: saved.get(k) for k in
               ("project_value", "project_unit", "requirement_id", "tender_required_value", "tender_unit")}}
        requirement = workflow.get("requirements", {}).get(saved.get("requirement_id"))
        source_stale = bool(saved.get("requirement_id") and
                            (not requirement or requirement["status"] != "confirmed"
                             or source_fingerprint(requirement) != saved.get("source_fingerprint")))
        fingerprint = row_fingerprint(template, saved, requirement)
        review = saved.get("review")
        review = deepcopy(review) if review and review.get("fingerprint") == fingerprint and not stale and not source_stale else None
        status = saved.get("fact_status", "pending")
        if stale or source_stale or (status == "confirmed" and saved.get("fact_fingerprint") != fingerprint):
            status = "needs_review"
        judgment, message, exceeds = judge_row(row)
        row.update(source=deepcopy(requirement["source"]) if requirement else None, source_stale=source_stale,
                   judgment=judgment, judgment_label=LABELS[judgment], message=message,
                   exceeds_capability=exceeds, review=review, fact_status=status,
                   variable_token="{{sla:" + row["var_key"] + "}}")
        rows.append(row)
    from .input_snapshot import project_input_fingerprint
    fingerprint = project_input_fingerprint(state, project_id)
    commitments = [{k: v for k, v in entry.items() if k not in ("content", "table")}
                   | {"status": "valid" if entry["fingerprint"] == fingerprint else "stale"}
                   for entry in workflow.get("sla_commitments", {}).values()]
    return {"template_id": selected["template_id"], "template_name": template["name"] if template else selected["template_name"],
            "template_revision": selected["template_revision"], "template_stale": stale, "rows": rows,
            "commitments": commitments}


def sla_facts(state, project_id):
    sla = public_sla(state, project_id)
    if not sla:
        return []
    return [{"id": "sla:" + row["var_key"], "key": row["label"], "value": value_text(row["project_value"]),
             "unit": row["project_unit"], "status": row["fact_status"], "reason": "", "source": row["source"],
             "source_type": "sla", "sla_var_key": row["var_key"], "required": bool(row["requirement_id"])}
            for row in sla["rows"]]


def sla_issues(state, project_id, chapters=()):
    sla = public_sla(state, project_id)
    requirements = state.workflows.get(project_id, {}).get("requirements", {})
    issues = []
    def add(code, message, **links):
        issues.append({"id": new_id("issue"), "code": code, "severity": "blocking", "message": message, **links})
    linked = {r["requirement_id"] for r in sla["rows"] if r["requirement_id"]} if sla else set()
    for requirement in requirements.values():
        if (requirement.get("sla_required") or requirement["category"] == "sla") and requirement["status"] != "rejected" and requirement["id"] not in linked:
            add("SLA_REQUIREMENT_UNBOUND", "服务承诺条款尚未绑定指标，不能靠改类别跳过。", requirement_id=requirement["id"])
    if sla:
        if sla["template_stale"]:
            add("SLA_TEMPLATE_STALE", "公司模板已变化或未确认，请刷新模板并重新核对项目承诺。")
        for row in sla["rows"]:
            links = {"requirement_id": row["requirement_id"]} if row["requirement_id"] else {}
            if row["source_stale"]:
                add("SLA_SOURCE_STALE", row["label"] + "的招标来源已变化，请重新登记要求。", **links)
            if row["judgment"] in ("missing", "not_satisfied"):
                add("SLA_VALUE_INVALID", row["label"] + "：" + row["message"], **links)
            if row["judgment"] in ("manual", "unquantified", "exceeds_capability", "not_required") and not row["review"]:
                add("SLA_REVIEW_REQUIRED", row["label"] + "：" + row["message"], **links)
            if row["requirement_id"] and row["fact_status"] != "confirmed":
                add("SLA_FACT_UNCONFIRMED", row["label"] + "须由项目负责人逐条确认。", **links)
    for chapter in chapters:
        try:
            resolve_variables(state, project_id, chapter.content)
        except DomainError as error:
            add(error.code, error.message, chapter_id=chapter.id)
        if not sla:
            continue
        for row in sla["rows"]:
            if row["value_type"] == "text" or row["project_value"] is None:
                continue
            # 只覆盖可明确识别的“指标名＋数值＋单位”，不冒充自然语言全覆盖。
            label = re.escape(row["label"])
            expression = re.compile(label + r"\s*[:：为是]?\s*(\d+(?:\.\d+)?)\s*(分钟|小时|自然日|工作日|次/月|次/季|次/半年|次/年|课时|人|个|月|%)")
            for match in expression.finditer(chapter.content):
                actual = converted(match.group(1), match.group(2), row["project_unit"])
                if actual is None or actual != number(row["project_value"]):
                    add("SLA_TEXT_MISMATCH", row["label"] + "的手写数字与当前变量不一致：" + match.group(0), chapter_id=chapter.id)
    return issues


def resolve_variables(state, project_id, text):
    sla = public_sla(state, project_id)
    rows = {r["var_key"]: r for r in sla["rows"]} if sla else {}
    def replace(match):
        row = rows.get(match.group(1))
        if row is None:
            raise DomainError(409, "SLA_VARIABLE_UNKNOWN", "正文引用了不存在的服务承诺变量：" + match.group(1))
        if (sla["template_stale"] or row["source_stale"] or row["project_value"] is None
                or row["fact_status"] != "confirmed" or row["judgment"] == "not_satisfied"
                or (row["judgment"] in ("manual", "unquantified", "exceeds_capability", "not_required") and not row["review"])):
            raise DomainError(409, "SLA_VARIABLE_UNCONFIRMED", "正文服务承诺变量尚未有效确认：" + row["label"])
        # 模板中的变量以模板单位输出；不能把0.5小时接到“分钟”后缀而变成0.5分钟。
        unit = unit_code(row["unit"])
        value = row["project_value"] if row["value_type"] == "text" else converted(
            row["project_value"], row["project_unit"], unit)
        if value is None:
            raise DomainError(409, "SLA_VARIABLE_UNIT_UNRESOLVED", "承诺无法换算为正文变量的模板单位：" + row["label"])
        suffix = UNIT_SUFFIX.match(text[match.end():])
        if suffix and unit_code(suffix.group(1)) != unit:
            raise DomainError(409, "SLA_VARIABLE_UNIT_MISMATCH", "正文变量后的单位与模板不同：" + row["label"])
        displayed = format(value.normalize(), "f") if isinstance(value, Decimal) else value_text(value)
        return displayed if suffix or not unit else displayed + " " + UNIT_LABELS[unit]
    result = TOKEN.sub(replace, text)
    if re.search(r"\{\{\s*sla\s*:", result):
        raise DomainError(409, "SLA_VARIABLE_UNKNOWN", "正文服务承诺变量格式不完整，请重新插入变量。")
    return result


class SlaService:
    def __init__(self, workflow):
        self.workflow = workflow
        self.demo = workflow.demo
        self.repository = workflow.repository

    @staticmethod
    def manager(principal):
        if principal.user.role != "manager":
            raise DomainError(403, "SLA_MANAGER_REQUIRED", "服务承诺维护和必备事实确认仅限本公司项目负责人。")

    def templates(self, principal):
        state = self.repository.read()
        company = principal.user.company_id
        return {"revision": state.library_revisions.get(company, 1),
                "items": [item for item in state.sla_templates.values() if item["company_id"] == company]}

    @staticmethod
    def validate_template(item):
        keys = set()
        for variable in item["variables"]:
            if not KEY.fullmatch(variable["var_key"]) or variable["var_key"] in keys:
                raise DomainError(422, "INVALID_SLA_VARIABLE", "模板变量键须以字母开头且在本模板内唯一。")
            keys.add(variable["var_key"])
            if not variable["label"].strip() or not variable["group"].strip():
                raise DomainError(422, "INVALID_SLA_VARIABLE", "指标名称和分组不能为空。")
            if variable["group"] not in GROUPS:
                raise DomainError(422, "INVALID_SLA_GROUP", "请从服务承诺指标分组中选择。")
            if unit_code(variable["unit"]) not in UNITS:
                raise DomainError(422, "INVALID_SLA_UNIT", "请从字典的服务承诺单位中选择。")
            if variable["value_type"] == "text" and variable["compare_direction"] != "exact":
                raise DomainError(422, "INVALID_SLA_DIRECTION", "文本承诺使用须一致的比较方向。")
            validate_value(variable["default_value"], variable["value_type"])
            validate_value(variable.get("best_committable_value"), variable["value_type"], nullable=True)
        if not item["name"].strip() or not item["body_text"].strip() or not item["version_no"].strip():
            raise DomainError(422, "EMPTY_SLA_TEMPLATE", "模板名称、业务版本号和正文不能为空。")
        if item["status"] == "confirmed":
            remaining = TEMPLATE_TOKEN.sub(lambda match: "" if match.group(1) in keys else match.group(0), item["body_text"])
            if "{{" in remaining or "}}" in remaining:
                raise DomainError(409, "SLA_TEMPLATE_VARIABLE_UNKNOWN", "模板正文引用了不存在或格式错误的变量，不能确认。")

    def write_template(self, principal, payload, expected, key, item_id=None):
        from .idempotency import lookup, remember
        self.manager(principal)
        key = self.workflow._idempotency(key)
        company = principal.user.company_id
        scope_id = "library:" + company
        action = "sla-template.update:" + item_id if item_id else "sla-template.create"
        request_fingerprint = self.workflow._request_hash(action, payload, expected)
        def operation(state):
            replay = lookup(state, scope_id, principal.user.id, key, request_fingerprint, self.demo._now())
            if replay is not None:
                return replay
            revision = state.library_revisions.get(company, 1)
            self.workflow._version(revision, expected)
            previous = state.sla_templates.get(item_id) if item_id else None
            if item_id and (not previous or previous["company_id"] != company):
                raise DomainError(404, "NOT_FOUND", "未找到本公司服务承诺模板。")
            if any(v is None for v in payload.values()):
                raise DomainError(422, "INVALID_SLA_TEMPLATE", "模板字段不能设为空值。")
            item = {**deepcopy(previous), **deepcopy(payload)} if previous else {
                "id": new_id("sla-template"), "company_id": company, "revision": 0, **deepcopy(payload)}
            changed = previous and any(k in payload and payload[k] != previous[k] for k in
                                      ("name", "edition", "service_hours", "body_text", "version_no", "variables"))
            if changed:
                if payload.get("status") == "confirmed":
                    if not payload.get("reason", "").strip():
                        raise DomainError(409, "REVIEW_REASON_REQUIRED", "模板实质内容变化后同次重新确认须填写依据。")
                else:
                    item.update(status="pending", reason="")
            if item["status"] == "confirmed" and (not previous or previous["status"] != "confirmed"
                                                   or "status" in payload):
                if not payload.get("reason", "").strip():
                    raise DomainError(409, "REVIEW_REASON_REQUIRED", "确认服务模板须填写本次逐项核对依据。")
            self.validate_template(item)
            item["revision"] += 1
            state.sla_templates[item["id"]] = item
            state.library_revisions[company] = revision + 1
            # 模板关键字段变化立即使在编项目引用型事实需复核；项目取值不删除。
            for project_id, workflow in state.workflows.items():
                selected = workflow.get("sla")
                if selected and selected["template_id"] == item["id"]:
                    state.projects[project_id].revision += 1
                    workflow["plan_confirmed"] = False
                    for row in selected["values"].values():
                        row.update(fact_status="needs_review", review=None, fact_fingerprint=None)
            state.audit.append({"id": new_id("event"), "action": action, "actor_id": principal.user.id,
                                "company_id": company, "project_id": "", "chapter_id": "", "revision": revision + 1,
                                "at": iso_time(self.demo._now()), "details": {"reason": payload.get("reason", ""),
                                "old": deepcopy(previous), "new": deepcopy(item)}})
            result = {"revision": revision + 1, "item": item}
            remember(state, scope_id, principal.user.id, key, request_fingerprint, result, self.demo._now())
            return result
        return self.repository.transaction(operation)

    def _write(self, principal, project_id, action, payload, expected, key, operation):
        self.manager(principal)
        def wrapped(state, project, workflow):
            old = deepcopy(workflow.get("sla"))
            result = operation(state, project, workflow)
            self.workflow._audit(state, principal, project_id, action + ".details",
                                 {"reason": payload.get("reason", ""), "old": old, "new": deepcopy(workflow.get("sla"))})
            return result
        return self.workflow._write(principal, project_id, action, payload, expected, key, wrapped)

    def select(self, principal, project_id, payload, expected, key):
        def operation(state, project, workflow):
            template = state.sla_templates.get(payload["template_id"])
            if not template or template["company_id"] != project.company_id:
                raise DomainError(404, "NOT_FOUND", "未找到本公司服务承诺模板。")
            if template["status"] != "confirmed":
                raise DomainError(409, "SLA_TEMPLATE_UNCONFIRMED", "请选择已确认的公司模板。")
            old = workflow.get("sla")
            same = old and old["template_id"] == template["id"]
            if old and not same and not payload.get("reason", "").strip():
                raise DomainError(422, "REASON_REQUIRED", "更换模板会重置项目承诺，请说明依据。")
            variables = {}
            keys = {v["var_key"] for v in template["variables"]}
            if same and set(old["values"]) - keys:
                raise DomainError(409, "SLA_VARIABLE_REMOVED", "新模板删除了已选指标。为保留项目取值，请先整理模板或明确更换模板。")
            for definition in template["variables"]:
                saved = deepcopy(old["values"].get(definition["var_key"])) if same else None
                if saved:
                    # 仍需验证已有值适配新的类型，失败整个刷新回滚，旧承诺保留。
                    validate_value(saved["project_value"], definition["value_type"], nullable=True)
                    validate_value(saved["tender_required_value"], definition["value_type"], nullable=True)
                    saved.update(definition=deepcopy(definition), review=None, fact_status="needs_review", fact_fingerprint=None)
                else:
                    saved = {"definition": deepcopy(definition), "project_value": definition["default_value"],
                             "project_unit": definition["unit"], "requirement_id": None, "tender_required_value": None,
                             "tender_unit": definition["unit"], "source_fingerprint": None,
                             "review": None, "fact_status": "pending", "fact_fingerprint": None}
                variables[definition["var_key"]] = saved
            workflow["sla"] = {"template_id": template["id"], "template_name": template["name"],
                               "template_revision": template["revision"], "values": variables}
            workflow["plan_confirmed"] = False
            return {"sla": public_sla(state, project_id)}
        return self._write(principal, project_id, "sla.template.select", payload, expected, key, operation)

    @staticmethod
    def _saved(state, project_id, workflow, var_key):
        selected = workflow.get("sla")
        if not selected or var_key not in selected["values"]:
            raise DomainError(404, "NOT_FOUND", "未找到本项目服务承诺指标。")
        if public_sla(state, project_id)["template_stale"]:
            raise DomainError(409, "SLA_TEMPLATE_STALE", "请先刷新并核对当前已确认模板。")
        return selected["values"][var_key], state.sla_templates[selected["template_id"]]

    def patch_value(self, principal, project_id, var_key, payload, expected, key):
        def operation(state, project, workflow):
            saved, template = self._saved(state, project_id, workflow, var_key)
            updated = {**saved, **{k: v for k, v in payload.items() if k != "reason"}}
            definition = saved["definition"]
            validate_value(updated["project_value"], definition["value_type"], nullable=True)
            validate_value(updated["tender_required_value"], definition["value_type"], nullable=True)
            for unit in (updated["project_unit"], updated["tender_unit"]):
                if unit is None or unit_code(unit) not in UNITS:
                    raise DomainError(422, "INVALID_SLA_UNIT", "请使用字典中的单位；不同含义的单位不可强行换算。")
            requirement = workflow["requirements"].get(updated["requirement_id"]) if updated["requirement_id"] else None
            if updated["requirement_id"] and (not requirement or requirement["status"] != "confirmed"):
                raise DomainError(409, "SLA_SOURCE_INVALID", "只能绑定本项目已确认招标条款。")
            if updated["tender_required_value"] is not None and not requirement:
                raise DomainError(422, "SLA_SOURCE_REQUIRED", "登记招标要求数值必须同时选择原文来源。")
            if any(k in payload for k in ("requirement_id", "tender_required_value", "tender_unit")):
                if not payload.get("reason", "").strip():
                    raise DomainError(422, "REASON_REQUIRED", "登记招标数值或更换来源须说明原文核对依据。")
                updated["source_fingerprint"] = source_fingerprint(requirement) if requirement else None
            changed = any(updated[k] != saved.get(k) for k in
                          ("project_value", "project_unit", "requirement_id", "tender_required_value", "tender_unit", "source_fingerprint"))
            if changed:
                updated.update(review=None, fact_status="needs_review", fact_fingerprint=None)
                workflow["plan_confirmed"] = False
            if requirement:
                requirement["sla_required"] = True
            saved.update(updated)
            return {"sla": public_sla(state, project_id)}
        return self._write(principal, project_id, "sla.value.update:" + var_key, payload, expected, key, operation)

    def apply_tender(self, principal, project_id, payload, expected, key):
        def operation(state, project, workflow):
            sla = public_sla(state, project_id)
            if not sla:
                raise DomainError(409, "SLA_TEMPLATE_REQUIRED", "请先选择服务承诺模板。")
            if sla["template_stale"]:
                raise DomainError(409, "SLA_TEMPLATE_STALE", "请先刷新并核对模板。")
            changed = False
            for row in sla["rows"]:
                if row["source_stale"]:
                    raise DomainError(409, "SLA_SOURCE_STALE", "招标来源已变，请先重新登记数值。")
                if row["tender_required_value"] is None:
                    continue
                saved = workflow["sla"]["values"][row["var_key"]]
                requested = (row["tender_required_value"] if row["value_type"] == "text" else
                             converted(row["tender_required_value"], row["tender_unit"], row["unit"]))
                if requested is None:
                    continue
                capability = row["best_committable_value"]
                if capability is not None and _strict(requested, capability if row["value_type"] == "text" else number(capability), row["compare_direction"]):
                    requested = capability
                if isinstance(requested, Decimal):
                    requested = format(requested.normalize(), "f")
                validate_value(requested, row["value_type"])
                if requested != saved["project_value"] or saved["project_unit"] != row["unit"]:
                    saved.update(project_value=requested, project_unit=row["unit"], review=None,
                                 fact_status="needs_review", fact_fingerprint=None)
                    changed = True
            if changed:
                workflow["plan_confirmed"] = False
            return {"sla": public_sla(state, project_id)}
        return self._write(principal, project_id, "sla.apply-tender", payload, expected, key, operation)

    def review(self, principal, project_id, var_key, payload, expected, key):
        if not payload["reason"].strip():
            raise DomainError(422, "REASON_REQUIRED", "请说明当前承诺的核对和履约依据。")
        def operation(state, project, workflow):
            saved, template = self._saved(state, project_id, workflow, var_key)
            row = next(row for row in public_sla(state, project_id)["rows"] if row["var_key"] == var_key)
            if row["source_stale"] or row["judgment"] in ("missing", "not_satisfied"):
                raise DomainError(409, "SLA_REVIEW_FORBIDDEN", "过期、未填写或不满足招标的承诺不能批准为通过。")
            requirement = workflow["requirements"].get(saved["requirement_id"])
            saved["review"] = {"actor_id": principal.user.id, "actor_name": principal.user.name,
                               "at": iso_time(self.demo._now()), "reason": payload["reason"].strip(),
                               "fingerprint": row_fingerprint(template, saved, requirement)}
            return {"sla": public_sla(state, project_id)}
        return self._write(principal, project_id, "sla.value.review:" + var_key, payload, expected, key, operation)

    def confirm_fact(self, state, principal, project_id, workflow, var_key, payload):
        self.manager(principal)
        saved, template = self._saved(state, project_id, workflow, var_key)
        if "value" in payload:
            raise DomainError(409, "SLA_FACT_READ_ONLY", "此事实引用服务承诺矩阵，请到来源修改取值。")
        if payload.get("status") != "confirmed":
            raise DomainError(422, "SLA_FACT_CONFIRM_REQUIRED", "服务承诺事实须逐条确认，不能忽略必备承诺。")
        row = next(row for row in public_sla(state, project_id)["rows"] if row["var_key"] == var_key)
        if row["source_stale"] or row["judgment"] in ("missing", "not_satisfied"):
            raise DomainError(409, "SLA_FACT_INVALID", "当前承诺过期、未填写或不满足招标，不能确认。")
        if row["judgment"] in ("manual", "unquantified", "exceeds_capability", "not_required") and not row["review"]:
            raise DomainError(409, "SLA_REVIEW_REQUIRED", "请先在服务承诺矩阵处理履约风险或人工判断。")
        requirement = workflow["requirements"].get(saved["requirement_id"])
        saved.update(fact_status="confirmed", fact_fingerprint=row_fingerprint(template, saved, requirement))
        self.workflow._audit(state, principal, project_id, "sla.fact.confirm", {"var_key": var_key, "reason": payload.get("reason", ""),
                             "input_fingerprint": saved["fact_fingerprint"]})
        workflow["plan_confirmed"] = False
        return {"fact": next(f for f in sla_facts(state, project_id) if f["sla_var_key"] == var_key)}

    def commitment(self, principal, project_id, payload, expected, key):
        def operation(state, project, workflow):
            sla = public_sla(state, project_id)
            if not sla:
                raise DomainError(409, "SLA_TEMPLATE_REQUIRED", "请先选用并核对服务承诺模板。")
            template = state.sla_templates[sla["template_id"]]
            normalized_body = TEMPLATE_TOKEN.sub(lambda match: "{{sla:" + match.group(1) + "}}", template["body_text"])
            issues = sla_issues(state, project_id, (SimpleNamespace(id=template["id"], content=normalized_body),))
            issues.extend({"code": "SLA_FACT_UNCONFIRMED", "message": row["label"] + "尚未确认，不能进入承诺函。"}
                          for row in sla["rows"] if row["fact_status"] != "confirmed")
            if issues:
                raise DomainError(409, "SLA_COMMITMENT_BLOCKED", "服务承诺仍有未处理项目，不能生成承诺函。", {"issues": issues})
            content = resolve_variables(state, project_id, normalized_body)
            identity = new_id("sla-commitment")
            filename = identity + ".docx"
            table = [["指标", "招标要求", "我方承诺", "公司能力极限", "判定"]]
            for row in sla["rows"]:
                display = lambda value, unit: value_text(value) + (" " + UNIT_LABELS[unit_code(unit)] if value is not None and unit else "")
                table.append([row["label"], display(row["tender_required_value"], row["tender_unit"]) or LABELS[row["judgment"]],
                              display(row["project_value"], row["project_unit"]),
                              display(row["best_committable_value"], row["unit"]) or "未登记，须人工核对", row["judgment_label"]])
            record = {"id": identity, "filename": filename,
                      "download_url": f"/api/v1/projects/{project_id}/sla/commitment/{identity}",
                      "created_at": iso_time(self.demo._now()), "fingerprint": self.workflow._fingerprint(state, project_id),
                      "content": self.workflow._mask(content),
                      "table": [[self.workflow._mask(cell) for cell in line] for line in table]}
            workflow.setdefault("sla_commitments", {})[identity] = record
            return {"commitment": {k: v for k, v in record.items() if k not in ("content", "table")} | {"status": "valid"}}
        return self._write(principal, project_id, "sla.commitment.export", payload, expected, key, operation)

    def download(self, principal, project_id, export_id):
        def operation(state):
            project = self.demo._project(state, principal, project_id)
            record = self.workflow._workflow(state, project_id).get("sla_commitments", {}).get(export_id)
            if not record:
                raise DomainError(404, "NOT_FOUND", "未找到本项目承诺函。")
            if record["fingerprint"] != self.workflow._fingerprint(state, project_id):
                raise DomainError(409, "EXPORT_STALE", "项目输入已变化，旧承诺函已过期。")
            self.workflow._audit(state, principal, project_id, "sla-commitment.download", {"export_id": export_id})
            return {**record, "title": self.workflow._mask(project.name) + " — 服务承诺函（内部稿）",
                    "project_name": self.workflow._mask(project.name)}
        return self.repository.transaction(operation)
