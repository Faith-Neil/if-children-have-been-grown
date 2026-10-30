# 为什么有这个文件：任务与模型对应表（PRD v1.8 §6.4、§6.5、§5.10.5 A-10；APP-M2-T040）。
# 它解决什么问题：
# 1. 公司管理员为每类模型任务指定首选模型和备用模型：章节长文写作（含定位修正、整章建议）、对话助手问答、对话助手修改样例
#    （章节模型评审目前不调用模型，不列入）；
# 2. 保存时按降级口径核对：首选为本地的，备用只能是本地；“只能本地”的任务首选和备用都必须本地；备用不能与首选相同；
#    只能选本公司的真实模型配置；
# 3. 取模型的顺序：项目负责人为项目单独绑定的模型 → 本公司该任务的首选 → 本公司默认模型；备用取任务表的，没填时取模型配置自带的；
#    敏感项目运行时仍由各任务的本地模型门禁核对，备用不满足本地要求时不用。

from __future__ import annotations

from typing import Any

from .domain import DemoState, DomainError, Principal, iso_time, new_id

STORE = "task_model_routes"
# 任务代码 → (名称, 是否只能本地)
TASKS: dict[str, tuple[str, bool]] = {
    "chapter_generation": ("章节长文写作（含定位修正、整章建议）", False),
    "assistant_qa": ("对话助手问答", False),
    "assistant_suggest": ("对话助手修改样例", False),
}


def routes(state: DemoState, company_id: str) -> dict[str, dict]:
    return ((state.service_stores.get(STORE) or {}).get(company_id) or {}).get("routes") or {}


def problems(state: DemoState, company_id: str, task: str, primary_id: str | None, fallback_id: str | None) -> list[str]:
    name, local_only = TASKS[task]
    found = []
    primary = state.model_configs.get(primary_id) if primary_id else None
    fallback = state.model_configs.get(fallback_id) if fallback_id else None
    for label, ident, cfg in (("首选", primary_id, primary), ("备用", fallback_id, fallback)):
        if ident and (cfg is None or cfg.company_id != company_id):
            found.append(f"{name}：{label}模型不存在或不属于本公司")
        elif cfg is not None and cfg.provider == "demo":
            found.append(f"{name}：{label}模型必须是真实模型")
    if fallback_id and not primary_id:
        found.append(f"{name}：先选首选模型，再选备用模型")
    if primary_id and fallback_id and primary_id == fallback_id:
        found.append(f"{name}：备用模型不能与首选相同")
    if local_only and ((primary and not primary.is_local) or (fallback and not fallback.is_local)):
        found.append(f"{name}：只能使用本地模型")
    if primary and fallback and primary.is_local and not fallback.is_local:
        found.append(f"{name}：首选为本地模型时，备用只能是本地模型（不改走云端）")
    return found


def public(state: DemoState, company_id: str) -> dict:
    saved = (state.service_stores.get(STORE) or {}).get(company_id) or {}
    current = saved.get("routes") or {}
    return {"tasks": [{"task": code, "name": name, "local_only": local_only,
                       "primary_config_id": (current.get(code) or {}).get("primary_config_id"),
                       "fallback_config_id": (current.get(code) or {}).get("fallback_config_id")}
                      for code, (name, local_only) in TASKS.items()],
            "revision": saved.get("revision", 0), "updated_by": saved.get("updated_by"), "updated_at": saved.get("updated_at")}


def resolve(state: DemoState, company_id: str, task: str | None) -> tuple[Any, Any] | None:
    """（首选配置，备用配置或 None）；该任务没配首选时返回 None。"""
    if not task:
        return None
    route = routes(state, company_id).get(task) or {}
    primary = state.model_configs.get(route.get("primary_config_id") or "")
    if primary is None or primary.company_id != company_id:
        return None
    fallback = state.model_configs.get(route.get("fallback_config_id") or "")
    if fallback is not None and problems(state, company_id, task, primary.id, fallback.id):
        fallback = None  # 配置事后被改得不合规时不用
    return primary, fallback


class TaskModelRouteService:
    def __init__(self, demo: Any) -> None:
        self.demo = demo

    @staticmethod
    def _admin(principal: Principal) -> None:
        from .auth_service import is_super_admin
        from .project_access import normalize_role
        if not (is_super_admin(principal) or normalize_role(principal.user.role) in ("company_admin", "platform_admin")):
            raise DomainError(403, "FORBIDDEN", "任务与模型对应表只能由公司管理员（或平台管理员）修改。")

    def get(self, principal: Principal) -> dict:
        return public(self.demo.repository.read(), principal.user.company_id)

    def update(self, principal: Principal, payload: dict, expected: int | None) -> dict:
        self._admin(principal)
        company = principal.user.company_id

        def write(state: DemoState):
            saved = state.service_stores.setdefault(STORE, {}).setdefault(company, {"routes": {}, "revision": 0})
            if expected is not None and expected != saved.get("revision", 0):
                raise DomainError(409, "REVISION_CONFLICT", "任务与模型对应表已被他人修改，请刷新后再保存。",
                                  {"current_revision": saved.get("revision", 0)})
            issues, updated = [], dict(saved.get("routes") or {})
            for item in payload["routes"]:
                task = item["task"]
                if task not in TASKS:
                    issues.append(f"不认识的任务：{task}")
                    continue
                primary, fallback = item.get("primary_config_id") or None, item.get("fallback_config_id") or None
                issues += problems(state, company, task, primary, fallback)
                updated[task] = {"primary_config_id": primary, "fallback_config_id": fallback}
            if issues:
                raise DomainError(422, "VALIDATION_ERROR", "；".join(issues))
            saved.update(routes=updated, revision=saved.get("revision", 0) + 1, updated_by=principal.user.id,
                         updated_at=iso_time(self.demo._now()))
            state.audit.append({"id": new_id("event"), "action": "task_model_routes.update", "actor_id": principal.user.id,
                                "company_id": company, "at": saved["updated_at"], "details": {"routes": updated}})
            return public(state, company)
        return self.demo.repository.transaction(write)
