# 为什么有这个文件：让迁移只从环境变量读取 MySQL 连接。
# 它解决什么问题：避免把密码写进 alembic.ini 或迁移日志。

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None


def migration_url() -> str:
    url = os.environ.get("ICG_DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError(
            "ICG_DATABASE_URL is required to run migrations. "
            "Keep the password in the environment; do not write it into alembic.ini."
        )
    return url


def run_migrations_offline() -> None:
    context.configure(url=migration_url(), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(
        migration_url(),
        poolclass=pool.NullPool,
        connect_args={
            "charset": "utf8mb4",
            "collation": "utf8mb4_0900_ai_ci",
            "connect_timeout": 3,
        },
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
