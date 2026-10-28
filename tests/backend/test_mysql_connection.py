# 为什么有这个文件：用真实 MySQL 8 核对连接、迁移和回退。
# 它解决什么问题：确认只设置 ICG_DATABASE_URL 就能连上库，回执表和会话表可以建出来，也可以降回基线后再建回来。

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


def _alembic(*args: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "backend/bid-core/alembic.ini", *args],
        cwd=ROOT, env=os.environ.copy(), capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    return result


def _table_names(connection) -> list[str]:
    return sorted(connection.execute(text("SHOW TABLES")).scalars().all())


def test_alembic_upgrade_creates_session_and_receipt_tables():
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
        tables = _table_names(connection)
    assert charset[0] == "utf8mb4"
    assert charset[1] == "utf8mb4_0900_ai_ci"
    assert tables == [
        "alembic_version", "chapter_lease", "demo_chapter", "demo_chapter_version",
        "demo_check", "demo_export", "demo_job", "demo_library_item", "demo_library_revision",
        "demo_model_config", "demo_project", "demo_project_model_config", "demo_project_team",
        "demo_project_workflow_state",
        "demo_sla_template", "demo_workflow", "idempotency_receipt", "user_session",
    ]


def test_alembic_downgrade_to_base_then_upgrade_restores_tables():
    # QA M1：第一批真实表必须能降回基线再升回来。DevOps 可以把同样两条 alembic 命令加进 backend-mysql，本测试不改工作流。
    _alembic("upgrade", "head")
    try:
        _alembic("downgrade", "base")
        repository = create_app().state.service.repository
        with repository.engine.connect() as connection:
            remaining = _table_names(connection)
        assert "idempotency_receipt" not in remaining
        assert "user_session" not in remaining
        assert "demo_project" not in remaining
        assert "demo_project_team" not in remaining
        assert "demo_project_workflow_state" not in remaining
        assert "chapter_lease" not in remaining
        assert "demo_model_config" not in remaining
        assert "demo_project_model_config" not in remaining
        assert "demo_chapter" not in remaining
        assert "demo_chapter_version" not in remaining
        assert "demo_check" not in remaining
        assert "demo_export" not in remaining
        assert "demo_library_item" not in remaining
        assert "demo_library_revision" not in remaining
        assert "demo_sla_template" not in remaining
        assert "demo_workflow" not in remaining
        assert "demo_job" not in remaining
    finally:
        _alembic("upgrade", "head")
    repository = create_app().state.service.repository
    with repository.engine.connect() as connection:
        assert _table_names(connection) == [
            "alembic_version", "chapter_lease", "demo_chapter", "demo_chapter_version",
            "demo_check", "demo_export", "demo_job", "demo_library_item", "demo_library_revision",
            "demo_model_config", "demo_project", "demo_project_model_config", "demo_project_team",
        "demo_project_workflow_state",
            "demo_sla_template", "demo_workflow", "idempotency_receipt", "user_session",
        ]


def test_health_uses_mysql_connection_without_code_change():
    with TestClient(create_app()) as client:
        response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["repository"] == "mysql"
    assert body["status"] == "ok"
