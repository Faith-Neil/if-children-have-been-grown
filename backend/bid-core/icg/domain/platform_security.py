# 为什么有这个文件：平台级账号安全策略的单一真相源（ISSUE-056）。
# 它解决什么问题：密码强度、连续失败锁定与会话超时不再由各公司自行放宽，也不只停留在前端提示；
# 平台管理员保存后，登录、改密、用户创建/重置和会话鉴权都按同一份后端配置强制执行。

from __future__ import annotations

import time
from typing import Any

from pydantic import BaseModel, Field

from .domain import DomainError, Principal
from .auth_service import is_super_admin
from .project_access import ROLE_PLATFORM_ADMIN, normalize_role

STORE_KEY = "platform_security"

DEFAULT_PASSWORD_MIN_LENGTH = 8
DEFAULT_PASSWORD_MIN_CHAR_CLASSES = 3
DEFAULT_MAX_LOGIN_ATTEMPTS = 5
DEFAULT_SESSION_TIMEOUT_MINUTES = 120


class PlatformSecuritySettings(BaseModel):
    password_min_length: int = Field(default=DEFAULT_PASSWORD_MIN_LENGTH, ge=8, le=32)
    password_min_char_classes: int = Field(default=DEFAULT_PASSWORD_MIN_CHAR_CLASSES, ge=3, le=4)
    max_login_attempts: int = Field(default=DEFAULT_MAX_LOGIN_ATTEMPTS, ge=1, le=5)
    session_timeout_minutes: int = Field(default=DEFAULT_SESSION_TIMEOUT_MINUTES, ge=30, le=480)
    updated_at: str | None = None
    updated_by: str | None = None


class UpdatePlatformSecuritySettingsRequest(BaseModel):
    password_min_length: int | None = Field(default=None, ge=8, le=32)
    password_min_char_classes: int | None = Field(default=None, ge=3, le=4)
    max_login_attempts: int | None = Field(default=None, ge=1, le=5)
    session_timeout_minutes: int | None = Field(default=None, ge=30, le=480)


def is_platform_admin(principal: Principal) -> bool:
    return is_super_admin(principal) or normalize_role(principal.user.role) == ROLE_PLATFORM_ADMIN


def require_platform_admin(principal: Principal) -> None:
    if not is_platform_admin(principal):
        raise DomainError(403, "FORBIDDEN", "只有平台管理员可以管理平台安全策略。")


def stored_settings(state: Any) -> dict:
    value = (getattr(state, "service_stores", {}).get(STORE_KEY) or {}).get("global") or {}
    return dict(value) if isinstance(value, dict) else {}


def policy_for_state(state: Any) -> PlatformSecuritySettings:
    try:
        return PlatformSecuritySettings(**stored_settings(state))
    except Exception:
        return PlatformSecuritySettings()


def read_policy(service: Any) -> PlatformSecuritySettings:
    return policy_for_state(service.repository.read())


def update_policy(service: Any, principal: Principal, payload: UpdatePlatformSecuritySettingsRequest) -> PlatformSecuritySettings:
    require_platform_admin(principal)
    current = read_policy(service).model_dump()
    for key, value in payload.model_dump(exclude_unset=True).items():
        if value is not None:
            current[key] = value
    current["updated_by"] = principal.user.id
    current["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    model = PlatformSecuritySettings(**current)

    def write(state: Any) -> None:
        state.service_stores.setdefault(STORE_KEY, {})["global"] = model.model_dump()

    service.repository.transaction(write)
    return model


def session_times(state: Any) -> dict[str, float]:
    raw = (getattr(state, "service_stores", {}).get("session_times") or {}).get("tokens") or {}
    return dict(raw) if isinstance(raw, dict) else {}


def remember_session(state: Any, token: str, at: float | None = None) -> None:
    state.service_stores.setdefault("session_times", {}).setdefault("tokens", {})[token] = float(at if at is not None else time.time())


def forget_session(state: Any, token: str) -> None:
    tokens = state.service_stores.setdefault("session_times", {}).setdefault("tokens", {})
    tokens.pop(token, None)


def session_expired(state: Any, token: str, now: float | None = None) -> bool:
    started = session_times(state).get(token)
    if not isinstance(started, (int, float)):
        # 迁移前旧会话没有可信签发时间；按过期处理并要求重新登录，不能留下绕过窗口。
        return True
    minutes = policy_for_state(state).session_timeout_minutes
    return float(now if now is not None else time.time()) - float(started) > minutes * 60
