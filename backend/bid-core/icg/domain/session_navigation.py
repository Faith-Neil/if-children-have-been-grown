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



# 原8角色的入口矩阵是后续身份适配的共同定义，不代表当前演示身份已经具备这些角色。
# 写作档案遵循PRD具体矩阵：审核人、只读成员不授予；公司统计独立于项目/集团统计。
ROLE_NAVIGATION = {
    "platform_admin": (("platform", "write"), ("platform.audit", "read"), ("jobs", "read")),
    "group_admin": (("workbench", "read"), ("library", "read"), ("knowledge", "read"),
                    ("writing", "read"), ("admin", "read")),
    "company_admin": (("workbench", "write"), ("library", "write"), ("knowledge", "write"),
                      ("writing", "write"), ("statistics", "read"), ("admin", "write"), ("jobs", "read")),
    "data_admin": (("workbench", "read"), ("library", "write"), ("knowledge", "write"),
                   ("writing", "read"), ("jobs", "read")),
    "project_lead": (("workbench", "write"), ("library", "write"), ("knowledge", "write"),
                     ("writing", "read"), ("admin.rules", "read"), ("jobs", "read")),
    "bid_writer": (("workbench", "read"), ("library", "write"), ("knowledge", "write"),
                   ("writing", "read"), ("jobs", "read")),
    "reviewer": (("workbench", "read"), ("library", "read"), ("knowledge", "read"), ("jobs", "read")),
    "readonly": (("workbench", "read"), ("library", "read"), ("knowledge", "read"), ("jobs", "read")),
}

NAVIGATION_PATHS = {
    "workbench": "/workbench", "library": "/library", "knowledge": "/knowledge",
    "writing": "/writing", "statistics": "/statistics", "admin": "/admin",
    "admin.rules": "/admin/rules", "jobs": "/jobs", "platform": "/platform",
    "platform.audit": "/platform/audit", "platform.jobs": "/platform/jobs",
}

PROJECT_READ_ROUTES = tuple("project." + tab for tab in (
    "overview", "tender", "parse", "matrix", "facts", "editor", "manual", "checks", "settings"))


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

    if is_super_admin(user):
        auth_mode = "authenticated"
        role_mode = "rbac-8roles"
        primary_role = "platform_admin"
        roles = ["platform_admin"]
        home_path = "/workbench"
        actions = [
            "projects.read",
            "projects.create",
            "library.read",
            "library.write",
            "sla_templates.read",
            "sla_templates.write",
            "jobs.read",
            "platform.write",
            "admin.write",
        ]
        navigation = [{"route_id": route_id, "path": path, "access": "write"} for route_id, path in NAVIGATION_PATHS.items()]
    else:
        # 所有账号都按正式 8 角色会话处理（旧 manager/editor/viewer 经 ROLE_NORMALIZATION_MAP 归一）。
        if user.role not in ROLE_NORMALIZATION_MAP:
            raise DomainError(403, "SESSION_ROLE_UNSUPPORTED", "当前账号角色尚未接入，请联系管理员。")
        norm_role = normalize_role(user.role)
        auth_mode = "authenticated"
        role_mode = "rbac-8roles"
        primary_role = norm_role
        roles = [norm_role]
        nav_role = "reviewer" if norm_role == "auditor" else ("readonly" if norm_role == "viewer" else norm_role)
        nav_roles = [nav_role]
        home_path = "/platform" if norm_role == "platform_admin" else "/workbench"
        if norm_role == "platform_admin":
            actions = ["jobs.read"]
        else:
            actions = ["projects.read", "library.read", "sla_templates.read", "jobs.read"]
            if norm_role in ("project_lead", "company_admin"):
                actions.extend(("projects.create", "sla_templates.write", "library.write"))
            elif norm_role in ("bid_writer", "data_admin"):
                actions.append("library.write")
                if norm_role == "data_admin":
                    actions.append("sla_templates.write")
        navigation = navigation_for_roles(nav_roles)

    current = Principal(user, principal.session_token)
    allowed_company_ids = (
        sorted(list(set([p.company_id for p in state.projects.values()] + [user.company_id])))
        if is_super_admin(user)
        else [user.company_id]
    )
    result = {
        "auth_mode": auth_mode,
        "role_mode": role_mode,
        "user": {**{k: v for k, v in asdict(user).items() if k not in ("password_hash", "salt")}, "username": user.id, "display_name": user.display_name or user.name, "roles": roles, "primary_role": primary_role},
        "scope": {
            "kind": "system" if is_super_admin(user) else "company",
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
        if (is_super_admin(user)
                or permissions["export_internal"] or permissions["export_volumes"]
                or (team.get("assembly_owner_id") == user.id and (user.role in ("manager", "editor") or user_norm_role in WRITER_COMPANY_ROLES))):
            routes.append("project.export")
        result["project_access"] = {
            "id": project.id, "revision": project.revision, "route_permissions": routes,
            "permissions": permissions,
            "chapters": [{"id": chapter.id, "volume": chapter.volume,
                          "permissions": chapter_permissions(state, chapter, user.id)}
                         for chapter in state.chapters.values() if chapter.project_id == project.id],
        }
    return result
