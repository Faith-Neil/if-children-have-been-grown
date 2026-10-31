# 为什么有这个文件：R19 关联投标冲突（APP-M2-T096 / PRD v1.8 §5.1.2 业务规则 2、§8.3、§5.8.1 R19）。
# 它解决什么问题：集团内存在控股、管理关系的公司投同一标段，相关投标均无效（《招标投标法实施条例》第三十四条）。
# 立项（填写或修改招标编号、项目名称）时按招标编号 + 标段在平台内其他公司的项目里查找；没有编号时按“招标人 + 项目名称”近似匹配。
# 找到时只告诉对方公司名称，不透露对方项目任何内容；项目负责人须填写说明确认无上述关系才能继续，全程留痕并通知集团管理员。
# 导出前全文检查再核一次（规则 R19，警告）。本平台按集团私有化部署，平台内的公司都视为同一集团。

from __future__ import annotations

import re
import unicodedata
from typing import Any

from .domain import DomainError, Principal, iso_time

STATUTE = ("依据《招标投标法实施条例》第三十四条和《政府采购法实施条例》第十八条，存在控股、管理关系或单位负责人为同一人的"
           "不同单位不得参加同一标段投标。")
MESSAGES = {
    "exact": "集团内另一家公司已对同一标段立项。" + STATUTE,
    "approximate": "集团内另一家公司可能已对同一项目立项（招标编号或标段缺失，按招标人与项目名称近似判断）。" + STATUTE,
}
MIN_REASON = 5
NUMBER_KEYS = ("招标编号", "项目编号", "采购编号")
LOT_KEYS = ("标段", "标段编号", "包号", "采购包")
TENDERER_KEYS = ("采购人", "招标人")

_DROP = re.compile(r"[\s\W_]+", re.UNICODE)


def normalize(text: Any) -> str:
    """全角转半角、去空白与标点、英文小写：同一编号写法不同也能比对。"""
    value = unicodedata.normalize("NFKC", str(text or "")).lower()
    return _DROP.sub("", value)


def _fact(workflow: dict, keys: tuple[str, ...]) -> str:
    facts = list((workflow.get("facts") or {}).values())
    for status in ("confirmed", None):
        for key in keys:
            for fact in facts:
                if fact.get("key") == key and (status is None or fact.get("status") == status) and str(fact.get("value") or "").strip():
                    return str(fact["value"])
    return ""


def project_keys(state: Any, project: Any) -> dict:
    workflow = state.workflows.get(project.id) or {}
    return {
        "number": normalize(project.tender_number or _fact(workflow, NUMBER_KEYS)),
        "lot": normalize(_fact(workflow, LOT_KEYS)),
        "tenderer": normalize(_fact(workflow, TENDERER_KEYS)),
        "name": normalize(project.name),
    }


def match(a: dict, b: dict) -> str | None:
    if a["number"] and b["number"]:
        if a["number"] != b["number"]:
            return None
        if a["lot"] == b["lot"]:
            return "exact"
        return "approximate" if not a["lot"] or not b["lot"] else None
    if a["tenderer"] and b["tenderer"] and a["name"] and b["name"]:
        return "approximate" if a["tenderer"] == b["tenderer"] and a["name"] == b["name"] else None
    return None


def _company_name(state: Any, company_id: str) -> str:
    from .company_settings import company_display_name
    return company_display_name(state, company_id)


def conflicts(state: Any, project: Any) -> dict:
    """平台内其他公司的在投项目中与本项目匹配的；只返回对方公司，不返回对方项目。"""
    mine = project_keys(state, project)
    found: dict[str, str] = {}
    for other in state.projects.values():
        if (other.id == project.id or other.company_id == project.company_id or other.company_id in ("", "system")
                or getattr(other, "is_deleted", False) or getattr(other, "is_archived", False)):
            continue
        kind = match(mine, project_keys(state, other))
        if kind and found.get(other.company_id) != "exact":
            found[other.company_id] = kind
    companies = sorted(({"company_id": cid, "company_name": _company_name(state, cid), "match": kind}
                        for cid, kind in found.items()), key=lambda c: c["company_name"])
    overall = "exact" if any(c["match"] == "exact" for c in companies) else ("approximate" if companies else None)
    return {"match": overall, "companies": companies}


def acknowledged(workflow: dict, found: dict) -> dict | None:
    """已确认的说明覆盖当前全部冲突公司时返回该说明；出现新的冲突公司须重新确认。"""
    ack = workflow.get("related_bid_ack")
    if not ack or not found["companies"]:
        return None
    covered = set(ack.get("company_ids") or [])
    return ack if {c["company_id"] for c in found["companies"]} <= covered else None


def public_details(found: dict) -> dict:
    return {"match": found["match"], "companies": [c["company_name"] for c in found["companies"]],
            "message": MESSAGES.get(found["match"] or "", ""), "statute": STATUTE}


def require_ack(state: Any, principal: Principal, project: Any, workflow: dict, reason: str | None, now: float) -> dict | None:
    """有冲突且未确认时：没有说明则 409 RELATED_BID_CONFLICT；有说明则记录确认、留痕并通知集团管理员。"""
    found = conflicts(state, project)
    if not found["companies"] or acknowledged(workflow, found):
        return None
    if not reason or len(reason.strip()) < MIN_REASON:
        raise DomainError(409, "RELATED_BID_CONFLICT", MESSAGES[found["match"]], details=public_details(found))
    return record_ack(state, principal, project, workflow, found, reason.strip(), now)


def record_ack(state: Any, principal: Principal, project: Any, workflow: dict, found: dict, reason: str, now: float) -> dict:
    from .project_access import lead, normalize_role
    if not lead(state, project.id, principal.user.id) and normalize_role(principal.user.role) != "company_admin":
        raise DomainError(403, "PROJECT_LEAD_REQUIRED", "关联投标冲突只能由项目负责人确认。")
    record = {"company_ids": [c["company_id"] for c in found["companies"]],
              "company_names": [c["company_name"] for c in found["companies"]], "match": found["match"],
              "reason": reason, "by": principal.user.id, "by_name": principal.user.name, "at": iso_time(now)}
    workflow["related_bid_ack"] = record
    workflow.setdefault("related_bid_history", []).append(record)
    from .notifications import notify
    group_admins = [a.id for a in state.accounts.values() if normalize_role(a.role) == "group_admin"
                    and getattr(a, "status", "active") == "active"]
    own = _company_name(state, project.company_id)
    notify(state, group_admins, "related_bid_conflict", "关联投标冲突已确认",
           f"{own} 的项目负责人确认与 {'、'.join(record['company_names'])} 无控股、管理关系或单位负责人相同，继续投标；说明：{reason}",
           now=iso_time(now), project_id=project.id, target_id="settings")
    return record


def status(state: Any, project: Any) -> dict:
    workflow = state.workflows.get(project.id) or {}
    found = conflicts(state, project)
    ack = acknowledged(workflow, found)
    return {**public_details(found), "needs_ack": bool(found["companies"]) and ack is None,
            "acknowledged": {k: ack[k] for k in ("company_names", "match", "reason", "by_name", "at")} if ack else None}
