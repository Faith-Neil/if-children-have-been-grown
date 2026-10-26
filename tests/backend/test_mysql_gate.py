# 为什么有这个文件：核对未配置或连不上 MySQL 时，标记测试是跳过还是失败。
# 它解决什么问题：内网 CI 设置 ICG_REQUIRE_MYSQL=1 时，缺库必须失败，不能被当成跳过。

import os
import subprocess
import sys
import time
from pathlib import Path

from icg_demo.adapters import MemoryRepository
from icg_demo.database import mysql_gate
from icg_demo.main import create_app


ROOT = Path(__file__).resolve().parents[2]


def test_unset_url_uses_memory(monkeypatch):
    monkeypatch.delenv("ICG_DATABASE_URL", raising=False)
    monkeypatch.delenv("ICG_REQUIRE_MYSQL", raising=False)
    repository = create_app().state.service.repository
    assert repository.mode == "memory"


def test_explicit_repository_ignores_database_url(monkeypatch):
    monkeypatch.setenv("ICG_DATABASE_URL", "mysql+pymysql://user:secret@127.0.0.1:1/icg_demo")
    repository = MemoryRepository()
    application = create_app(repository=repository)
    assert application.state.service.repository is repository


def test_gate_skips_when_url_missing(monkeypatch):
    monkeypatch.delenv("ICG_DATABASE_URL", raising=False)
    monkeypatch.delenv("ICG_REQUIRE_MYSQL", raising=False)
    gate = mysql_gate()
    assert gate.action == "skip"
    assert "ICG_DATABASE_URL" in gate.reason


def test_gate_fails_when_required_and_url_missing(monkeypatch):
    monkeypatch.delenv("ICG_DATABASE_URL", raising=False)
    monkeypatch.setenv("ICG_REQUIRE_MYSQL", "1")
    gate = mysql_gate()
    assert gate.action == "fail"
    assert "ICG_REQUIRE_MYSQL" in gate.reason
    assert "ICG_DATABASE_URL" in gate.reason


def test_repository_from_environment_raises_when_required_and_url_missing(monkeypatch):
    import pytest
    from icg.infra.mysql_gate import repository_from_environment

    monkeypatch.delenv("ICG_DATABASE_URL", raising=False)
    monkeypatch.setenv("ICG_REQUIRE_MYSQL", "1")
    with pytest.raises(RuntimeError, match="ICG_REQUIRE_MYSQL=1 but ICG_DATABASE_URL is missing"):
        repository_from_environment()


def test_repository_from_environment_allows_memory_when_not_required(monkeypatch):
    from icg.infra.mysql_gate import repository_from_environment

    monkeypatch.delenv("ICG_DATABASE_URL", raising=False)
    monkeypatch.delenv("ICG_REQUIRE_MYSQL", raising=False)
    repo = repository_from_environment()
    assert repo.mode == "memory"


def test_gate_fails_when_required_and_database_unreachable(monkeypatch):
    monkeypatch.setenv("ICG_DATABASE_URL", "mysql+pymysql://user:secret@127.0.0.1:1/icg_demo")
    monkeypatch.setenv("ICG_REQUIRE_MYSQL", "1")
    gate = mysql_gate()
    assert gate.action == "fail"
    assert "secret" not in gate.reason
    assert "ICG_REQUIRE_MYSQL" in gate.reason


def test_gate_fails_when_url_is_set_but_database_unreachable(monkeypatch):
    monkeypatch.setenv("ICG_DATABASE_URL", "mysql+pymysql://user:secret@127.0.0.1:1/icg_demo")
    monkeypatch.delenv("ICG_REQUIRE_MYSQL", raising=False)
    gate = mysql_gate()
    assert gate.action == "fail"
    assert "secret" not in gate.reason


def test_create_app_does_not_connect_when_the_url_is_set(monkeypatch):
    monkeypatch.setenv("ICG_DATABASE_URL", "mysql+pymysql://user:secret@127.0.0.1:1/icg_demo")
    application = create_app()
    repository = application.state.service.repository
    assert repository.mode == "mysql"
    assert repository._engine is None


def test_required_unreachable_database_fails_fast_without_a_collection_error():
    env = os.environ.copy()
    env["ICG_DATABASE_URL"] = "mysql+pymysql://user:secret@127.0.0.1:1/icg_demo"
    env["ICG_REQUIRE_MYSQL"] = "1"
    started = time.monotonic()
    result = subprocess.run(
        [sys.executable, "-m", "pytest",
         "tests/backend/test_mysql_connection.py::test_health_uses_mysql_connection_without_code_change",
         "-m", "mysql", "-q", "--tb=line"],
        cwd=ROOT, env=env, capture_output=True, text=True, check=False,
    )
    elapsed = time.monotonic() - started
    combined = result.stdout + result.stderr
    summary = combined.strip().splitlines()[-1]
    assert result.returncode != 0, combined
    assert "failed" in summary
    assert "error" not in summary
    assert "secret" not in combined
    assert elapsed < 8


def test_mysql_marker_fails_instead_of_skipping_when_required():
    env = os.environ.copy()
    env.pop("ICG_DATABASE_URL", None)
    env["ICG_REQUIRE_MYSQL"] = "1"
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/backend/test_mysql_connection.py",
         "-m", "mysql", "-q", "--tb=line"],
        cwd=ROOT, env=env, capture_output=True, text=True, check=False,
    )
    combined = result.stdout + result.stderr
    assert result.returncode != 0, combined
    summary = combined.strip().splitlines()[-1]
    assert "failed" in summary
    assert "skipped" not in summary
    assert "error" not in summary
