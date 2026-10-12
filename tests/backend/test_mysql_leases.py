# 为什么有这个文件：用真实 MySQL 核对编辑租约能不能跨进程续期和过期接管。
# 它解决什么问题：内存仓库里的 120 秒租约换进程就消失，续期和接管必须在库里仍然成立。

import os
import subprocess
import sys
import time
from datetime import timezone
from pathlib import Path

import pytest
from sqlalchemy import text

from icg_demo.main import create_app


pytestmark = pytest.mark.mysql

ROOT = Path(__file__).resolve().parents[2]
WORKER_DIR = Path(__file__).resolve().parent
CHAPTER = "alpha-tech"


def _process(action: str, payload: dict) -> dict:
    if str(WORKER_DIR) not in sys.path:
        sys.path.insert(0, str(WORKER_DIR))
    from mysql_worker import run_action
    import multiprocessing

    context = multiprocessing.get_context("spawn")
    queue = context.Queue()
    process = context.Process(target=run_action, args=(action, payload, queue))
    process.start()
    process.join(60)
    assert process.exitcode == 0, process.exitcode
    return queue.get(timeout=5)


def _upgrade() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "backend/bid-core/alembic.ini", "upgrade", "head"],
        cwd=ROOT, env=os.environ.copy(), capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr


def _lease_row():
    repository = create_app().state.service.repository
    with repository.engine.connect() as connection:
        tables = connection.execute(text("SHOW TABLES")).scalars().all()
        assert "chapter_lease" in tables
        return connection.execute(
            text(
                "SELECT token, owner_id, session_token, expires_at "
                "FROM chapter_lease WHERE chapter_id = :chapter_id"
            ),
            {"chapter_id": CHAPTER},
        ).one_or_none()


def _expire_lease() -> None:
    repository = create_app().state.service.repository
    with repository.engine.begin() as connection:
        result = connection.execute(
            text(
                "UPDATE chapter_lease SET expires_at = '2000-01-01 00:00:00.000000' "
                "WHERE chapter_id = :chapter_id"
            ),
            {"chapter_id": CHAPTER},
        )
        assert result.rowcount == 1


def _clear_lease() -> None:
    repository = create_app().state.service.repository
    with repository.engine.begin() as connection:
        tables = connection.execute(text("SHOW TABLES")).scalars().all()
        if "chapter_lease" not in tables:
            return
        connection.execute(
            text("DELETE FROM chapter_lease WHERE chapter_id = :chapter_id"),
            {"chapter_id": CHAPTER},
        )


def test_renewal_keeps_the_same_owner_for_about_120_seconds():
    _upgrade()
    _clear_lease()
    try:
        acquired = _process("lock_acquire", {"chapter_id": CHAPTER, "account_id": "alpha-editor"})
        assert acquired["status"] == 200, acquired
        first = acquired["body"]
        stored = _lease_row()
        assert stored is not None
        assert stored.token == first["lease_token"]
        assert stored.owner_id == first["owner_id"]
        remaining = stored.expires_at.replace(tzinfo=timezone.utc).timestamp() - time.time()
        # DATETIME 按 UTC 读出。剩余时间应接近租约的 120 秒，而不是会话寿命。
        assert 90 <= remaining <= 130
        renewed = _process("lock_renew", {
            "chapter_id": CHAPTER,
            "token": acquired["token"],
            "lease_token": first["lease_token"],
        })
        assert renewed["status"] == 200, renewed
        second = renewed["body"]
        assert second["lease_token"] == first["lease_token"]
        assert second["owner_id"] == first["owner_id"]
        assert second["expires_at"] > first["expires_at"]
        updated = _lease_row()
        assert updated.token == first["lease_token"]
        assert updated.owner_id == first["owner_id"]
        assert updated.session_token == stored.session_token
        assert updated.expires_at > stored.expires_at
    finally:
        _clear_lease()


def test_expired_lease_can_be_taken_by_another_session():
    _upgrade()
    _clear_lease()
    try:
        held = _process("lock_acquire", {"chapter_id": CHAPTER, "account_id": "alpha-editor"})
        assert held["status"] == 200, held
        assert _lease_row() is not None
        blocked = _process("lock_acquire", {"chapter_id": CHAPTER, "account_id": "alpha-editor"})
        assert blocked["status"] == 423, blocked
        _expire_lease()
        taken = _process("lock_acquire", {"chapter_id": CHAPTER, "account_id": "alpha-editor"})
        assert taken["status"] == 200, taken
        assert taken["body"]["lease_token"] != held["body"]["lease_token"]
        assert taken["token"] != held["token"]
        stored = _lease_row()
        assert stored.token == taken["body"]["lease_token"]
        assert stored.owner_id == taken["body"]["owner_id"]
    finally:
        _clear_lease()
