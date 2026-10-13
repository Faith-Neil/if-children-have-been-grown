# 为什么有这个文件：按环境变量决定进程使用内存仓库还是连上 MySQL。
# 它解决什么问题：未设置连接串时，现有测试和公网 CI 仍走内存；设置后回执、登录会话、编辑租约和项目对多个进程可见。

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Callable, TypeVar

from .adapters import MemoryRepository
from .domain import DemoState, DomainError, Lease, Project

DATABASE_URL_ENV = "ICG_DATABASE_URL"
REQUIRE_MYSQL_ENV = "ICG_REQUIRE_MYSQL"
CHARSET = "utf8mb4"
COLLATION = "utf8mb4_0900_ai_ci"
CONNECT_TIMEOUT_SECONDS = 3
RECEIPT_TTL = timedelta(hours=24)

T = TypeVar("T")


def database_url() -> str:
    return os.environ.get(DATABASE_URL_ENV, "").strip()


def mysql_required() -> bool:
    return os.environ.get(REQUIRE_MYSQL_ENV, "").strip() == "1"


@dataclass(frozen=True)
class MysqlGate:
    action: str
    reason: str


def _use_utc(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("SET time_zone = '+00:00'")
    finally:
        cursor.close()


def create_mysql_engine(url: str):
    # 连接参数强制字符集。密码只来自调用方传入的环境变量，这里不记录连接串。
    from sqlalchemy import create_engine, event

    engine = create_engine(
        url,
        pool_pre_ping=True,
        connect_args={
            "charset": CHARSET,
            "collation": COLLATION,
            "connect_timeout": CONNECT_TIMEOUT_SECONDS,
        },
    )
    event.listen(engine, "connect", _use_utc)
    return engine


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


def _utc_naive(timestamp: float) -> datetime:
    return datetime.fromtimestamp(float(timestamp), timezone.utc).replace(tzinfo=None)


def _as_timestamp(value: datetime) -> float:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.timestamp()


def _json_value(value):
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8")
    if isinstance(value, str):
        return json.loads(value)
    return value


class MysqlConnectionRepository:
    # 章节、检查、导出、资料、工作流和审计仍在内存。登录会话、幂等回执、编辑租约和项目写入 MySQL。
    # 导入和 create_app 都不连接。未改过的种子项目不插入，避免把整份状态写成一批行。
    mode = "mysql"

    def __init__(self, url: str):
        self._url = url
        self._engine = None
        self._engine_lock = Lock()
        self._memory = MemoryRepository()

    @property
    def engine(self):
        if self._engine is not None:
            return self._engine
        with self._engine_lock:
            if self._engine is None:
                engine = create_mysql_engine(self._url)
                try:
                    with engine.connect() as connection:
                        connection.exec_driver_sql("SELECT 1")
                except Exception:
                    engine.dispose()
                    raise
                self._engine = engine
            return self._engine

    def read(self):
        state = self._memory.read()
        self._load_shared(state, set())
        state.cap_receipts = False
        return state

    def transaction(self, operation: Callable[..., T]) -> T:
        loaded_project_ids: set[str] = set()

        def wrapped(state: DemoState) -> T:
            self._load_shared(state, loaded_project_ids)
            state.cap_receipts = False
            before_sessions = dict(state.sessions)
            before_receipts = {key: dict(receipt) for key, receipt in state.workflow_receipts.items()}
            before_leases = _lease_snapshot(state)
            before_projects = _project_snapshot(state)
            before_teams = _team_snapshot(state)
            result = operation(state)
            self._save_shared(
                before_sessions, dict(state.sessions), before_receipts, state.workflow_receipts,
                before_leases, _lease_snapshot(state),
                before_projects, _project_snapshot(state), before_teams, _team_snapshot(state),
                loaded_project_ids,
            )
            state.sessions.clear()
            state.workflow_receipts.clear()
            for chapter in state.chapters.values():
                chapter.lock = None
            state.cap_receipts = True
            return result

        return self._memory.transaction(wrapped)

    def _load_shared(self, state: DemoState, loaded_project_ids: set[str]) -> None:
        from sqlalchemy import text

        with self.engine.begin() as connection:
            connection.execute(text("DELETE FROM idempotency_receipt WHERE expires_at <= NOW(6)"))
            sessions = connection.execute(text("SELECT token, user_id FROM user_session")).all()
            receipts = connection.execute(text(
                "SELECT scope_id, user_id, idempotency_key, fingerprint, result_json, created_at "
                "FROM idempotency_receipt"
            )).all()
            leases = connection.execute(text(
                "SELECT chapter_id, token, owner_id, session_token, expires_at FROM chapter_lease"
            )).all()
            projects = connection.execute(text(
                "SELECT id, name, company_id, revision, tender_number, deadline, is_sensitive FROM demo_project"
            )).all()
            teams = connection.execute(text(
                "SELECT project_id, team_json FROM demo_project_team"
            )).all()
        state.sessions = {token: user_id for token, user_id in sessions}
        state.workflow_receipts = {
            (scope_id, user_id, key): {
                "fingerprint": fingerprint,
                "result": _json_value(result_json),
                "created_at": _as_timestamp(created_at),
            }
            for scope_id, user_id, key, fingerprint, result_json, created_at in receipts
        }
        loaded = {
            chapter_id: Lease(token, owner_id, session_token, _as_timestamp(expires_at))
            for chapter_id, token, owner_id, session_token, expires_at in leases
        }
        for chapter_id, chapter in state.chapters.items():
            chapter.lock = loaded.get(chapter_id)
        loaded_project_ids.clear()
        loaded_project_ids.update(project_id for project_id, *_rest in projects)
        for project_id, name, company_id, revision, tender_number, deadline, sensitive in projects:
            state.projects[project_id] = Project(
                project_id, name, company_id, int(revision),
                tender_number or "", deadline or "", bool(sensitive),
            )
        for project_id, team_json in teams:
            state.project_teams[project_id] = _json_value(team_json)

    def _save_shared(self, before_sessions: dict, after_sessions: dict,
                     before_receipts: dict, after_receipts: dict,
                     before_leases: dict, after_leases: dict,
                     before_projects: dict, after_projects: dict,
                     before_teams: dict, after_teams: dict,
                     loaded_project_ids: set[str]) -> None:
        from sqlalchemy import text
        from sqlalchemy.exc import IntegrityError

        with self.engine.begin() as connection:
            connection.execute(text("DELETE FROM idempotency_receipt WHERE expires_at <= NOW(6)"))
            for token in before_sessions:
                if token not in after_sessions:
                    connection.execute(text("DELETE FROM user_session WHERE token = :token"), {"token": token})
            for token, user_id in after_sessions.items():
                if before_sessions.get(token) == user_id:
                    continue
                if token in before_sessions:
                    connection.execute(
                        text("UPDATE user_session SET user_id = :user_id WHERE token = :token"),
                        {"token": token, "user_id": user_id},
                    )
                else:
                    connection.execute(
                        text(
                            "INSERT INTO user_session (token, user_id, created_at) "
                            "VALUES (:token, :user_id, UTC_TIMESTAMP(6))"
                        ),
                        {"token": token, "user_id": user_id},
                    )
            for key in before_receipts:
                if key not in after_receipts:
                    scope_id, user_id, idempotency_key = key
                    previous = before_receipts[key]
                    connection.execute(
                        text(
                            "DELETE FROM idempotency_receipt WHERE scope_id = :scope_id "
                            "AND user_id = :user_id AND idempotency_key = :idempotency_key"
                            " AND created_at = :created_at AND fingerprint = :fingerprint"
                        ),
                        {"scope_id": scope_id, "user_id": user_id, "idempotency_key": idempotency_key,
                         "created_at": _utc_naive(previous["created_at"]), "fingerprint": previous["fingerprint"]},
                    )
            for key, receipt in after_receipts.items():
                previous = before_receipts.get(key)
                if previous is not None and _same_receipt(previous, receipt):
                    continue
                scope_id, user_id, idempotency_key = key
                created_at = _utc_naive(receipt["created_at"])
                payload = {
                    "scope_id": scope_id,
                    "user_id": user_id,
                    "idempotency_key": idempotency_key,
                    "fingerprint": receipt["fingerprint"],
                    "result_json": json.dumps(receipt["result"], ensure_ascii=False, sort_keys=True),
                    "created_at": created_at,
                    "expires_at": created_at + RECEIPT_TTL,
                }
                if previous is None:
                    connection.execute(
                        text(
                            "INSERT INTO idempotency_receipt "
                            "(scope_id, user_id, idempotency_key, fingerprint, result_json, created_at, expires_at) "
                            "VALUES (:scope_id, :user_id, :idempotency_key, :fingerprint, "
                            "CAST(:result_json AS JSON), :created_at, :expires_at)"
                        ),
                        payload,
                    )
                else:
                    connection.execute(
                        text(
                            "UPDATE idempotency_receipt SET fingerprint = :fingerprint, "
                            "result_json = CAST(:result_json AS JSON), created_at = :created_at, "
                            "expires_at = :expires_at WHERE scope_id = :scope_id AND user_id = :user_id "
                            "AND idempotency_key = :idempotency_key"
                        ),
                        payload,
                    )
            for chapter_id in set(before_leases) | set(after_leases):
                previous = before_leases.get(chapter_id)
                current = after_leases.get(chapter_id)
                if previous == current:
                    continue
                # 旧快照只能修改自己读到的租约，不能撤掉或覆盖另一进程已经接管的编辑权。
                condition = ("chapter_id = :chapter_id AND token = :previous_token "
                             "AND owner_id = :previous_owner_id AND session_token = :previous_session_token "
                             "AND expires_at = :previous_expires_at")
                comparison = {} if previous is None else {
                    "chapter_id": chapter_id,
                    "previous_token": previous[0],
                    "previous_owner_id": previous[1],
                    "previous_session_token": previous[2],
                    "previous_expires_at": _utc_naive(previous[3]),
                }
                if current is None:
                    deleted = connection.execute(
                        text("DELETE FROM chapter_lease WHERE " + condition), comparison,
                    )
                    if deleted.rowcount != 1:
                        raise DomainError(423, "LOCK_LOST", "编辑权已失效，请重新取得编辑权后再操作。")
                    continue
                token, owner_id, session_token, expires_at = current
                payload = {
                    "chapter_id": chapter_id,
                    "token": token,
                    "owner_id": owner_id,
                    "session_token": session_token,
                    "expires_at": _utc_naive(expires_at),
                }
                if previous is None:
                    try:
                        connection.execute(
                            text(
                                "INSERT INTO chapter_lease "
                                "(chapter_id, token, owner_id, session_token, expires_at) "
                                "VALUES (:chapter_id, :token, :owner_id, :session_token, :expires_at)"
                            ),
                            payload,
                        )
                    except IntegrityError as error:
                        raise DomainError(423, "LOCK_HELD", "其他会话正在编辑，请重新核对编辑权。") from error
                else:
                    updated = connection.execute(
                        text(
                            "UPDATE chapter_lease SET token = :token, owner_id = :owner_id, "
                            "session_token = :session_token, expires_at = :expires_at "
                            "WHERE " + condition
                        ),
                        {**payload, **comparison},
                    )
                    if updated.rowcount != 1:
                        raise DomainError(423, "LOCK_LOST", "编辑权已失效，请重新取得编辑权后再操作。")
            _save_projects(
                connection, before_projects, after_projects, before_teams, after_teams, loaded_project_ids,
            )


def _lease_snapshot(state: DemoState) -> dict:
    snapshot = {}
    for chapter_id, chapter in state.chapters.items():
        lease = chapter.lock
        snapshot[chapter_id] = None if lease is None else (
            lease.token, lease.owner_id, lease.session_token, float(lease.expires_at),
        )
    return snapshot


def _same_receipt(previous: dict, receipt: dict) -> bool:
    return (previous.get("fingerprint") == receipt.get("fingerprint")
            and previous.get("result") == receipt.get("result"))


def _project_snapshot(state: DemoState) -> dict:
    return {
        project.id: (
            project.name, project.company_id, int(project.revision),
            project.tender_number, project.deadline, bool(project.sensitive),
        )
        for project in state.projects.values()
    }


def _team_snapshot(state: DemoState) -> dict:
    return {
        project_id: json.dumps(team, ensure_ascii=False, sort_keys=True)
        for project_id, team in state.project_teams.items()
    }


def _save_projects(connection, before_projects: dict, after_projects: dict,
                   before_teams: dict, after_teams: dict, loaded_project_ids: set[str]) -> None:
    from sqlalchemy import text

    project_ids = set(before_projects) | set(after_projects) | set(before_teams) | set(after_teams)
    for project_id in project_ids:
        previous = before_projects.get(project_id)
        current = after_projects.get(project_id)
        previous_team = before_teams.get(project_id)
        current_team = after_teams.get(project_id)
        if previous == current and previous_team == current_team:
            continue
        loaded = project_id in loaded_project_ids
        if current is None:
            if loaded:
                connection.execute(
                    text("DELETE FROM demo_project_team WHERE project_id = :id"),
                    {"id": project_id},
                )
                connection.execute(text("DELETE FROM demo_project WHERE id = :id"), {"id": project_id})
            continue
        name, company_id, revision, tender_number, deadline, sensitive = current
        payload = {
            "id": project_id,
            "name": name,
            "company_id": company_id,
            "revision": revision,
            "tender_number": tender_number,
            "deadline": deadline,
            "is_sensitive": 1 if sensitive else 0,
        }
        if not loaded:
            connection.execute(
                text(
                    "INSERT INTO demo_project "
                    "(id, name, company_id, revision, tender_number, deadline, is_sensitive) "
                    "VALUES (:id, :name, :company_id, :revision, :tender_number, :deadline, :is_sensitive)"
                ),
                payload,
            )
        elif previous != current:
            expected = previous[2]
            result = connection.execute(
                text(
                    "UPDATE demo_project SET name = :name, company_id = :company_id, revision = :revision, "
                    "tender_number = :tender_number, deadline = :deadline, is_sensitive = :is_sensitive "
                    "WHERE id = :id AND revision = :expected"
                ),
                {**payload, "expected": expected},
            )
            if result.rowcount != 1:
                raise DomainError(409, "REVISION_CONFLICT", "项目已被其他会话更新，请刷新后再保存。")
        if current_team is None:
            if loaded or previous is not None and previous != current:
                connection.execute(
                    text("DELETE FROM demo_project_team WHERE project_id = :id"),
                    {"id": project_id},
                )
            continue
        if not loaded or previous_team is None:
            connection.execute(
                text(
                    "INSERT INTO demo_project_team (project_id, team_json) "
                    "VALUES (:id, CAST(:team_json AS JSON))"
                ),
                {"id": project_id, "team_json": current_team},
            )
        elif previous_team != current_team:
            connection.execute(
                text("UPDATE demo_project_team SET team_json = CAST(:team_json AS JSON) WHERE project_id = :id"),
                {"id": project_id, "team_json": current_team},
            )


def repository_from_environment():
    url = database_url()
    if not url:
        return MemoryRepository()
    return MysqlConnectionRepository(url)
