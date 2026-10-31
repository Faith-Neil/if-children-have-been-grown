# 为什么有这个文件：口令登录的安全规则（APP-M2-T260 / PRD v1.8 §5.12.1、Q28；字典 v1.9 sys_user.must_change_password）。
# 它解决什么问题：首次登录与被重置后必须先改密、改密前只能改密与注销（后端判定）；停用公司的账号不能登录；
# 账号不存在、密码错误、账号停用的提示相同；密码规则按账号所属公司的安全设置校验；锁定到期自动解锁。

from __future__ import annotations

import os
import time
from dataclasses import replace
from typing import Any

from .auth_service import CHAR_CLASS_LABELS, hash_password, password_problems, verify_password
from .company_settings import (
    PLATFORM_PASSWORD_CHAR_CLASSES_LOWER_BOUND,
    PLATFORM_PASSWORD_CHAR_CLASSES_UPPER_BOUND,
    PLATFORM_PASSWORD_MIN_LENGTH_LOWER_BOUND,
    PLATFORM_PASSWORD_MIN_LENGTH_UPPER_BOUND,
)
from .domain import DomainError, Principal
from .project_access import ROLE_GROUP_ADMIN, ROLE_PLATFORM_ADMIN, normalize_role

# PRD §5.12.1 业务规则 2：不区分“账号不存在”和“密码错误”。账号停用也用同一句（T260 卡）。
LOGIN_FAILED_MESSAGE = "账号或密码错误，请核实后重试。"
COMPANY_DISABLED_MESSAGE = "所属公司已停用，请联系平台管理员。"
PASSWORD_CHANGE_REQUIRED_MESSAGE = "首次登录或密码被重置后，须先修改密码才能使用系统。"

# PRD §5.12.1 状态：锁定 login_lock_minutes（示例 15 分钟）后自动解锁。平台设置页尚未建，先用部署变量。
DEFAULT_LOGIN_LOCK_MINUTES = 15

# 须改密的会话只能调用这几个接口（T260 卡“权限与失败”）。
PASSWORD_CHANGE_ALLOWED: frozenset[tuple[str, str]] = frozenset({
    ("POST", "/api/v1/auth/password"),
    ("GET", "/api/v1/auth/password-policy"),
    ("POST", "/api/v1/auth/logout"),
})


def login_lock_minutes() -> int:
    raw = os.environ.get("ICG_LOGIN_LOCK_MINUTES", "")
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_LOGIN_LOCK_MINUTES
    return value if 1 <= value <= 1440 else DEFAULT_LOGIN_LOCK_MINUTES


def company_record(state: Any, company_id: str) -> dict:
    return dict((state.service_stores.get("companies") or {}).get(company_id) or {})


def company_disabled(state: Any, company_id: str) -> bool:
    return company_record(state, company_id).get("status") == "disabled"


def is_platform_account(account: Any) -> bool:
    """平台管理员、集团管理员等平台级账号按平台默认密码规则执行（PRD §5.12.1 规则 3）。"""
    role = normalize_role(getattr(account, "role", "") or "")
    return getattr(account, "company_id", "") in ("", "system") or role in (ROLE_PLATFORM_ADMIN, ROLE_GROUP_ADMIN)


def _bounded(value: Any, lower: int, upper: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        return lower
    return max(lower, min(upper, value))


def policy_for(state: Any, account: Any) -> dict:
    """当前适用的密码规则：公司账号取本公司安全设置（不低于平台默认），平台级账号取平台默认。"""
    if is_platform_account(account):
        min_length, min_classes, scope = PLATFORM_PASSWORD_MIN_LENGTH_LOWER_BOUND, PLATFORM_PASSWORD_CHAR_CLASSES_LOWER_BOUND, "platform"
    else:
        stored = (state.service_stores.get("company_settings") or {}).get(account.company_id) or {}
        min_length = _bounded(stored.get("password_min_length"), PLATFORM_PASSWORD_MIN_LENGTH_LOWER_BOUND,
                              PLATFORM_PASSWORD_MIN_LENGTH_UPPER_BOUND)
        min_classes = _bounded(stored.get("password_min_char_classes"), PLATFORM_PASSWORD_CHAR_CLASSES_LOWER_BOUND,
                               PLATFORM_PASSWORD_CHAR_CLASSES_UPPER_BOUND)
        scope = "company"
    return {
        "min_length": min_length,
        "min_char_classes": min_classes,
        "char_classes": [label for _key, label in CHAR_CLASS_LABELS],
        "scope": scope,
    }


def require_strong_password(state: Any, account: Any, password: str, *, field: str,
                            current_password: str | None = None) -> None:
    policy = policy_for(state, account)
    problems = password_problems(password, policy["min_length"], policy["min_char_classes"])
    if current_password is not None and password == current_password:
        problems.append("不能与当前密码相同")
    if problems:
        raise DomainError(422, "PASSWORD_WEAK", "新密码不符合密码规则：" + "；".join(problems),
                          details={"field": field, "problems": problems, "policy": policy})


def max_login_failures(state: Any, account: Any) -> int:
    stored = (state.service_stores.get("company_settings") or {}).get(getattr(account, "company_id", "")) or {}
    value = stored.get("max_login_attempts")
    return value if isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= 5 else 5


def lock_expired(account: Any, now: float) -> bool:
    """连续失败锁定满 login_lock_minutes 后到期。没有锁定时间的旧锁定只能由管理员解锁。"""
    locked_at = getattr(account, "locked_at", None)
    return bool(getattr(account, "is_locked", False)) and isinstance(locked_at, (int, float)) \
        and now - locked_at >= login_lock_minutes() * 60


def locked_message(account: Any, now: float) -> str:
    locked_at = getattr(account, "locked_at", None)
    if isinstance(locked_at, (int, float)):
        remaining = max(1, int((locked_at + login_lock_minutes() * 60 - now + 59) // 60))
        return f"账号已锁定，请 {remaining} 分钟后重试或联系公司管理员。"
    return "账号已锁定，请联系公司管理员解锁。"


def require_password_changed(principal: Principal, method: str, path: str) -> None:
    """须改密的会话除改密、读密码规则和注销外一律拒绝；由后端判定，不靠页面跳转。"""
    if getattr(principal.user, "must_change_password", False) and (method.upper(), path) not in PASSWORD_CHANGE_ALLOWED:
        raise DomainError(403, "PASSWORD_CHANGE_REQUIRED", PASSWORD_CHANGE_REQUIRED_MESSAGE,
                          details={"change_password": "/api/v1/auth/password"})


def _audit(state: Any, action: str, user_id: str, **extra: Any) -> None:
    from .security_audit import record
    record(state, action, operator=user_id, user_id=user_id, **extra)


def change_own_password(service: Any, principal: Principal, old_password: str, new_password: str) -> dict:
    """本人修改密码：核对原密码、按适用规则校验新密码；成功后清除须改密标记并注销本人其他会话。"""
    state = service.repository.read()
    account = state.accounts.get(principal.user.id)
    if account is None:
        raise DomainError(401, "UNAUTHENTICATED", "登录已失效，请重新登录。")
    if not (account.password_hash and verify_password(old_password, account.password_hash, account.salt)):
        raise DomainError(422, "OLD_PASSWORD_INCORRECT", "原密码不正确。", details={"field": "old_password"})
    require_strong_password(state, account, new_password, field="new_password", current_password=old_password)
    password_hash, salt = hash_password(new_password)
    now = time.time()

    def write(s: Any) -> dict:
        current = s.accounts.get(account.id)
        if current is None:
            raise DomainError(401, "UNAUTHENTICATED", "登录已失效，请重新登录。")
        s.accounts[account.id] = replace(current, password_hash=password_hash, salt=salt, must_change_password=False,
                                         password_changed_at=now, updated_at=now)
        for token, user_id in list(s.sessions.items()):
            if user_id == account.id and token != principal.session_token:
                del s.sessions[token]
        _audit(s, "user.change_password", account.id, forced=bool(current.must_change_password))
        return {"success": True, "must_change_password": False}

    return service.repository.transaction(write)


def logout(service: Any, principal: Principal) -> dict:
    """注销本次会话：令牌立即作废，记审计（PRD §5.12.1 规则 4）。"""
    def write(s: Any) -> dict:
        if s.sessions.get(principal.session_token) == principal.user.id:
            del s.sessions[principal.session_token]
            _audit(s, "user.logout", principal.user.id)
        return {"success": True}

    return service.repository.transaction(write)


def password_policy_response(service: Any, principal: Principal) -> dict:
    state = service.repository.read()
    account = state.accounts.get(principal.user.id) or principal.user
    return {**policy_for(state, account), "must_change_password": bool(getattr(account, "must_change_password", False))}
