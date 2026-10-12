# 为什么有这个文件：统一核对项目成员、项目负责人、分册负责人和本节编写人的实际权限。
# 它解决什么问题：公司经理身份不能冒充任何项目的负责人，旧登录或旧编辑权也不能越过新的分工。

from __future__ import annotations

from dataclasses import asdict

from .domain import DomainError

VOLUMES = ("technical", "business")


def initial_team(user_id):
    return {"members": {user_id: {"user_id": user_id, "project_role": "lead", "volumes": list(VOLUMES)}},
            "owners": {volume: user_id for volume in VOLUMES}, "assembly_owner_id": user_id, "handoffs": []}


def member(state, project_id, user_id):
    return state.project_teams.get(project_id, {}).get("members", {}).get(user_id)


def writable(state, project_id, user_id):
    account, membership = state.accounts.get(user_id), member(state, project_id, user_id)
    if not (account and membership and account.company_id == state.projects[project_id].company_id):
        return False
    # 公司管理员和资料管理员仍须已是项目成员；经理和编辑的原有分工不变。
    if account.role in ("company_admin", "data_admin"):
        return True
    return bool(account.role in ("manager", "editor")
                and (membership["project_role"] == "writer"
                     or membership["project_role"] == "lead" and account.role == "manager"))


def lead(state, project_id, user_id):
    return writable(state, project_id, user_id) and member(state, project_id, user_id)["project_role"] == "lead"


def volume_owner(state, project_id, volume, user_id):
    return (writable(state, project_id, user_id) and volume in member(state, project_id, user_id)["volumes"]
            and state.project_teams[project_id]["owners"].get(volume) == user_id)


def chapter_edit(state, chapter, user_id):
    return writable(state, chapter.project_id, user_id) and (
        lead(state, chapter.project_id, user_id)
        or volume_owner(state, chapter.project_id, chapter.volume, user_id)
        or chapter.assignee_id == user_id and chapter.volume in member(state, chapter.project_id, user_id)["volumes"])


def chapter_structure(state, chapter, user_id):
    return lead(state, chapter.project_id, user_id) or volume_owner(state, chapter.project_id, chapter.volume, user_id)


def require_lead(state, principal, project_id):
    if not lead(state, project_id, principal.user.id):
        raise DomainError(403, "PROJECT_LEAD_REQUIRED", "此操作须由本项目负责人办理，公司的经理身份不能代替项目分工。")


def require_chapter(state, principal, chapter):
    if not chapter_edit(state, chapter, principal.user.id):
        raise DomainError(403, "CHAPTER_EDITOR_REQUIRED", "只有本项目负责人、本册负责人或本节编写人可以编辑、确认或生成本节。")


def chapter_permissions(state, chapter, user_id):
    edit, structure = chapter_edit(state, chapter, user_id), chapter_structure(state, chapter, user_id)
    return {"edit": edit, "confirm_plan": edit, "generate": edit,
            "manage_structure": structure, "assign": structure, "takeover": structure}


def project_permissions(state, project_id, user_id):
    is_lead = lead(state, project_id, user_id)
    volumes = [v for v in VOLUMES if is_lead or volume_owner(state, project_id, v, user_id)]
    return {"manage_team": is_lead, "manage_project": is_lead, "manage_structure": is_lead,
            "prepare_sources": is_lead, "manage_sla": is_lead, "confirm_facts": is_lead,
            "edit_facts": writable(state, project_id, user_id),
            "check_all": is_lead, "export_internal": is_lead,
            "check_volumes": volumes, "export_volumes": volumes}


def public_team(state, project_id, user_id):
    team = state.project_teams[project_id]
    return {"members": [{**item, "name": state.accounts[identity].name, "company_role": state.accounts[identity].role}
                        for identity, item in team["members"].items() if identity in state.accounts],
            "volumes": [{"volume": volume, "owner_id": team["owners"].get(volume),
                         "owner_name": state.accounts[team["owners"][volume]].name if team["owners"].get(volume) in state.accounts else None}
                        for volume in VOLUMES],
            "assembly_owner_id": team.get("assembly_owner_id"), "handoffs": team.get("handoffs", []),
            "available_accounts": [asdict(a) for a in state.accounts.values()
                                   if a.company_id == state.projects[project_id].company_id]
                                  if lead(state, project_id, user_id) else []}
