# 为什么有这个文件：统一核对项目成员、项目负责人、分册负责人和本节编写人的实际权限。
# 它解决什么问题：公司经理身份不能冒充任何项目的负责人，旧登录或旧编辑权也不能越过新的分工。

from __future__ import annotations

from dataclasses import asdict

from .domain import DomainError

VOLUMES = ("technical", "business")

# 标准八角色系统定义 (PRD v1.8 §2.2)
ROLE_PLATFORM_ADMIN = "platform_admin"  # 平台管理员 (整套系统运维、模型/服务登记)
ROLE_GROUP_ADMIN = "group_admin"        # 集团管理员 (集团管理视角，跨公司只读)
ROLE_COMPANY_ADMIN = "company_admin"    # 公司管理员 (公司配置、模型、用户与角色、新建项目)
ROLE_DATA_ADMIN = "data_admin"          # 资料管理员 (资料库与知识库整体维护，不参与项目编写除非加入项目)
ROLE_PROJECT_LEAD = "project_lead"      # 项目负责人 (新建项目、分配成员、确认分册、矩阵、全书定稿)
ROLE_BID_WRITER = "bid_writer"          # 投标编写人 (编写被分配章节、挂接证据、使用助手)
ROLE_AUDITOR = "auditor"                # 审核人 (资料与方案审核，只读视角)
ROLE_VIEWER = "viewer"                  # 只读成员 (公司内项目与资料查看，不能修改)

# 角色别名映射（双向兼容历史 manager / editor / viewer / reviewer / readonly 等）
ROLE_NORMALIZATION_MAP = {
    "manager": ROLE_PROJECT_LEAD,
    "project_lead": ROLE_PROJECT_LEAD,
    "editor": ROLE_BID_WRITER,
    "bid_writer": ROLE_BID_WRITER,
    "viewer": ROLE_VIEWER,
    "readonly": ROLE_VIEWER,
    "auditor": ROLE_AUDITOR,
    "reviewer": ROLE_AUDITOR,
    "platform_admin": ROLE_PLATFORM_ADMIN,
    "group_admin": ROLE_GROUP_ADMIN,
    "company_admin": ROLE_COMPANY_ADMIN,
    "data_admin": ROLE_DATA_ADMIN,
}

# 只读系统角色集合：阻断一切写入修改
READONLY_SYSTEM_ROLES = {
    ROLE_GROUP_ADMIN,
    ROLE_VIEWER,
    ROLE_AUDITOR,
    ROLE_PLATFORM_ADMIN,
}

# 具备项目负责人资质的公司角色
LEAD_COMPANY_ROLES = {
    ROLE_PROJECT_LEAD,
    ROLE_COMPANY_ADMIN,
}

# 具备项目编写资质的公司角色
WRITER_COMPANY_ROLES = {
    ROLE_BID_WRITER,
    ROLE_PROJECT_LEAD,
    ROLE_COMPANY_ADMIN,
    ROLE_DATA_ADMIN,
}


def normalize_role(role: str) -> str:
    """将历史演示角色或别名归一化为标准八角色名称。"""
    return ROLE_NORMALIZATION_MAP.get(role, role)


def initial_team(user_id):
    return {"members": {user_id: {"user_id": user_id, "project_role": "lead", "volumes": list(VOLUMES)}},
            "owners": {volume: user_id for volume in VOLUMES}, "assembly_owner_id": user_id, "handoffs": []}


def member(state, project_id, user_id):
    return state.project_teams.get(project_id, {}).get("members", {}).get(user_id)


def writable(state, project_id, user_id):
    account, membership = state.accounts.get(user_id), member(state, project_id, user_id)
    if not (account and membership and account.company_id == state.projects[project_id].company_id):
        return False
    norm = normalize_role(account.role)
    if norm in READONLY_SYSTEM_ROLES:
        return False
    if membership.get("project_role") == "readonly":
        return False
    # 公司管理员和资料管理员仍须已是项目成员；经理和编写人的分工依项目成员角色判定。
    if norm in (ROLE_COMPANY_ADMIN, ROLE_DATA_ADMIN):
        return True
    return bool(norm in (ROLE_PROJECT_LEAD, ROLE_BID_WRITER)
                and (membership.get("project_role") == "writer"
                     or (membership.get("project_role") == "lead" and norm == ROLE_PROJECT_LEAD)))


def lead(state, project_id, user_id):
    m = member(state, project_id, user_id)
    return writable(state, project_id, user_id) and m is not None and m.get("project_role") == "lead"


def volume_owner(state, project_id, volume, user_id):
    m = member(state, project_id, user_id)
    return (writable(state, project_id, user_id)
            and m is not None
            and volume in m.get("volumes", [])
            and state.project_teams[project_id].get("owners", {}).get(volume) == user_id)


def chapter_edit(state, chapter, user_id):
    m = member(state, chapter.project_id, user_id)
    if not (writable(state, chapter.project_id, user_id) and m is not None):
        return False
    return (
        lead(state, chapter.project_id, user_id)
        or volume_owner(state, chapter.project_id, chapter.volume, user_id)
        or (chapter.assignee_id == user_id and chapter.volume in m.get("volumes", []))
    )


def chapter_structure(state, chapter, user_id):
    return lead(state, chapter.project_id, user_id) or volume_owner(state, chapter.project_id, chapter.volume, user_id)


def require_same_company(state, principal, project_id):
    project = state.projects.get(project_id)
    if project is None:
        raise DomainError(404, "NOT_FOUND", "未找到有权访问的项目。")
    if principal.user.company_id != project.company_id:
        raise DomainError(403, "FORBIDDEN", "无权跨公司访问其他公司的项目。")


def ensure_not_readonly(principal):
    norm = normalize_role(principal.user.role)
    if norm in READONLY_SYSTEM_ROLES:
        raise DomainError(403, "FORBIDDEN", "只读角色不能执行修改操作。")


def require_lead(state, principal, project_id):
    project = state.projects.get(project_id)
    if project and principal.user.company_id and principal.user.company_id != project.company_id:
        raise DomainError(403, "FORBIDDEN", "无权跨公司操作其他公司的投标项目。")
    norm = normalize_role(principal.user.role)
    if norm in (ROLE_GROUP_ADMIN, ROLE_VIEWER):
        raise DomainError(403, "FORBIDDEN", "只读或跨公司角色不允许执行写入操作。")
    if not lead(state, project_id, principal.user.id):
        raise DomainError(403, "PROJECT_LEAD_REQUIRED", "此操作须由本项目负责人办理，公司的经理身份不能代替项目分工。")


def require_chapter(state, principal, chapter):
    project = state.projects.get(chapter.project_id)
    if project and principal.user.company_id and principal.user.company_id != project.company_id:
        raise DomainError(403, "FORBIDDEN", "无权跨公司操作其他公司的章节。")
    norm = normalize_role(principal.user.role)
    if norm in (ROLE_GROUP_ADMIN, ROLE_VIEWER):
        raise DomainError(403, "FORBIDDEN", "只读或跨公司角色不允许执行写入操作。")
    if not chapter_edit(state, chapter, principal.user.id):
        raise DomainError(403, "CHAPTER_EDITOR_REQUIRED", "只有本项目负责人、本册负责人或本节编写人可以编辑、确认或生成本节。")


def require_volume_owner(state, principal, project_id, volume):
    project = state.projects.get(project_id)
    if project and principal.user.company_id and principal.user.company_id != project.company_id:
        raise DomainError(403, "FORBIDDEN", "无权跨公司操作其他公司的分册。")
    norm = normalize_role(principal.user.role)
    if norm in (ROLE_GROUP_ADMIN, ROLE_VIEWER):
        raise DomainError(403, "FORBIDDEN", "只读或跨公司角色不允许执行写入操作。")
    if not (lead(state, project_id, principal.user.id) or volume_owner(state, project_id, volume, principal.user.id)):
        raise DomainError(403, "VOLUME_OWNER_REQUIRED", "只能调整和批量确认自己负责的分册。")


def require_project_writer(state, principal, project_id):
    project = state.projects.get(project_id)
    if project and principal.user.company_id and principal.user.company_id != project.company_id:
        raise DomainError(403, "FORBIDDEN", "无权跨公司操作其他公司的投标项目。")
    norm = normalize_role(principal.user.role)
    if norm in (ROLE_GROUP_ADMIN, ROLE_VIEWER):
        raise DomainError(403, "FORBIDDEN", "只读或跨公司角色不允许执行写入操作。")
    if not writable(state, project_id, principal.user.id):
        raise DomainError(403, "PROJECT_WRITER_REQUIRED", "当前公司角色和项目角色只允许查看，不能办理此操作。")


def require_data_admin(state, principal):
    norm = normalize_role(principal.user.role)
    if norm not in (ROLE_DATA_ADMIN, ROLE_COMPANY_ADMIN):
        raise DomainError(403, "FORBIDDEN", "此操作须由资料管理员或公司管理员办理。")


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
