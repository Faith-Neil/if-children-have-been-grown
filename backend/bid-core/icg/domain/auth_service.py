# 为什么有这个文件：正式账号密码凭据认证服务与密码加盐哈希（PBKDF2-HMAC-SHA256）。
# 它解决什么问题：支持非 demo 正式「账号 + 密码」登录，提供加盐哈希存储、密码核验、Bearer Access Token 签发与全系统超级管理员内置映射。

from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import Any

DEFAULT_SUPER_ADMIN_USERNAME = "admin"
DEFAULT_SUPER_ADMIN_PASSWORD = "X_2026"
DEFAULT_SUPER_ADMIN_NAME = "系统超级管理员"
DEFAULT_SUPER_ADMIN_COMPANY = "system"
DEFAULT_SUPER_ADMIN_ROLE = "platform_admin"

PBKDF2_ITERATIONS = 100_000
HASH_ALGORITHM = "sha256"


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    """使用 PBKDF2-HMAC-SHA256 对密码进行加盐哈希处理，返回 (formatted_hash, salt)。"""
    if salt is None:
        salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac(
        HASH_ALGORITHM,
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS,
    ).hex()
    formatted_hash = f"pbkdf2:sha256:{PBKDF2_ITERATIONS}${salt}${hashed}"
    return formatted_hash, salt


def verify_password(password: str, stored_hash: str, salt: str | None = None) -> bool:
    """核验明文密码与存储的加盐哈希是否一致（使用 constant-time compare 防止时序侧信道攻击）。"""
    if not stored_hash or not password:
        return False
    if stored_hash.startswith("pbkdf2:sha256:"):
        parts = stored_hash.split("$")
        if len(parts) == 3:
            _, s, h = parts
            computed = hashlib.pbkdf2_hmac(
                HASH_ALGORITHM,
                password.encode("utf-8"),
                s.encode("utf-8"),
                PBKDF2_ITERATIONS,
            ).hex()
            return hmac.compare_digest(computed, h)
    if salt:
        computed = hashlib.pbkdf2_hmac(
            HASH_ALGORITHM,
            password.encode("utf-8"),
            salt.encode("utf-8"),
            PBKDF2_ITERATIONS,
        ).hex()
        return hmac.compare_digest(computed, stored_hash)
    return False


def is_super_admin(user_or_principal: Any) -> bool:
    """判定是否为系统级超级管理员（Super Admin，账号为 admin）。"""
    if user_or_principal is None:
        return False
    if isinstance(user_or_principal, str):
        return user_or_principal == DEFAULT_SUPER_ADMIN_USERNAME
    user = getattr(user_or_principal, "user", user_or_principal)
    user_id = getattr(user, "id", None)
    if user_id == DEFAULT_SUPER_ADMIN_USERNAME:
        return True
    return False


def validate_password_strength(password: str, min_length: int = 8, min_classes: int = 3) -> tuple[bool, str]:
    """依据 PRD v1.8 §5.10.2 / Q28 定案核验密码强度：最少8位且至少包含四类字符中的三类。"""
    if not password or len(password) < min_length:
        return False, f"密码长度不能低于平台下限 {min_length} 位。"
    classes = 0
    if any(c.isupper() for c in password):
        classes += 1
    if any(c.islower() for c in password):
        classes += 1
    if any(c.isdigit() for c in password):
        classes += 1
    if any(not c.isalnum() for c in password):
        classes += 1
    if classes < min_classes:
        return False, f"密码至少需包含大写字母、小写字母、数字、特殊符号中的 {min_classes} 类。"
    return True, ""
