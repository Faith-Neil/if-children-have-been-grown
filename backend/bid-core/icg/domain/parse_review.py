# 为什么有这个文件：解析结果页的分类树、确认闸门与批量确认（PRD v1.8 §5.2.2；APP-M2-T104）。
# 它解决什么问题：
# 1. 把抽取出的条款和事实归入 PRD 的 10 类（项目基本信息、资格要求、评分办法与评分项、废标与无效标、星号实质性条款、
#    技术服务要求、SLA、投标文件格式、时间节点、保证金），每类给出条目数和待确认数；评分类再按评分项分组列出得分要点；
# 2. “确认解析结果”的前提逐条列出（冲突待选定、疑似遗漏、星号/废标/资格逐条确认、其他待确认、事实待核对），
#    每条带剩余条数，页面直接显示还差什么；“引用未解析”只提示不阻断；
# 3. 批量确认在后台核对：星号、废标、资格三类不许批量确认（防止漏看），带未解析引用的条目须单独写明核对结果。
# 分类只用于展示和批量确认门禁；条款原有的 category / volume 不改。

from __future__ import annotations

import re
from typing import Any

from .domain import DomainError, Principal, iso_time

CATEGORIES: list[tuple[str, str]] = [
    ("basic", "项目基本信息"), ("qualification", "资格要求"), ("scoring", "评分办法与评分项"),
    ("disqualification", "废标与无效标条款"), ("star", "星号实质性条款"), ("technical", "技术服务要求"),
    ("sla", "SLA 要求"), ("format", "投标文件格式要求"), ("timeline", "时间节点"), ("deposit", "保证金"),
]
LABELS = dict(CATEGORIES)
INDIVIDUAL = {"star", "disqualification", "qualification"}  # 不允许批量确认（§5.2.2 规则 3）

STAR = re.compile(r"[★▲]|^\s*\*|实质性(要求|条款|响应)|不得偏离|不允许偏离|必须满足")
DISQUALIFY = re.compile(r"废标|无效投标|无效响应|无效标|否决|视为无效|作无效|按无效|无效处理|不予受理|不予接受")
SLA = re.compile(r"7\s*[×xX*]\s*24|响应时[间限]|到场时[间限]|恢复时[间限]|故障(分级|等级)|一级故障|二级故障|SLA", re.I)
FORMAT = re.compile(r"字体|字号|页边距|装订|密封|正本|副本|签字盖章|加盖公章|投标文件(格式|组成|编制)|目录|页码|暗标")
DEPOSIT = re.compile(r"保证金")
TIMELINE_FACTS = {"投标截止时间", "开标时间"}
DEPOSIT_FACTS = {"投标保证金"}
SLA_FACTS = {"响应时间"}


def requirement_category(row: dict) -> str:
    text = str(row.get("text") or "")
    category = row.get("category")
    kind = row.get("section_kind")
    if category == "star" or STAR.search(text):
        return "star"
    if category == "disqualification" or DISQUALIFY.search(text):
        return "disqualification"
    if category == "qualification" or kind == "qualification":
        return "qualification"
    if category in ("scoring", "score") or kind == "scoring":
        return "scoring"
    if category == "sla" or SLA.search(text):
        return "sla"
    if kind == "format" or FORMAT.search(text):
        return "format"
    if DEPOSIT.search(text):
        return "deposit"
    return "technical"


def fact_category(fact: dict) -> str:
    key = fact.get("key")
    if key in TIMELINE_FACTS:
        return "timeline"
    if key in DEPOSIT_FACTS:
        return "deposit"
    if key in SLA_FACTS or fact.get("sla_var_key"):
        return "sla"
    return "basic"


def _scoring_groups(rows: list[dict]) -> list[dict]:
    """评分项 → 得分要点：同一评分项（章节路径的最后一级）下的条目作为要点。"""
    groups: dict[str, dict] = {}
    for row in rows:
        path = list(row.get("section_path") or [])
        name = path[-1] if path else "评分项"
        group = groups.setdefault(name, {"name": name, "score": None, "ids": [], "pending": 0})
        group["ids"].append(row["id"])
        group["pending"] += row.get("status") == "pending"
        if isinstance(row.get("score"), (int, float)):
            group["score"] = (group["score"] or 0) + row["score"]
    return list(groups.values())


def review(workflow: dict, facts: list[dict], threshold: float = 0.8) -> dict:
    rows = [r for r in workflow.get("requirements", {}).values() if not r.get("out_of_scope")]
    by_id = {r["id"]: requirement_category(r) for r in rows}
    fact_by_id = {f["id"]: fact_category(f) for f in facts}
    tree = []
    for no, (key, label) in enumerate(CATEGORIES, start=1):
        members = [r for r in rows if by_id[r["id"]] == key]
        fact_members = [f for f in facts if fact_by_id[f["id"]] == key]
        item = {"no": no, "key": key, "label": label,
                "requirements": len(members), "facts": len(fact_members),
                "total": len(members) + len(fact_members),
                "pending": sum(r["status"] == "pending" for r in members) + sum(f["status"] in ("pending", "needs_review") for f in fact_members),
                "batch_allowed": key not in INDIVIDUAL}
        if key == "scoring":
            item["groups"] = _scoring_groups(members)
        tree.append(item)
    return {"categories": tree, "requirement_categories": by_id, "fact_categories": fact_by_id,
            "gates": gates(workflow, rows, facts, by_id, threshold), "confidence_threshold": threshold}


def gates(workflow: dict, rows: list[dict], facts: list[dict], by_id: dict[str, str], threshold: float = 0.8) -> list[dict]:
    """确认解析结果的前提（§5.2.2 规则 7），与后台 confirm_parse 的核对一致；blocking=False 的只提示。"""
    def pending_in(keys):
        return sum(1 for r in rows if r["status"] == "pending" and by_id[r["id"]] in keys)

    conflicts = sum(1 for c in workflow.get("conflicts", {}).values() if c.get("status") != "resolved")
    omissions = sum(1 for h in (workflow.get("post_process") or {}).get("hits", {}).values() if h.get("status") == "open")
    references = sum(1 for r in rows if r.get("reference_status") == "unresolved" and r["status"] != "rejected")
    from .parse_quality import low_confidence, unresolved_unreadable
    unreadable = sum(1 for item in [*rows, *facts] if unresolved_unreadable(item))
    low = sum(1 for item in [*rows, *facts] if item.get("status") == "pending" and low_confidence(item, threshold))
    items = [
        ("CONFLICTS_PENDING", "事实冲突待选定", conflicts, True),
        ("OMISSIONS_PENDING", "疑似遗漏未处理", omissions, True),
        ("STAR_PENDING", "星号条款待逐条确认", pending_in({"star"}), True),
        ("DISQUALIFICATION_PENDING", "废标条款待逐条确认", pending_in({"disqualification"}), True),
        ("QUALIFICATION_PENDING", "资格要求待逐条确认", pending_in({"qualification"}), True),
        ("REQUIREMENTS_PENDING", "其他条款待确认", pending_in(set(LABELS) - INDIVIDUAL), True),
        ("FACTS_PENDING", "项目事实待核对", sum(1 for f in facts if f.get("status") == "pending"), True),
        ("REQUIREMENTS_EMPTY", "还没有抽取到条款", 0 if rows else 1, True),
        ("UNREADABLE_PENDING", "原文不可读待对照原页补录", unreadable, True),
        ("LOW_CONFIDENCE", f"置信度低于 {threshold:g} 待人工核对（只提示）", low, False),
        ("REFERENCES_UNRESOLVED", "引用未解析（确认条目时写明人工核对结果）", references, False),
    ]
    return [{"code": code, "label": label, "count": count, "blocking": blocking, "ok": count == 0}
            for code, label, count, blocking in items]


class ParseReviewMixin:
    """挂在 WorkflowService 上：读取分类树与闸门，批量确认。"""

    def parse_review(self, principal: Principal, project_id: str) -> dict:
        from .generation_context import project_facts
        state = self.repository.read()
        self.demo._project(state, principal, project_id)
        workflow = self._workflow(state, project_id)
        facts = [f for f in project_facts(state, project_id) if f.get("source_type", "parsed") == "parsed" and not f.get("sla_var_key")]
        from .company_settings import parse_confidence_threshold
        result = review(workflow, facts, parse_confidence_threshold(state, self.demo._project(state, principal, project_id).company_id))
        result["can_confirm"] = all(g["ok"] for g in result["gates"] if g["blocking"])
        result["parse_confirmed"] = bool(workflow.get("parse_confirmed"))
        return result

    def batch_confirm_requirements(self, principal: Principal, project_id: str, payload: dict,
                                   expected: str | None, key: str | None):
        ids = list(dict.fromkeys(payload.get("requirement_ids") or []))
        if not ids:
            raise DomainError(422, "VALIDATION_ERROR", "请选择要批量确认的条目。")

        def operation(state, project, workflow):
            from .project_access import require_lead
            require_lead(state, principal, project_id)
            rows = []
            for identity in ids:
                row = workflow["requirements"].get(identity)
                if row is None:
                    raise DomainError(404, "NOT_FOUND", "所选条款不存在或不属于本项目。")
                rows.append(row)
            individual = [r["id"] for r in rows if requirement_category(r) in INDIVIDUAL]
            if individual:
                raise DomainError(409, "REQUIREMENT_NOT_READY", "星号条款、废标条款和资格要求必须逐条确认，不能批量确认。",
                                  {"requirement_ids": individual})
            from .parse_quality import unresolved_unreadable
            unreadable = [r["id"] for r in rows if unresolved_unreadable(r)]
            if unreadable:
                raise DomainError(409, "REQUIREMENT_NOT_READY", "原文不可读的条目须对照原页补录后逐条确认，不能批量确认。",
                                  {"requirement_ids": unreadable})
            references = [r["id"] for r in rows if r.get("reference_status") == "unresolved"]
            if references:
                raise DomainError(409, "REFERENCE_REASON_REQUIRED", "含未解析引用的条目须逐条确认并写明人工核对结果。",
                                  {"requirement_ids": references})
            now = iso_time(self.demo._now())
            confirmed = []
            for row in rows:
                if row["status"] == "pending":
                    row.update(status="confirmed", confirmed_by=principal.user.id, confirmed_by_name=principal.user.name,
                               confirmed_at=now)
                    confirmed.append(row["id"])
            if confirmed:
                workflow["parse_confirmed"] = False
                workflow["plan_confirmed"] = False
            return {"confirmed_ids": confirmed}

        return self._write(principal, project_id, "requirements.batch_confirm", payload, expected, key, operation)
