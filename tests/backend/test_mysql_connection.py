# 为什么有这个文件：用真实 MySQL 8 核对连接和空基线迁移。
# 它解决什么问题：确认只设置 ICG_DATABASE_URL 就能连上库，且本卡还不建业务表。

import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from icg_demo.main import create_app


pytestmark = pytest.mark.mysql

ROOT = Path(__file__).resolve().parents[2]


def test_alembic_baseline_upgrade_creates_only_version_table():
    env = os.environ.copy()
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "backend/bid-core/alembic.ini", "upgrade", "head"],
        cwd=ROOT, env=env, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "ICG_DATABASE_URL" not in result.stderr or "required" not in result.stderr
    repository = create_app().state.service.repository
    assert repository.mode == "mysql"
    with repository.engine.connect() as connection:
        charset = connection.execute(text(
            "SELECT @@character_set_connection, @@collation_connection"
        )).one()
        tables = connection.execute(text("SHOW TABLES")).scalars().all()
    assert charset[0] == "utf8mb4"
    assert charset[1] == "utf8mb4_0900_ai_ci"
    assert tables == ["alembic_version"]


def test_health_uses_mysql_connection_without_code_change():
    with TestClient(create_app()) as client:
        response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["repository"] == "mysql"
    assert body["status"] == "ok"
