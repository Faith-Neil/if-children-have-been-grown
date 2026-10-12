# 为什么有这个文件：按环境变量决定进程使用内存仓库还是连上 MySQL。
# 它解决什么问题：未设置连接串时，现有测试和公网 CI 仍走内存；设置后无需改代码即可连库。

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable, TypeVar

from .adapters import MemoryRepository

DATABASE_URL_ENV = "ICG_DATABASE_URL"
REQUIRE_MYSQL_ENV = "ICG_REQUIRE_MYSQL"
CHARSET = "utf8mb4"
COLLATION = "utf8mb4_0900_ai_ci"
CONNECT_TIMEOUT_SECONDS = 3

T = TypeVar("T")


def database_url() -> str:
    return os.environ.get(DATABASE_URL_ENV, "").strip()


def mysql_required() -> bool:
    return os.environ.get(REQUIRE_MYSQL_ENV, "").strip() == "1"


@dataclass(frozen=True)
class MysqlGate:
    action: str
    reason: str


def create_mysql_engine(url: str):
    # 连接参数强制字符集。密码只来自调用方传入的环境变量，这里不记录连接串。
    from sqlalchemy import create_engine

    return create_engine(
        url,
        pool_pre_ping=True,
        connect_args={
            "charset": CHARSET,
            "collation": COLLATION,
            "connect_timeout": CONNECT_TIMEOUT_SECONDS,
        },
    )


def _probe(url: str) -> None:
    engine = create_mysql_engine(url)
    try:
        with engine.connect() as connection:
            connection.exec_driver_sql("SELECT 1")
    finally:
        engine.dispose()


def mysql_gate() -> MysqlGate:
    # skip 只发生在未要求 MySQL 且没有连接串时。要求开启后，缺库或连不上都是 fail。
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
    return MysqlGate("run", "")


class MysqlConnectionRepository:
    # 本卡只验证连接。业务读写仍委托内存仓库，回执、会话、租约和聚合表留给后续卡。
    mode = "mysql"

    def __init__(self, url: str):
        self.engine = create_mysql_engine(url)
        with self.engine.connect() as connection:
            connection.exec_driver_sql("SELECT 1")
        self._memory = MemoryRepository()

    def read(self):
        return self._memory.read()

    def transaction(self, operation: Callable[..., T]) -> T:
        return self._memory.transaction(operation)


def repository_from_environment():
    url = database_url()
    if not url:
        return MemoryRepository()
    return MysqlConnectionRepository(url)
