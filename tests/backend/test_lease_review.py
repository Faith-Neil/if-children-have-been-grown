# 为什么有这个文件：复现旧租约快照覆盖或删除已接管编辑权的竞态。
# 它解决什么问题：通过实际领域回调和 SQLite 执行生产 SQL 核验条件更新与回滚，不冒充真实 MySQL 验收。

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, event, text

from icg_demo.adapters import DemoModelProvider
from icg_demo.database import MysqlConnectionRepository
from icg_demo.domain import DemoService, DomainError, Lease, Principal


NOW = datetime(2026, 10, 12, 12, 0, 0, 123456)
NOW_SECONDS = NOW.replace(tzinfo=timezone.utc).timestamp()
CHAPTER = "alpha-tech"
OLD_LEASE = ("old-lease", "alpha-editor", "editor-session", NOW_SECONDS + 60)
WINNING_LEASE = ("new-lease", "alpha-manager", "manager-session", NOW_SECONDS + 120)


@pytest.fixture
def repository(monkeypatch):
    engine = create_engine("sqlite://")

    @event.listens_for(engine, "connect")
    def install_now(connection, _record):
        connection.create_function("NOW", 1, lambda _precision: NOW.strftime("%Y-%m-%d %H:%M:%S.%f"))

    with engine.begin() as connection:
        connection.execute(text(
            "CREATE TABLE idempotency_receipt (scope_id TEXT, user_id TEXT, idempotency_key TEXT, "
            "fingerprint TEXT, created_at DATETIME, expires_at DATETIME)"
        ))
        connection.execute(text(
            "CREATE TABLE chapter_lease (chapter_id TEXT PRIMARY KEY, token TEXT, owner_id TEXT, "
            "session_token TEXT, expires_at DATETIME)"
        ))
    repository = MysqlConnectionRepository("unused-synthetic-url")
    repository._engine = engine

    def load_snapshot(state, _loaded_project_ids, *_args, **_kwargs):
        # 模拟进程已读到旧租约，另一个进程在保存之前提交了接管。
        state.sessions = {"editor-session": "alpha-editor", "manager-session": "alpha-manager"}
        state.workflow_receipts = {}
        state.chapters[CHAPTER].lock = Lease(*OLD_LEASE)

    monkeypatch.setattr(repository, "_load_shared", load_snapshot)
    try:
        yield repository
    finally:
        engine.dispose()


def store_lease(repository, lease):
    token, owner_id, session_token, expires_at = lease
    expiry = datetime.fromtimestamp(expires_at, timezone.utc).replace(tzinfo=None)
    with repository.engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO chapter_lease VALUES (:chapter_id, :token, :owner_id, :session_token, :expires_at)"
        ), {"chapter_id": CHAPTER, "token": token, "owner_id": owner_id,
            "session_token": session_token, "expires_at": expiry})


def stored_lease(repository):
    with repository.engine.connect() as connection:
        return connection.execute(text(
            "SELECT token, owner_id, session_token, expires_at FROM chapter_lease WHERE chapter_id = :chapter_id"
        ), {"chapter_id": CHAPTER}).one_or_none()


def perform(service, repository, operation):
    account_id = "alpha-manager" if operation == "takeover" else "alpha-editor"
    token = "manager-session" if operation == "takeover" else "editor-session"
    principal = Principal(repository._memory.read().accounts[account_id], token)
    if operation == "renew":
        return service.renew_lock(principal, CHAPTER, OLD_LEASE[0])
    if operation == "release":
        return service.release_lock(principal, CHAPTER, OLD_LEASE[0])
    return service.acquire_lock(principal, CHAPTER, "合成接管复核")


@pytest.mark.parametrize("operation", ["renew", "release", "takeover"])
def test_stale_lease_mutation_is_rejected_and_preserves_new_owner(repository, operation):
    store_lease(repository, WINNING_LEASE)
    before_sql = stored_lease(repository)
    before_memory = repository._memory.read()
    service = DemoService(repository, DemoModelProvider(), clock=lambda: NOW_SECONDS)

    with pytest.raises(DomainError) as failed:
        perform(service, repository, operation)

    assert failed.value.status == 423 and failed.value.code == "LOCK_LOST"
    assert stored_lease(repository) == before_sql
    assert repository._memory.read() == before_memory


@pytest.mark.parametrize("operation", ["renew", "release", "takeover"])
def test_matching_lease_mutation_still_commits(repository, operation):
    store_lease(repository, OLD_LEASE)
    service = DemoService(repository, DemoModelProvider(), clock=lambda: NOW_SECONDS)

    result = perform(service, repository, operation)

    row = stored_lease(repository)
    if operation == "release":
        assert result == {"released": True}
        assert row is None
    else:
        assert row.token == result["lease_token"]
        assert row.owner_id == result["owner_id"]
        assert row.session_token == ("manager-session" if operation == "takeover" else "editor-session")
    assert repository._memory.read().audit[-1]["action"] == "lock." + operation


def test_first_acquire_race_returns_existing_lock_error(repository):
    store_lease(repository, WINNING_LEASE)
    before = stored_lease(repository)

    with pytest.raises(DomainError) as failed:
        repository._save_shared({}, {}, {}, {}, {CHAPTER: None}, {CHAPTER: OLD_LEASE}, {}, {}, {}, {}, set())

    assert failed.value.status == 423 and failed.value.code == "LOCK_HELD"
    assert stored_lease(repository) == before


def test_lease_conflict_rolls_back_preceding_receipt_deletion(repository):
    store_lease(repository, WINNING_LEASE)
    created_at = NOW - timedelta(seconds=60)
    key = ("alpha-project", "alpha-editor", "synthetic-receipt-key")
    with repository.engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO idempotency_receipt VALUES (:scope_id, :user_id, :key, :fingerprint, :created_at, :expires_at)"
        ), {"scope_id": key[0], "user_id": key[1], "key": key[2], "fingerprint": "a" * 64,
            "created_at": created_at, "expires_at": created_at + timedelta(hours=24)})
    before_receipts = {key: {"created_at": created_at.replace(tzinfo=timezone.utc).timestamp(),
                              "fingerprint": "a" * 64, "result": {"revision": 1}}}

    with pytest.raises(DomainError):
        repository._save_shared({}, {}, before_receipts, {}, {CHAPTER: OLD_LEASE}, {CHAPTER: None}, {}, {}, {}, {}, set())

    with repository.engine.connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM idempotency_receipt")).scalar() == 1
