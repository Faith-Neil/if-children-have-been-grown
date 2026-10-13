# 为什么有这个文件：复现回执读取容量与旧快照删除的隔离审查缺陷。
# 它解决什么问题：验证 MySQL 仓储的读取契约和实际删除 SQL，不把 SQLite 探针当成真实 MySQL 验收。

from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, event, text

from icg_demo.adapters import DemoModelProvider
from icg_demo.database import MysqlConnectionRepository
from icg_demo.domain import DemoService, Principal
from icg_demo.idempotency import fingerprint
from icg_demo.parsing import LocalTextParser
from icg_demo.workflow import WorkflowService


NOW = datetime(2026, 10, 12, 12, 0, 0, 123456)
RECEIPT_KEY = ("alpha-project", "alpha-manager", "parse-replay-oldest")


@pytest.mark.parametrize("count", [2048, 2049])
def test_mysql_read_replays_old_parse_receipt_without_memory_capacity_limit(monkeypatch, count):
    # 只替换共享数据装载；read()、预检查、权限和幂等查找均执行实际实现。
    repository = MysqlConnectionRepository("unused-synthetic-url")
    repository._memory.transaction(lambda state: setattr(state.projects["alpha-project"], "revision", 2))
    now = NOW.replace(tzinfo=timezone.utc).timestamp()
    first_result = {"revision": 2, "job": {"status": "completed"}}
    receipts = {RECEIPT_KEY: {
        "fingerprint": fingerprint("parse.run", {}, "1"),
        "result": first_result,
        "created_at": now - 60,
    }}
    for index in range(count - 1):
        receipts[("unrelated-project", "alpha-editor", f"extra-key-{index:05d}")] = {
            "fingerprint": "f" * 64, "result": {"n": index}, "created_at": now - 30,
        }

    def load_shared(state, _loaded_project_ids):
        state.sessions = {"synthetic-session": "alpha-manager"}
        state.workflow_receipts = deepcopy(receipts)

    monkeypatch.setattr(repository, "_load_shared", load_shared)
    state = repository.read()
    principal = Principal(state.accounts["alpha-manager"], "synthetic-session")
    workflow = WorkflowService(DemoService(repository, DemoModelProvider(), clock=lambda: now), LocalTextParser())
    snapshot, replayed = workflow._preflight(principal, "alpha-project", "parse.run", {}, "1", RECEIPT_KEY[2])

    assert replayed == first_result
    assert snapshot.cap_receipts is False
    assert len(snapshot.workflow_receipts) == count


@pytest.fixture
def sql_repository():
    # SQLite 仅执行生产代码的 DELETE 语句。连接、迁移和 MySQL 多进程验收另有 mysql 标记测试。
    engine = create_engine("sqlite://")

    @event.listens_for(engine, "connect")
    def install_now(connection, _record):
        connection.create_function("NOW", 1, lambda _precision: NOW.strftime("%Y-%m-%d %H:%M:%S.%f"))

    with engine.begin() as connection:
        connection.execute(text(
            "CREATE TABLE idempotency_receipt ("
            "scope_id TEXT, user_id TEXT, idempotency_key TEXT, fingerprint TEXT, "
            "created_at DATETIME, expires_at DATETIME, "
            "PRIMARY KEY (scope_id, user_id, idempotency_key))"
        ))
    repository = MysqlConnectionRepository("unused-synthetic-url")
    repository._engine = engine
    try:
        yield repository
    finally:
        engine.dispose()


def store_receipt(repository, created_at, receipt_fingerprint):
    with repository.engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO idempotency_receipt "
            "(scope_id, user_id, idempotency_key, fingerprint, created_at, expires_at) "
            "VALUES (:scope_id, :user_id, :key, :fingerprint, :created_at, :expires_at)"
        ), {"scope_id": RECEIPT_KEY[0], "user_id": RECEIPT_KEY[1], "key": RECEIPT_KEY[2],
            "fingerprint": receipt_fingerprint, "created_at": created_at,
            "expires_at": created_at + timedelta(hours=24)})


def stored_receipts(repository):
    with repository.engine.connect() as connection:
        return connection.execute(text("SELECT fingerprint, created_at FROM idempotency_receipt")).all()


@pytest.mark.parametrize("change", ["created_at", "fingerprint"])
def test_old_snapshot_delete_preserves_replacement_receipt(sql_repository, change):
    old_created_at = NOW - timedelta(seconds=60)
    old_fingerprint = "a" * 64
    before = {RECEIPT_KEY: {"created_at": old_created_at.replace(tzinfo=timezone.utc).timestamp(),
                            "fingerprint": old_fingerprint, "result": {"revision": 1}}}
    new_created_at = NOW if change == "created_at" else old_created_at
    new_fingerprint = "b" * 64 if change == "fingerprint" else old_fingerprint
    store_receipt(sql_repository, new_created_at, new_fingerprint)
    before_delete = stored_receipts(sql_repository)

    # 此时另一进程已提交同键新回执；当前进程仍持有删除前的旧快照。
    sql_repository._save_shared({}, {}, before, {}, {}, {}, {}, {}, {}, {}, set())

    assert stored_receipts(sql_repository) == before_delete


def test_removed_snapshot_receipt_is_deleted_when_current_row_matches(sql_repository):
    created_at = NOW - timedelta(seconds=60)
    receipt_fingerprint = "a" * 64
    store_receipt(sql_repository, created_at, receipt_fingerprint)
    before = {RECEIPT_KEY: {"created_at": created_at.replace(tzinfo=timezone.utc).timestamp(),
                            "fingerprint": receipt_fingerprint, "result": {"revision": 1}}}

    sql_repository._save_shared({}, {}, before, {}, {}, {}, {}, {}, {}, {}, set())

    assert stored_receipts(sql_repository) == []
