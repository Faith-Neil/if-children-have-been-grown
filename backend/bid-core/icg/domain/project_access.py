# 为什么有这个文件：统一核对项目成员、项目负责人、分册负责人和本节编写人的实际权限。
# 它解决什么问题：公司经理身份不能冒充任何项目的负责人，旧登录或旧编辑权也不能越过新的分工。

from __future__ import annotations

from dataclasses import asdict

from .domain import DomainError
from .auth_service import is_super_admin

VOLUMES = ("technical", "business")

# 登录角色只有三个。项目负责人是项目成员身份，不是登录角色。
ROLE_PLATFORM_ADMIN = "platform_admin"
ROLE_COMPANY_ADMIN = "company_admin"
ROLE_MEMBER = "member"

# 旧登录角色收成普通用户。集团管理员若没有公司，会话仍因公司范围为空而进不了项目。
ROLE_NORMALIZATION_MAP = {
    "platform_admin": ROLE_PLATFORM_ADMIN,
    "company_admin": ROLE_COMPANY_ADMIN,
    "member": ROLE_MEMBER,
    "group_admin": ROLE_MEMBER,
    "data_admin": ROLE_MEMBER,
    "project_lead": ROLE_MEMBER,
    "manager": ROLE_MEMBER,
    "lead": ROLE_MEMBER,
    "bid_writer": ROLE_MEMBER,
    "editor": ROLE_MEMBER,
    "writer": ROLE_MEMBER,
    "auditor": ROLE_MEMBER,
    "reviewer": ROLE_MEMBER,
    "viewer": ROLE_MEMBER,
    "readonly": ROLE_MEMBER,
}

# 平台管理员不能写投标项目。普通用户是否可写由项目成员身份决定。
READONLY_SYSTEM_ROLES = {
    ROLE_PLATFORM_ADMIN,
}

LEAD_COMPANY_ROLES = {
    ROLE_MEMBER,
    ROLE_COMPANY_ADMIN,
}

WRITER_COMPANY_ROLES = {
    ROLE_MEMBER,
    ROLE_COMPANY_ADMIN,
}


def normalize_role(role: str) -> str:
    """将历史演示角色或别名归一化为标准八角色名称。"""
    return ROLE_NORMALIZATION_MAP.get(role, role)


VOLUME_MODES = {"both": VOLUMES, "technical_only": ("technical",)}


def volumes_for_mode(mode: str | None) -> tuple[str, ...]:
    return VOLUME_MODES.get(mode or "both", VOLUMES)


def project_volume_mode(state, project_id) -> str:
    """项目编写哪些分册：both（技术+商务，导出后合标）或 technical_only（只写技术标，不合标）。存在项目团队记录里。"""
    team = state.project_teams.get(project_id) or {}
    mode = team.get("volume_mode") or "both"
    return mode if mode in VOLUME_MODES else "both"


def project_volumes(state, project_id) -> tuple[str, ...]:
    return volumes_for_mode(project_volume_mode(state, project_id))


def rule_scope(state, project_id, volume):
    """检查与规则的实际范围：只写技术标时“全文”就是技术分册；商务分册不存在。"""
    active = project_volumes(state, project_id)
    if volume == "all":
        return "all" if len(active) > 1 else active[0]
    require_project_volume(state, project_id, volume)
    return volume


def in_scope_workflow(workflow):
    """交给合规规则的工作流视图：去掉“不在本项目范围”的条款（只写技术标时的商务/资格条款）。"""
    rows = workflow.get("requirements") or {}
    if not any(r.get("out_of_scope") for r in rows.values()):
        return workflow
    return {**workflow, "requirements": {k: r for k, r in rows.items() if not r.get("out_of_scope")}}


def require_project_volume(state, project_id, volume):
    """只写技术标的项目里，任何指向商务分册的写入都拒绝，而不是悄悄建出一个商务册。"""
    if volume not in project_volumes(state, project_id):
        from .domain import DomainError
        raise DomainError(404, "NOT_FOUND", "本项目只编写技术标，没有商务分册。")


def initial_team(user_id, volume_mode="both"):
    volumes = volumes_for_mode(volume_mode)
    return {"members": {user_id: {"user_id": user_id, "project_role": "lead", "volumes": list(volumes)}},
            "owners": {volume: user_id for volume in volumes}, "assembly_owner_id": user_id, "handoffs": [],
            "volume_mode": volume_mode if volume_mode in VOLUME_MODES else "both"}


def member(state, project_id, user_id):
    return state.project_teams.get(project_id, {}).get("members", {}).get(user_id)


def _blocks_project(account) -> bool:
    if account is None:
        return True
    return is_super_admin(account) or normalize_role(account.role) == ROLE_PLATFORM_ADMIN


def writable(state, project_id, user_id):
    account, membership = state.accounts.get(user_id), member(state, project_id, user_id)
    if _blocks_project(account):
        return False
    if not (account and membership and account.company_id == state.projects[project_id].company_id):
        return False
    if membership.get("project_role") == "readonly":
        return False
    norm = normalize_role(account.role)
    if norm == ROLE_COMPANY_ADMIN:
        return True
    return bool(norm == ROLE_MEMBER and membership.get("project_role") in ("writer", "lead"))


def lead(state, project_id, user_id):
    account = state.accounts.get(user_id)
    if _blocks_project(account):
        return False
    project = state.projects.get(project_id)
    if account and project and normalize_role(account.role) == ROLE_COMPANY_ADMIN and account.company_id == project.company_id:
        return True
    m = member(state, project_id, user_id)
    return writable(state, project_id, user_id) and m is not None and m.get("project_role") == "lead"


def volume_owner(state, project_id, volume, user_id):
    if _blocks_project(state.accounts.get(user_id)):
        return False
    m = member(state, project_id, user_id)
    return (writable(state, project_id, user_id)
            and m is not None
            and volume in m.get("volumes", [])
            and state.project_teams[project_id].get("owners", {}).get(volume) == user_id)


def chapter_edit(state, chapter, user_id):
    if _blocks_project(state.accounts.get(user_id)):
        return False
    m = member(state, chapter.project_id, user_id)
    if not (writable(state, chapter.project_id, user_id) and m is not None):
        return False
    return (
        lead(state, chapter.project_id, user_id)
        or volume_owner(state, chapter.project_id, chapter.volume, user_id)
        or (chapter.assignee_id == user_id and chapter.volume in m.get("volumes", []))
    )


def chapter_structure(state, chapter, user_id):
    if _blocks_project(state.accounts.get(user_id)):
        return False
    return lead(state, chapter.project_id, user_id) or volume_owner(state, chapter.project_id, chapter.volume, user_id)


def require_same_company(state, principal, project_id):
    project = state.projects.get(project_id)
    if project is None or _blocks_project(principal.user):
        raise DomainError(404, "NOT_FOUND", "未找到有权访问的项目。")
    if principal.user.company_id != project.company_id:
        raise DomainError(403, "FORBIDDEN", "无权跨公司访问其他公司的项目。")


def ensure_not_readonly(principal):
    if _blocks_project(principal.user):
        raise DomainError(403, "FORBIDDEN", "平台管理员不参与投标项目。")
    norm = normalize_role(principal.user.role)
    if norm in READONLY_SYSTEM_ROLES:
        raise DomainError(403, "FORBIDDEN", "只读角色不能执行修改操作。")


def require_lead(state, principal, project_id):
    if _blocks_project(principal.user):
        raise DomainError(404, "NOT_FOUND", "未找到有权访问的项目。")
    project = state.projects.get(project_id)
    if project and principal.user.company_id and principal.user.company_id != project.company_id:
        raise DomainError(403, "FORBIDDEN", "无权跨公司操作其他公司的投标项目。")
    norm = normalize_role(principal.user.role)
    if norm == ROLE_PLATFORM_ADMIN:
        raise DomainError(404, "NOT_FOUND", "未找到有权访问的项目。")
    if not lead(state, project_id, principal.user.id):
        raise DomainError(403, "PROJECT_LEAD_REQUIRED", "此操作须由本项目负责人办理，公司的经理身份不能代替项目分工。")


def require_chapter(state, principal, chapter):
    if _blocks_project(principal.user):
        raise DomainError(404, "NOT_FOUND", "未找到有权访问的项目。")
    project = state.projects.get(chapter.project_id)
    if project and principal.user.company_id and principal.user.company_id != project.company_id:
        raise DomainError(403, "FORBIDDEN", "无权跨公司操作其他公司的章节。")
    norm = normalize_role(principal.user.role)
    if norm == ROLE_PLATFORM_ADMIN:
        raise DomainError(404, "NOT_FOUND", "未找到有权访问的项目。")
    if not chapter_edit(state, chapter, principal.user.id):
        raise DomainError(403, "CHAPTER_EDITOR_REQUIRED", "只有本项目负责人、本册负责人或本节编写人可以编辑、确认或生成本节。")


def require_volume_owner(state, principal, project_id, volume):
    if _blocks_project(principal.user):
        raise DomainError(404, "NOT_FOUND", "未找到有权访问的项目。")
    project = state.projects.get(project_id)
    if project and principal.user.company_id and principal.user.company_id != project.company_id:
        raise DomainError(403, "FORBIDDEN", "无权跨公司操作其他公司的分册。")
    norm = normalize_role(principal.user.role)
    if norm == ROLE_PLATFORM_ADMIN:
        raise DomainError(404, "NOT_FOUND", "未找到有权访问的项目。")
    if not (lead(state, project_id, principal.user.id) or volume_owner(state, project_id, volume, principal.user.id)):
        raise DomainError(403, "VOLUME_OWNER_REQUIRED", "只能调整和批量确认自己负责的分册。")


def require_project_writer(state, principal, project_id):
    if _blocks_project(principal.user):
        raise DomainError(404, "NOT_FOUND", "未找到有权访问的项目。")
    project = state.projects.get(project_id)
    if project and principal.user.company_id and principal.user.company_id != project.company_id:
        raise DomainError(403, "FORBIDDEN", "无权跨公司操作其他公司的投标项目。")
    norm = normalize_role(principal.user.role)
    if norm == ROLE_PLATFORM_ADMIN:
        raise DomainError(404, "NOT_FOUND", "未找到有权访问的项目。")
    if not writable(state, project_id, principal.user.id):
        raise DomainError(403, "PROJECT_WRITER_REQUIRED", "当前公司角色和项目角色只允许查看，不能办理此操作。")


def require_data_admin(state, principal):
    del state
    norm = normalize_role(principal.user.role)
    if norm != ROLE_COMPANY_ADMIN:
        raise DomainError(403, "FORBIDDEN", "此操作须由公司管理员办理。")


def chapter_permissions(state, chapter, user_id):
    if _blocks_project(state.accounts.get(user_id)):
        return {"edit": False, "confirm_plan": False, "generate": False,
                "manage_structure": False, "assign": False, "takeover": False}
    edit, structure = chapter_edit(state, chapter, user_id), chapter_structure(state, chapter, user_id)
    return {"edit": edit, "confirm_plan": edit, "generate": edit,
            "manage_structure": structure, "assign": structure, "takeover": structure}


def project_permissions(state, project_id, user_id):
    if _blocks_project(state.accounts.get(user_id)):
        return {"manage_team": False, "manage_project": False, "manage_structure": False,
                "prepare_sources": False, "manage_sla": False, "confirm_facts": False,
                "edit_facts": False, "check_all": False, "export_internal": False,
                "check_volumes": [], "export_volumes": []}
    is_lead = lead(state, project_id, user_id)
    volumes = [v for v in project_volumes(state, project_id) if is_lead or volume_owner(state, project_id, v, user_id)]
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
                        for volume in project_volumes(state, project_id)],
            "volume_mode": project_volume_mode(state, project_id),
            "assembly_owner_id": team.get("assembly_owner_id"), "handoffs": team.get("handoffs", []),
            "available_accounts": [asdict(a) for a in state.accounts.values()
                                   if a.company_id == state.projects[project_id].company_id]
                                  if lead(state, project_id, user_id) else []}
