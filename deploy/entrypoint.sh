#!/bin/sh
# 为什么有这个文件：容器里的产品进程只在连上 MySQL 之后才监听端口。
# 它解决什么问题：避免镜像在没写连接串时静默改用内存仓库。
set -eu
if [ -z "${ICG_DATABASE_URL:-}" ]; then
  echo "ICG_DATABASE_URL is required. This image does not start a memory repository." >&2
  exit 1
fi
if [ "${ICG_REQUIRE_MYSQL:-}" != "1" ]; then
  echo "ICG_REQUIRE_MYSQL=1 is required." >&2
  exit 1
fi
if [ "${ICG_ENV:-}" = "production" ] && [ -z "${ICG_SECRET_KEY:-}" ]; then
  echo "ICG_SECRET_KEY is required when ICG_ENV=production." >&2
  exit 1
fi
if [ "${ICG_ENV:-}" = "production" ] && [ -z "${ICG_ADMIN_INITIAL_PASSWORD:-}" ]; then
  echo "ICG_ADMIN_INITIAL_PASSWORD is required when ICG_ENV=production." >&2
  exit 1
fi
cd /opt/icg/backend/bid-core
python -m alembic -c alembic.ini upgrade head
exec python -m uvicorn icg_demo.main:app --app-dir /opt/icg/backend/bid-core --host 0.0.0.0 --port 8710 --workers 1
