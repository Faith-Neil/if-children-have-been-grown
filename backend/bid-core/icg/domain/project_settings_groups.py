# 为什么有这个文件：项目设置里 PRD v1.8 §5.1.4 的设置组读写（基本信息人工修改标记、合作方协议、规则覆盖、分册格式、
# 递交版完整值类别）和概览待办（APP-M2-T097～T100）。
# 它解决什么问题：project_settings.py 只管基本字段保存；这里集中各设置组的校验、保存和读回，
# 事务、版本、幂等与审计仍走 WorkflowService._write（动作名 project.update:<组>，仅项目负责人）。
# 数据保存在项目工作流里（basic_info、manual_edits、rule_overrides、volume_settings、submit_full_value），
# 对应字典的 project_rule_override、bid_volume 设置列和 bid_project.submit_full_value_*。

from __future__ import annotations

from datetime import timedelta
from typing import Any

from .domain import DomainError, Principal, iso_time
from .export_naming import problems
from .project_access import project_volumes
from .project_lifecycle import (CLOSED, current_status, occupancy_conflicts, parse_time, registered_status)
from .sla import public_sla

BASIC_KEYS = ("tenderee_name", "agency_name", "lot_name", "client_address", "open_at", "service_period", "project_location")
TRACKED_FIELDS = ("name", "tender_number", "deadline", *BASIC_KEYS)
FULL_VALUE_CATEGORIES = {"id_number": "身份证件号码", "phone": "手机号", "bank_account": "银行账号"}
BOOL_RULES = ("require_own_staff", "check_service_period")
COMPILE_MODES = ("system", "external")
PAGE_NUMBERING = ("per_volume", "continuous")
URGENT_DAYS = 3  # 示例 3 天（PRD 5.1.1，可配置）；分册内部截止提前 1 天进待办（PRD 5.1.4 规则 4）


def mark_manual_edits(workflow: dict, changed: list[str], principal: Principal, now: str) -> None:
    marks = workflow.setdefault("manual_edits", {})
    for field in changed:
        marks[field] = {"by": principal.user.id, "at": now}


def partner_rows(raw: list[dict]) -> list[dict]:
    return [{**p, "agreement_ok": bool(str(p.get("agreement_attachment_id") or "").strip()),
             "problem": None if str(p.get("agreement_attachment_id") or "").strip() else "缺协议：其资料不能被章节引用"}
            for p in raw or []]


def validate_partners(partners: list[dict]) -> list[dict]:
    seen, cleaned = set(), []
    for item in partners:
        entity = item["partner_entity_id"].strip()
        if not entity:
            raise DomainError(422, "VALIDATION_ERROR", "合作方主体不能为空。")
        if entity in seen:
            raise DomainError(422, "VALIDATION_ERROR", "同一合作方不要重复添加。", {"partner_entity_id": entity})
        seen.add(entity)
        agreement = (item.get("agreement_attachment_id") or "").strip() or None
        cleaned.append({**{k: v for k, v in item.items() if v is not None}, "partner_entity_id": entity,
                        "agreement_attachment_id": agreement})
    return cleaned


def validate_rule_overrides(workflow: dict, entries: list[dict]) -> dict:
    result, requirements = {}, workflow.get("requirements", {})
    for entry in entries:
        key, value, basis = entry["rule_key"].strip(), entry["value"], entry.get("source_requirement_id")
        if key in result:
            raise DomainError(422, "VALIDATION_ERROR", f"规则 {key} 重复。")
        if key.startswith("proof_valid_days."):
            ok = len(key) > len("proof_valid_days.") and isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= 3650
            hint = "证明材料有效天数须为 1～3650 的整数，并写明材料类型，如 proof_valid_days.纳税证明"
        elif key == "social_insurance_months":
            ok = isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 120
            hint = "连续缴纳社保月数须为 0～120 的整数"
        elif key in BOOL_RULES:
            ok, hint = isinstance(value, bool), "该规则的取值只能是是 / 否"
        else:
            raise DomainError(422, "VALIDATION_ERROR", f"不认识的规则：{key}", {"rule_key": key})
        if not ok:
            raise DomainError(422, "VALIDATION_ERROR", hint, {"rule_key": key})
        if basis and basis not in requirements:
            raise DomainError(422, "VALIDATION_ERROR", "依据的招标要求不存在于本项目。", {"source_requirement_id": basis})
        result[key] = {"value": value, "source_requirement_id": basis or None}
    return result


def validate_volume_settings(state: Any, project: Any, entries: list[dict]) -> tuple[dict, list[str]]:
    active, result, warnings = project_volumes(state, project.id), {}, []
    names = [state.accounts[i].name for i in (state.project_teams.get(project.id) or {}).get("members", {}) if i in state.accounts]
    limit = parse_time(project.deadline)
    for entry in entries:
        volume = entry["volume"]
        if volume not in active:
            raise DomainError(422, "VALIDATION_ERROR", "本项目没有这个分册。", {"volume": volume})
        if volume in result:
            raise DomainError(422, "VALIDATION_ERROR", "同一分册不要重复设置。", {"volume": volume})
        deadline = (entry.get("internal_deadline") or "").strip()
        moment = parse_time(deadline) if deadline else None
        if deadline and moment is None:
            raise DomainError(422, "INVALID_DATE", "内部截止时间请使用 ISO 时间格式，如 2026-12-30T17:00。")
        if moment and limit and moment > limit:
            warnings.append(f"{_label(volume)}分册内部截止时间晚于项目投标截止时间")
        name = (entry.get("submit_file_name") or "").strip()
        issues = problems(name, "submission") if name else []
        leaked = [n for n in names if n and n in name]
        if leaked:
            issues.append("递交文件名不能含编写人姓名：" + "、".join(leaked))
        if issues:
            raise DomainError(422, "VALIDATION_ERROR", "；".join(issues), {"volume": volume, "submit_file_name": name})
        result[volume] = {"compile_mode": entry["compile_mode"], "internal_deadline": deadline or None,
                          "separate_seal": bool(entry["separate_seal"]), "page_numbering": entry["page_numbering"],
                          "blind_bid": bool(entry["blind_bid"]), "cover_template": (entry.get("cover_template") or "").strip() or None,
                          "submit_file_name": name or None}
    return result, warnings


def validate_full_value(workflow: dict, categories: list[str], basis_ids: list[str]) -> None:
    unknown = sorted(set(categories) - set(FULL_VALUE_CATEGORIES))
    if unknown:
        raise DomainError(422, "VALIDATION_ERROR", "不认识的完整值类别：" + "、".join(unknown))
    if categories and not basis_ids:
        raise DomainError(422, "VALIDATION_ERROR", "勾选需填完整值的类别须关联招标要求作为依据。")
    missing = [i for i in basis_ids if i not in workflow.get("requirements", {})]
    if missing:
        raise DomainError(422, "VALIDATION_ERROR", "依据的招标要求不存在于本项目。", {"requirement_ids": missing})


def project_todos(state: Any, project: Any, workflow: dict, now: float) -> list[dict]:
    """概览待办（PRD 5.1.3）。每项带 tab，可一键跳转；只列真实存在的问题。"""
    if registered_status(workflow) in CLOSED:
        return []
    todos = []

    def add(code: str, title: str, tab: str, detail: str = "") -> None:
        todos.append({"code": code, "title": title, "detail": detail, "tab": tab})

    for partner in partner_rows(state.project_partners.get(project.id, [])):
        if not partner["agreement_ok"]:
            add("PARTNER_AGREEMENT_MISSING", f"合作方 {partner['partner_entity_id']} 缺联合体/分包协议", "settings", partner["problem"])
    owners = (state.project_teams.get(project.id) or {}).get("owners") or {}
    settings = workflow.get("volume_settings") or {}
    when = project_now(now)
    for volume in project_volumes(state, project.id):
        setting = settings.get(volume) or {}
        if setting.get("compile_mode") != "external" and not owners.get(volume):
            add("VOLUME_OWNER_MISSING", f"{_label(volume)}分册未指定负责人", "settings", "未指定负责人的系统编制分册，其写作方案不能确认")
        due = parse_time(setting.get("internal_deadline"))
        if due and due - when <= timedelta(days=1) and not _finalized(workflow, volume):
            add("VOLUME_DEADLINE_NEAR", f"{_label(volume)}分册内部截止时间已到或不足 1 天，尚未定稿", "editor")
    deadline = parse_time(project.deadline)
    if deadline and timedelta(0) < deadline - when <= timedelta(days=URGENT_DAYS):
        add("BID_DEADLINE_NEAR", f"距投标截止时间不足 {URGENT_DAYS} 天", "overview")
    for item in occupancy_conflicts(state, project, workflow):
        add("STAFF_OCCUPIED", f"{item['person_name']}同时拟派在“{item['other_project_name']}”", "settings", "只提示，不锁定")
    return todos


def project_now(now: float):
    from datetime import datetime, timezone
    return datetime.fromtimestamp(now, timezone.utc)


def _label(volume: str) -> str:
    return {"technical": "技术", "business": "商务"}.get(volume, volume)


def _finalized(workflow: dict, volume: str) -> bool:
    return bool((workflow.get("volumes") or {}).get(volume, {}).get("is_finalized"))


class ProjectSettingsGroupsMixin:
    """WorkflowService 的项目设置组：读回（getProjectSettings）和三个分组保存。"""

    def project_settings(self, principal: Principal, project_id: str) -> dict:
        state = self.repository.read()
        project = self.demo._project(state, principal, project_id)
        workflow = self._workflow(state, project_id)
        sla = public_sla(state, project_id)
        stage = self.workspace_stage(state, project_id, workflow)
        return {
            "revision": project.revision, "status": current_status(workflow, stage),
            "basic_info": {k: (workflow.get("basic_info") or {}).get(k, "") for k in BASIC_KEYS},
            "manual_edits": workflow.get("manual_edits") or {},
            "partners": partner_rows(state.project_partners.get(project_id, [])),
            "rule_overrides": [{"rule_key": k, **v} for k, v in (workflow.get("rule_overrides") or {}).items()],
            "volume_settings": [{"volume": v, **(workflow.get("volume_settings") or {}).get(v, DEFAULT_VOLUME)}
                                for v in project_volumes(state, project_id)],
            "submit_full_value": workflow.get("submit_full_value") or {
                "categories": [], "basis_requirement_ids": [], "confirmed_by": None, "confirmed_at": None},
            "sla": None if not sla else {"template_name": sla["template_name"], "template_stale": sla["template_stale"],
                                         "row_count": len(sla["rows"]),
                                         "exceeds_capability_count": sum(1 for r in sla["rows"] if r["exceeds_capability"]),
                                         "needs_review_count": sum(1 for r in sla["rows"] if r["fact_status"] == "needs_review")},
            "staff_occupancy": occupancy_conflicts(state, project, workflow),
            "todos": project_todos(state, project, workflow, self.demo._now()),
        }

    def save_rule_overrides(self, principal: Principal, project_id: str, payload: dict, expected: str | None, key: str | None):
        def operation(state, project, workflow):
            workflow["rule_overrides"] = validate_rule_overrides(workflow, payload["overrides"])
            for saved in workflow["rule_overrides"].values():
                saved.update(updated_by=principal.user.id, updated_at=iso_time(self.demo._now()))
            return {"rule_overrides": [{"rule_key": k, **v} for k, v in workflow["rule_overrides"].items()]}
        return self._write(principal, project_id, "project.update:rules", payload, expected, key, operation)

    def save_volume_settings(self, principal: Principal, project_id: str, payload: dict, expected: str | None, key: str | None):
        def operation(state, project, workflow):
            saved, warnings = validate_volume_settings(state, project, payload["volumes"])
            workflow["volume_settings"] = saved
            return {"volume_settings": [{"volume": v, **s} for v, s in saved.items()], "warnings": warnings}
        return self._write(principal, project_id, "project.update:volumes", payload, expected, key, operation)

    def save_full_value(self, principal: Principal, project_id: str, payload: dict, expected: str | None, key: str | None):
        def operation(state, project, workflow):
            categories = list(dict.fromkeys(payload["categories"]))
            basis = list(dict.fromkeys(payload["basis_requirement_ids"]))
            validate_full_value(workflow, categories, basis)
            workflow["submit_full_value"] = {"categories": categories, "basis_requirement_ids": basis,
                                             "confirmed_by": principal.user.id if categories else None,
                                             "confirmed_at": iso_time(self.demo._now()) if categories else None}
            return {"submit_full_value": workflow["submit_full_value"]}
        return self._write(principal, project_id, "project.update:full_value", payload, expected, key, operation)


DEFAULT_VOLUME = {"compile_mode": "system", "internal_deadline": None, "separate_seal": False, "page_numbering": "per_volume",
                  "blind_bid": False, "cover_template": None, "submit_file_name": None}
