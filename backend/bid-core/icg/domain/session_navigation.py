# 为什么有这个文件：从真实后台会话读取应用身份、导航入口和最小项目资源权限。
# 它解决什么问题：不让客户端公司或旧登录角色决定范围，并明确三角色兼容阶段与完整PRD权限的差别。

from __future__ import annotations

from dataclasses import asdict
from typing import Iterable

from .domain import DomainError, Principal
from .auth_service import is_super_admin
from .project_access import (
    ROLE_NORMALIZATION_MAP,
    WRITER_COMPANY_ROLES,
    chapter_permissions,
    normalize_role,
    project_permissions,
)



# 三个登录角色的入口。平台超级管理员进入全部界面，并且都可以写。
ROLE_NAVIGATION = {
    "platform_admin": (("workbench", "write"), ("library", "write"), ("knowledge", "write"),
                       ("writing", "write"), ("statistics", "read"), ("admin", "write"),
                       ("admin.rules", "write"), ("jobs", "write"), ("notifications", "read"),
                       ("platform", "write"), ("platform.audit", "write"), ("platform.jobs", "write")),
    "company_admin": (("workbench", "write"), ("library", "write"), ("knowledge", "write"),
                      ("writing", "write"), ("statistics", "read"), ("admin.rules", "write"),
                      ("jobs", "read"), ("notifications", "read")),
    "member": (("workbench", "write"), ("library", "write"), ("knowledge", "read"),
               ("writing", "read"), ("jobs", "read"), ("notifications", "read")),
}

NAVIGATION_PATHS = {
    "workbench": "/workbench", "library": "/library", "knowledge": "/knowledge",
    "writing": "/writing", "statistics": "/statistics", "admin": "/admin",
    "admin.rules": "/admin/rules", "jobs": "/jobs", "platform": "/platform",
    "platform.audit": "/platform/audit", "platform.jobs": "/platform/jobs", "notifications": "/notifications",
}

PROJECT_READ_ROUTES = tuple("project." + tab for tab in (
    "overview", "tender", "analyze", "editor", "export", "settings"))


def navigation_for_roles(roles: Iterable[str]) -> list[dict]:
    """只按明确定义的角色生成入口；该函数不负责授权业务动作或适配身份。"""
    access_by_route = {}
    for role in roles:
        if role not in ROLE_NAVIGATION:
            raise DomainError(403, "SESSION_ROLE_UNSUPPORTED", "当前账号角色尚未接入，请联系管理员。")
        for route_id, access in ROLE_NAVIGATION[role]:
            if access_by_route.get(route_id) != "write":
                access_by_route[route_id] = access
    return [{"route_id": route_id, "path": NAVIGATION_PATHS[route_id], "access": access}
            for route_id, access in access_by_route.items()]


def get_application_session(service, principal: Principal, project_id: str | None = None) -> dict:
    # 与项目权限计算共用同一份真实仓储快照，不使用登录响应或传入Principal的旧账号内容。
    state = service.repository.read()
    user = state.accounts.get(state.sessions.get(principal.session_token, ""))
    if user is None:
        raise DomainError(401, "UNAUTHENTICATED", "请先登录。")
    if not isinstance(user.company_id, str) or not user.company_id.strip():
        raise DomainError(403, "SESSION_SCOPE_UNSUPPORTED", "当前账号的公司范围尚未接入，请联系管理员。")

    if user.role not in ROLE_NORMALIZATION_MAP and not is_super_admin(user):
        raise DomainError(403, "SESSION_ROLE_UNSUPPORTED", "当前账号角色尚未接入，请联系管理员。")
    norm_role = "platform_admin" if is_super_admin(user) else normalize_role(user.role)
    auth_mode = "authenticated"
    role_mode = "rbac-3roles"
    primary_role = norm_role
    roles = [norm_role]
    home_path = "/workbench"
    if norm_role == "platform_admin":
        actions = ["projects.read", "projects.create", "library.read", "library.write",
                   "sla_templates.read", "sla_templates.write", "jobs.read", "admin.write", "platform.write"]
    elif norm_role == "company_admin":
        actions = ["projects.read", "projects.create", "library.read", "library.write",
                   "sla_templates.read", "sla_templates.write", "jobs.read", "admin.write"]
    else:
        actions = ["projects.read", "projects.create", "library.read", "library.write",
                   "sla_templates.read", "jobs.read"]
    navigation = navigation_for_roles([norm_role])

    current = Principal(user, principal.session_token)
    allowed_company_ids = (
        sorted({p.company_id for p in state.projects.values()} | {user.company_id})
        if norm_role == "platform_admin"
        else [user.company_id]
    )
    result = {
        "auth_mode": auth_mode,
        "role_mode": role_mode,
        "user": {**{k: v for k, v in asdict(user).items() if k not in ("password_hash", "salt")}, "username": user.id, "display_name": user.display_name or user.name, "roles": roles, "primary_role": primary_role},
        "scope": {
            "kind": "system" if norm_role == "platform_admin" else "company",
            "active_company_id": user.company_id,
            "allowed_company_ids": allowed_company_ids,
        },
        "navigation": navigation,
        "allowedActions": actions,
        "home_path": home_path,
        "session": {"expires_at": None, "renew_supported": False},
    }
    if project_id is not None:
        project = service._project(state, current, project_id)
        permissions = project_permissions(state, project.id, user.id)
        routes = list(PROJECT_READ_ROUTES)
        team = state.project_teams.get(project.id, {})
        user_norm_role = normalize_role(user.role) if user.role in ROLE_NORMALIZATION_MAP else user.role
        if (norm_role != "platform_admin" and (
                permissions["export_internal"] or permissions["export_volumes"]
                or (team.get("assembly_owner_id") == user.id and user_norm_role in WRITER_COMPANY_ROLES))):
            routes.append("project.export")
        result["project_access"] = {
            "id": project.id, "revision": project.revision, "route_permissions": routes,
            "permissions": permissions,
            "chapters": [{"id": chapter.id, "volume": chapter.volume,
                          "permissions": chapter_permissions(state, chapter, user.id)}
                         for chapter in state.chapters.values() if chapter.project_id == project.id],
        }
    return result
