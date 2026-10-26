# 为什么有这个文件：管理 MySQL 连接、网关门禁与环境变量。
# 它解决什么问题：集中管理 ICG_DATABASE_URL 与 ICG_REQUIRE_MYSQL 门禁逻辑，保证生产环境严禁静默回落到内存仓储。

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

DATABASE_URL_ENV = "ICG_DATABASE_URL"
REQUIRE_MYSQL_ENV = "ICG_REQUIRE_MYSQL"
CHARSET = "utf8mb4"
COLLATION = "utf8mb4_unicode_ci"
CONNECT_TIMEOUT_SECONDS = 3
RECEIPT_TTL = timedelta(hours=24)


def database_url() -> str:
    """获取当前配置的 MySQL 数据库连接串。"""
    return os.environ.get(DATABASE_URL_ENV, "").strip()


def mysql_required() -> bool:
    """判断当前环境是否强制要求 MySQL（生产或严格 CI 环境）。"""
    return os.environ.get(REQUIRE_MYSQL_ENV, "").strip() == "1"


@dataclass(frozen=True)
class MysqlGate:
    """MySQL 门禁状态。"""
    action: str
    reason: str


def _use_utc(dbapi_connection: Any, _connection_record: Any) -> None:
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("SET time_zone = '+00:00'")
    finally:
        cursor.close()


def create_mysql_engine(url: str):
    """创建配置了 UTF-8、UTC 时区与健康探测的 SQLAlchemy MySQL Engine。"""
    from sqlalchemy import create_engine, event

    engine = create_engine(
        url,
        pool_pre_ping=True,
        connect_args={
            "charset": CHARSET,
            "collation": COLLATION,
            "connect_timeout": CONNECT_TIMEOUT_SECONDS,
        },
    )
    event.listen(engine, "connect", _use_utc)
    return engine


def _probe(url: str) -> None:
    engine = create_mysql_engine(url)
    try:
        with engine.connect() as connection:
            connection.exec_driver_sql("SELECT 1")
    finally:
        engine.dispose()


def mysql_gate() -> MysqlGate:
    """检查 MySQL 是否满足当前运行门禁。"""
    url = database_url()
    required = mysql_required()
    if not url:
        if required:
            return MysqlGate("fail", "ICG_REQUIRE_MYSQL=1 but ICG_DATABASE_URL is missing")
        return MysqlGate("skip", "ICG_DATABASE_URL is unset")
    try:
        _probe(url)
    except Exception as exc:
        detail = type(exc).__name__
        if required:
            return MysqlGate("fail", f"ICG_REQUIRE_MYSQL=1 but the database is unreachable ({detail})")
        return MysqlGate("fail", f"database is unreachable ({detail})")
    return MysqlGate("pass", "database connection ok")


def repository_from_environment():
    """根据环境变量创建合适的持久化仓储。生产或强制要求时，严禁静默回退到内存。
    本地未设置 ICG_DATABASE_URL 时回退至 MemoryRepository 仅供开发与显式单元测试使用；
    生产、CI 与关演示冒烟必须设置 ICG_REQUIRE_MYSQL=1 并提供有效数据库连接串。
    """
    url = database_url()
    if not url:
        if mysql_required():
            raise RuntimeError("ICG_REQUIRE_MYSQL=1 but ICG_DATABASE_URL is missing")
        from icg.infra.memory_repository import MemoryRepository
        return MemoryRepository()
    from icg.infra.repositories.mysql_repository import MysqlConnectionRepository
    return MysqlConnectionRepository(url)
