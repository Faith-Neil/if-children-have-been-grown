# 为什么有这个文件：用真实 MySQL 核对回执和登录会话能不能跨进程、跨重启。
# 它解决什么问题：内存仓库做不到的共享和重启保留，要在 mysql 标记测试里失败而不是被跳过。

import multiprocessing
import sys
import time
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from icg_demo.idempotency import remember
from icg_demo.main import create_app


pytestmark = pytest.mark.mysql

ROOT = Path(__file__).resolve().parents[2]
WORKER_DIR = Path(__file__).resolve().parent
LIBRARY_BODY = {
    "name": "合成跨进程资料",
    "type": "qualification",
    "content": "仅供测试的合成正文。",
    "status": "pending",
}


def _process(action: str, payload: dict) -> dict:
    if str(WORKER_DIR) not in sys.path:
        sys.path.insert(0, str(WORKER_DIR))
    from mysql_worker import run_action

    context = multiprocessing.get_context("spawn")
    queue = context.Queue()
    process = context.Process(target=run_action, args=(action, payload, queue))
    process.start()
    process.join(60)
    assert process.exitcode == 0, process.exitcode
    return queue.get(timeout=5)


def _upgrade() -> None:
    import os
    import subprocess
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "backend/bid-core/alembic.ini", "upgrade", "head"],
        cwd=ROOT, env=os.environ.copy(), capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr


def test_receipt_and_session_survive_a_new_process():
    _upgrade()
    key = uuid4().hex
    written = _process("write", {"key": key, "body": LIBRARY_BODY})
    assert written["ok"], written
    assert written["replayed"] is None
    item_id = written["body"]["item"]["id"]
    replayed = _process("replay", {
        "key": key,
        "body": LIBRARY_BODY,
        "token": written["token"],
        "revision": written["revision"],
    })
    assert replayed["ok"], replayed
    assert replayed["replayed"] == "true"
    assert replayed["body"]["item"]["id"] == item_id
    assert replayed["session"]["user"]["id"] == "alpha-editor"


def test_failed_library_write_stores_no_receipt():
    key = "failedkey01"
    with TestClient(create_app()) as client:
        login = client.post("/api/demo/login", json={"account_id": "alpha-editor"})
        assert login.status_code == 200, login.text
        token = login.json()["access_token"]
        headers = {"Authorization": "Bearer " + token}
        library = client.get("/api/v1/library", headers=headers)
        response = client.post(
            "/api/v1/library",
            headers={**headers, "If-Match": str(library.json()["revision"]), "Idempotency-Key": key},
            json={"name": "空白正文", "type": "qualification", "content": "  "},
        )
        assert response.status_code == 422, response.text
    repository = create_app().state.service.repository
    with repository.engine.connect() as connection:
        count = connection.execute(
            text("SELECT COUNT(*) FROM idempotency_receipt WHERE idempotency_key = :key"),
            {"key": key},
        ).scalar()
    assert count == 0


def test_mysql_keeps_more_than_2048_receipts():
    repository = create_app().state.service.repository
    now = time.time()
    scope_id = "library:synthetic-cap"

    def operation(state):
        for index in range(2049):
            remember(state, scope_id, "alpha-editor", f"capkey{index:05d}", "f" * 64, {"n": index}, now)
        return sum(1 for key in state.workflow_receipts if key[0] == scope_id)

    with repository.engine.begin() as connection:
        connection.execute(
            text("DELETE FROM idempotency_receipt WHERE scope_id = :scope_id"),
            {"scope_id": scope_id},
        )
    try:
        kept = repository.transaction(operation)
        assert kept == 2049
        with repository.engine.connect() as connection:
            stored = connection.execute(
                text("SELECT COUNT(*) FROM idempotency_receipt WHERE scope_id = :scope_id"),
                {"scope_id": scope_id},
            ).scalar()
        assert stored == 2049
    finally:
        with repository.engine.begin() as connection:
            connection.execute(
                text("DELETE FROM idempotency_receipt WHERE scope_id = :scope_id"),
                {"scope_id": scope_id},
            )
