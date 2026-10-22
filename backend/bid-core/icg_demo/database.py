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
from .domain import Chapter, DemoState, DomainError, Lease, Project, iso_time

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


def _parse_db_timestamp(val) -> float | None:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, datetime):
        return _as_timestamp(val)
    return None


def _to_utc_naive(val) -> datetime | None:
    if val is None:
        return None
    if isinstance(val, datetime):
        if val.tzinfo is not None:
            return val.astimezone(timezone.utc).replace(tzinfo=None)
        return val
    try:
        return datetime.fromtimestamp(float(val), timezone.utc).replace(tzinfo=None)
    except Exception:
        return None


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

    def read_chapter(self, chapter_id: str) -> dict | None:
        return read_chapter(self.engine, chapter_id)

    def save_chapter(self, chapter: Chapter | dict, expected_revision: int | None = None, updated_at: datetime | None = None) -> None:
        save_chapter(self.engine, chapter, expected_revision=expected_revision, updated_at=updated_at)

    def commit_chapter_version(self, chapter_id: str, content: str, expected_revision: int,
                               new_revision: int, created_by: str,
                               updated_at: datetime | None = None) -> dict:
        return commit_chapter_version(self.engine, chapter_id, content, expected_revision,
                                      new_revision, created_by, updated_at=updated_at)

    def save_check(self, check_data: dict, updated_at: datetime | None = None) -> None:
        save_check(self.engine, check_data, updated_at=updated_at)

    def read_check(self, check_id: str) -> dict | None:
        return read_check(self.engine, check_id)

    def list_checks_by_project(self, project_id: str, volume_id: str | None = None, limit: int = 50, offset: int = 0) -> list[dict]:
        return list_checks_by_project(self.engine, project_id, volume_id=volume_id, limit=limit, offset=offset)

    def delete_check(self, check_id: str) -> bool:
        return delete_check(self.engine, check_id)

    def save_export(self, export_data: dict, updated_at: datetime | None = None) -> None:
        save_export(self.engine, export_data, updated_at=updated_at)

    def read_export(self, export_id: str) -> dict | None:
        return read_export(self.engine, export_id)

    def update_export_status(self, export_id: str, status: str, file_path: str | None = None, file_size: int | None = None) -> bool:
        return update_export_status(self.engine, export_id, status, file_path=file_path, file_size=file_size)

    def list_exports_by_project(self, project_id: str, export_type: str | None = None, limit: int = 50, offset: int = 0) -> tuple[list[dict], int]:
        return list_exports_by_project(self.engine, project_id, export_type=export_type, limit=limit, offset=offset)

    def delete_export(self, export_id: str) -> bool:
        return delete_export(self.engine, export_id)

    def save_library_item(self, item_data: dict, expected_revision: int | None = None, updated_at: datetime | None = None) -> None:
        save_library_item(self.engine, item_data, expected_revision=expected_revision, updated_at=updated_at)

    def read_library_item(self, item_id: str) -> dict | None:
        return read_library_item(self.engine, item_id)

    def list_library_items(self, company_id: str, category: str | None = None, status: str | None = None, limit: int = 50, offset: int = 0) -> tuple[list[dict], int]:
        return list_library_items(self.engine, company_id, category=category, status=status, limit=limit, offset=offset)

    def delete_library_item(self, item_id: str) -> bool:
        return delete_library_item(self.engine, item_id)

    def commit_library_revision(self, item_id: str, payload: dict, expected_revision: int, new_revision: int, changed_by: str, change_reason: str | None = None, updated_at: datetime | None = None) -> dict:
        return commit_library_revision(self.engine, item_id, payload, expected_revision, new_revision, changed_by, change_reason=change_reason, updated_at=updated_at)

    def list_library_revisions(self, item_id: str) -> list[dict]:
        return list_library_revisions(self.engine, item_id)

    def save_sla_template(self, template_data: dict, expected_revision: int | None = None, updated_at: datetime | None = None) -> None:
        save_sla_template(self.engine, template_data, expected_revision=expected_revision, updated_at=updated_at)

    def read_sla_template(self, template_id: str) -> dict | None:
        return read_sla_template(self.engine, template_id)

    def list_sla_templates(self, company_id: str, level: str | None = None) -> list[dict]:
        return list_sla_templates(self.engine, company_id, level=level)

    def delete_sla_template(self, template_id: str) -> bool:
        return delete_sla_template(self.engine, template_id)

    def save_workflow(self, workflow_data: dict, expected_revision: int | None = None, updated_at: datetime | None = None) -> None:
        save_workflow(self.engine, workflow_data, expected_revision=expected_revision, updated_at=updated_at)

    def read_workflow(self, project_id: str) -> dict | None:
        return read_workflow(self.engine, project_id)

    def delete_workflow(self, project_id: str) -> bool:
        return delete_workflow(self.engine, project_id)

    def save_job(self, job_data: dict, updated_at: datetime | None = None) -> None:
        save_job(self.engine, job_data, updated_at=updated_at)

    def read_job(self, job_id: str) -> dict | None:
        return read_job(self.engine, job_id)

    def update_job_progress(self, job_id: str, progress: int, status: str | None = None, step_name: str | None = None, error_json: Any = None, result_json: Any = None, updated_at: datetime | None = None) -> bool:
        return update_job_progress(self.engine, job_id, progress, status=status, step_name=step_name, error_json=error_json, result_json=result_json, updated_at=updated_at)

    def list_jobs_by_project(self, project_id: str, job_type: str | None = None, status: str | None = None, limit: int = 50, offset: int = 0) -> tuple[list[dict], int]:
        return list_jobs_by_project(self.engine, project_id, job_type=job_type, status=status, limit=limit, offset=offset)

    def delete_job(self, job_id: str) -> bool:
        return delete_job(self.engine, job_id)

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
            before_configs = dict(state.model_configs)
            before_bindings = dict(state.project_model_configs)
            result = operation(state)
            self._save_shared(
                before_sessions, dict(state.sessions), before_receipts, state.workflow_receipts,
                before_leases, _lease_snapshot(state),
                before_projects, _project_snapshot(state), before_teams, _team_snapshot(state),
                loaded_project_ids,
                before_configs, dict(state.model_configs),
                before_bindings, dict(state.project_model_configs),
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
            try:
                leases = connection.execute(text(
                    "SELECT chapter_id, token, owner_id, session_token, expires_at, "
                    "acquired_at, heartbeat_at, lock_reason, taken_over_from_user_id, "
                    "takeover_reason, released_at, release_reason, company_id, record_version "
                    "FROM chapter_lease WHERE released_at IS NULL"
                )).all()
                loaded = {
                    row[0]: Lease(
                        token=row[1],
                        owner_id=row[2],
                        session_token=row[3],
                        expires_at=_as_timestamp(row[4]),
                        acquired_at=_as_timestamp(row[5]) if row[5] else None,
                        heartbeat_at=_as_timestamp(row[6]) if row[6] else None,
                        lock_reason=row[7],
                        taken_over_from_user_id=row[8],
                        takeover_reason=row[9],
                        released_at=_as_timestamp(row[10]) if row[10] else None,
                        release_reason=row[11],
                        company_id=row[12],
                        record_version=int(row[13]) if row[13] is not None else 1,
                    )
                    for row in leases
                }
            except Exception:
                leases = connection.execute(text(
                    "SELECT chapter_id, token, owner_id, session_token, expires_at FROM chapter_lease"
                )).all()
                loaded = {
                    chapter_id: Lease(token, owner_id, session_token, _as_timestamp(expires_at))
                    for chapter_id, token, owner_id, session_token, expires_at in leases
                }
            try:
                projects = connection.execute(text(
                    "SELECT id, name, company_id, revision, tender_number, deadline, is_sensitive, "
                    "tender_type, budget_amount_cents, deadline_at, security_level, industry, is_archived, "
                    "created_by, created_at, updated_by, updated_at, record_version, is_deleted "
                    "FROM demo_project"
                )).all()
                has_full_project_schema = True
            except Exception:
                projects = connection.execute(text(
                    "SELECT id, name, company_id, revision, tender_number, deadline, is_sensitive FROM demo_project"
                )).all()
                has_full_project_schema = False
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
        for chapter_id, chapter in state.chapters.items():
            chapter.lock = loaded.get(chapter_id)
        loaded_project_ids.clear()
        loaded_project_ids.update(project_id for project_id, *_rest in projects)
        if has_full_project_schema:
            for (
                project_id, name, company_id, revision, tender_number, deadline, sensitive,
                tender_type, budget_amount_cents, deadline_at, security_level, industry, is_archived,
                created_by, created_at, updated_by, updated_at, record_version, is_deleted
            ) in projects:
                state.projects[project_id] = Project(
                    id=project_id,
                    name=name,
                    company_id=company_id,
                    revision=int(revision),
                    tender_number=tender_number or "",
                    deadline=deadline or "",
                    sensitive=bool(sensitive),
                    tender_type=tender_type or "comprehensive",
                    budget_amount_cents=int(budget_amount_cents) if budget_amount_cents is not None else 0,
                    deadline_at=_parse_db_timestamp(deadline_at),
                    security_level=security_level or "internal",
                    industry=industry or "it",
                    is_archived=bool(is_archived),
                    created_by=created_by or "",
                    created_at=_parse_db_timestamp(created_at),
                    updated_by=updated_by or "",
                    updated_at=_parse_db_timestamp(updated_at),
                    record_version=int(record_version) if record_version is not None else 1,
                    is_deleted=bool(is_deleted),
                )
        else:
            for project_id, name, company_id, revision, tender_number, deadline, sensitive in projects:
                state.projects[project_id] = Project(
                    project_id, name, company_id, int(revision),
                    tender_number or "", deadline or "", bool(sensitive),
                )
        for project_id, team_json in teams:
            state.project_teams[project_id] = _json_value(team_json)
        try:
            with self.engine.begin() as connection:
                configs = connection.execute(text(
                    "SELECT id, company_id, name, provider, base_url, model, encrypted_api_key, "
                    "api_key_masked, is_local, allow_sensitive, stream_enabled, json_mode_enabled, "
                    "revision, timeout_seconds, max_tokens FROM demo_model_config"
                )).all()
                bindings = connection.execute(text(
                    "SELECT project_id, model_config_id FROM demo_project_model_config"
                )).all()
            from .model_config_storage import ModelConfig
            for (cid, company_id, name, provider, base_url, model, encrypted_api_key,
                 api_key_masked, is_local, allow_sensitive, stream_enabled, json_mode_enabled,
                 revision, timeout_seconds, max_tokens) in configs:
                state.model_configs[cid] = ModelConfig(
                    id=cid, company_id=company_id, name=name, provider=provider,
                    base_url=base_url, model=model, encrypted_api_key=encrypted_api_key,
                    api_key_masked=api_key_masked, is_local=bool(is_local),
                    allow_sensitive=bool(allow_sensitive), stream_enabled=bool(stream_enabled),
                    json_mode_enabled=bool(json_mode_enabled), revision=int(revision),
                    timeout_seconds=float(timeout_seconds), max_tokens=int(max_tokens),
                )
            for pid, mid in bindings:
                state.project_model_configs[pid] = mid
        except Exception:
            pass
        try:
            with self.engine.begin() as connection:
                chapters_rows = connection.execute(text(
                    "SELECT id, project_id, volume, title, content, revision, assignee_id, updated_at "
                    "FROM demo_chapter"
                )).all()
                versions_rows = connection.execute(text(
                    "SELECT id, chapter_id, version_number, content, created_by, created_at "
                    "FROM demo_chapter_version ORDER BY version_number ASC"
                )).all()
            versions_by_cid: dict[str, list[dict]] = {}
            for vid, cid, v_num, v_content, v_actor, v_created in versions_rows:
                versions_by_cid.setdefault(cid, []).append({
                    "id": vid,
                    "chapter_id": cid,
                    "revision": int(v_num),
                    "version_number": int(v_num),
                    "content": v_content,
                    "actor_id": v_actor,
                    "created_by": v_actor,
                    "created_at": iso_time(_as_timestamp(v_created)) if isinstance(v_created, datetime) else str(v_created),
                })
            for cid, pid, volume, title, content, rev, assignee_id, updated_at in chapters_rows:
                if cid in state.chapters:
                    ch = state.chapters[cid]
                    ch.project_id = pid
                    ch.volume = volume
                    ch.title = title
                    ch.content = content
                    ch.revision = int(rev)
                    ch.assignee_id = assignee_id
                    if cid in versions_by_cid:
                        ch.versions = versions_by_cid[cid]
                else:
                    state.chapters[cid] = Chapter(
                        id=cid,
                        project_id=pid,
                        title=title,
                        volume=volume,
                        content=content,
                        revision=int(rev),
                        assignee_id=assignee_id,
                        versions=versions_by_cid.get(cid, []),
                    )
        except Exception:
            pass

    def _save_shared(self, before_sessions: dict, after_sessions: dict,
                     before_receipts: dict, after_receipts: dict,
                     before_leases: dict, after_leases: dict,
                     before_projects: dict, after_projects: dict,
                     before_teams: dict, after_teams: dict,
                     loaded_project_ids: set[str],
                     before_configs: dict | None = None, after_configs: dict | None = None,
                     before_bindings: dict | None = None, after_bindings: dict | None = None) -> None:
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
                token, owner_id, session_token, expires_at = current[:4]
                payload = {
                    "chapter_id": chapter_id,
                    "token": token,
                    "owner_id": owner_id,
                    "session_token": session_token,
                    "expires_at": _utc_naive(expires_at),
                    "acquired_at": _utc_naive(current[4]) if len(current) > 4 and current[4] else None,
                    "heartbeat_at": _utc_naive(current[5]) if len(current) > 5 and current[5] else None,
                    "lock_reason": current[6] if len(current) > 6 else None,
                    "taken_over_from_user_id": current[7] if len(current) > 7 else None,
                    "takeover_reason": current[8] if len(current) > 8 else None,
                    "released_at": _utc_naive(current[9]) if len(current) > 9 and current[9] else None,
                    "release_reason": current[10] if len(current) > 10 else None,
                    "company_id": current[11] if len(current) > 11 else None,
                    "record_version": current[12] if len(current) > 12 and current[12] is not None else 1,
                }
                if previous is None:
                    try:
                        connection.execute(
                            text(
                                "INSERT INTO chapter_lease "
                                "(chapter_id, token, owner_id, session_token, expires_at, "
                                "acquired_at, heartbeat_at, lock_reason, taken_over_from_user_id, "
                                "takeover_reason, released_at, release_reason, company_id, record_version) "
                                "VALUES (:chapter_id, :token, :owner_id, :session_token, :expires_at, "
                                ":acquired_at, :heartbeat_at, :lock_reason, :taken_over_from_user_id, "
                                ":takeover_reason, :released_at, :release_reason, :company_id, :record_version)"
                            ),
                            payload,
                        )
                    except Exception:
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
                    try:
                        updated = connection.execute(
                            text(
                                "UPDATE chapter_lease SET token = :token, owner_id = :owner_id, "
                                "session_token = :session_token, expires_at = :expires_at, "
                                "heartbeat_at = :heartbeat_at, lock_reason = :lock_reason, "
                                "record_version = :record_version "
                                "WHERE " + condition
                            ),
                            {**payload, **comparison},
                        )
                    except Exception:
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
            if before_configs is not None and after_configs is not None:
                _save_model_configs(
                    connection, before_configs, after_configs,
                    before_bindings or {}, after_bindings or {},
                )


def _save_model_configs(connection, before_configs: dict, after_configs: dict,
                       before_bindings: dict, after_bindings: dict) -> None:
    from sqlalchemy import text
    try:
        for cid, cfg in after_configs.items():
            prev = before_configs.get(cid)
            if prev == cfg:
                continue
            payload = {
                "id": cfg.id,
                "company_id": cfg.company_id,
                "name": cfg.name,
                "provider": cfg.provider,
                "base_url": cfg.base_url,
                "model": cfg.model,
                "encrypted_api_key": cfg.encrypted_api_key,
                "api_key_masked": cfg.api_key_masked,
                "is_local": 1 if cfg.is_local else 0,
                "allow_sensitive": 1 if cfg.allow_sensitive else 0,
                "stream_enabled": 1 if cfg.stream_enabled else 0,
                "json_mode_enabled": 1 if cfg.json_mode_enabled else 0,
                "revision": cfg.revision,
                "timeout_seconds": cfg.timeout_seconds,
                "max_tokens": cfg.max_tokens,
            }
            if prev is None:
                connection.execute(
                    text(
                        "INSERT INTO demo_model_config (id, company_id, name, provider, base_url, model, "
                        "encrypted_api_key, api_key_masked, is_local, allow_sensitive, stream_enabled, "
                        "json_mode_enabled, revision, timeout_seconds, max_tokens) "
                        "VALUES (:id, :company_id, :name, :provider, :base_url, :model, :encrypted_api_key, "
                        ":api_key_masked, :is_local, :allow_sensitive, :stream_enabled, :json_mode_enabled, "
                        ":revision, :timeout_seconds, :max_tokens)"
                    ),
                    payload,
                )
            else:
                connection.execute(
                    text(
                        "UPDATE demo_model_config SET name = :name, provider = :provider, base_url = :base_url, "
                        "model = :model, encrypted_api_key = :encrypted_api_key, api_key_masked = :api_key_masked, "
                        "is_local = :is_local, allow_sensitive = :allow_sensitive, stream_enabled = :stream_enabled, "
                        "json_mode_enabled = :json_mode_enabled, revision = :revision, "
                        "timeout_seconds = :timeout_seconds, max_tokens = :max_tokens WHERE id = :id"
                    ),
                    payload,
                )
        for pid, mid in after_bindings.items():
            if before_bindings.get(pid) != mid:
                connection.execute(
                    text(
                        "INSERT INTO demo_project_model_config (project_id, model_config_id) "
                        "VALUES (:project_id, :model_config_id) "
                        "ON DUPLICATE KEY UPDATE model_config_id = :model_config_id"
                    ),
                    {"project_id": pid, "model_config_id": mid},
                )
    except Exception:
        pass


def _lease_snapshot(state: DemoState) -> dict:
    snapshot = {}
    for chapter_id, chapter in state.chapters.items():
        lease = chapter.lock
        snapshot[chapter_id] = None if lease is None else (
            lease.token, lease.owner_id, lease.session_token, float(lease.expires_at),
            lease.acquired_at, lease.heartbeat_at, lease.lock_reason,
            lease.taken_over_from_user_id, lease.takeover_reason,
            lease.released_at, lease.release_reason, lease.company_id, lease.record_version,
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
            project.tender_type, (int(project.budget_amount_cents) if project.budget_amount_cents is not None else 0),
            project.deadline_at, project.security_level, project.industry,
            bool(project.is_archived), project.created_by, project.created_at,
            project.updated_by, project.updated_at, (int(project.record_version) if project.record_version is not None else 1),
            bool(project.is_deleted),
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

        if len(current) >= 18:
            (
                name, company_id, revision, tender_number, deadline, sensitive,
                tender_type, budget_amount_cents, deadline_at, security_level, industry,
                is_archived, created_by, created_at, updated_by, updated_at,
                record_version, is_deleted,
            ) = current[:18]
        else:
            name, company_id, revision, tender_number, deadline, sensitive = current[:6]
            tender_type, budget_amount_cents, deadline_at, security_level, industry = "comprehensive", 0, None, "internal", "it"
            is_archived, created_by, created_at, updated_by, updated_at = False, "", None, "", None
            record_version, is_deleted = 1, False

        payload = {
            "id": project_id,
            "name": name,
            "company_id": company_id,
            "revision": revision,
            "tender_number": tender_number,
            "deadline": deadline,
            "is_sensitive": 1 if sensitive else 0,
            "tender_type": tender_type or "comprehensive",
            "budget_amount_cents": int(budget_amount_cents) if budget_amount_cents is not None else 0,
            "deadline_at": _to_utc_naive(deadline_at),
            "security_level": security_level or "internal",
            "industry": industry or "it",
            "is_archived": 1 if is_archived else 0,
            "created_by": created_by or "",
            "created_at": _to_utc_naive(created_at),
            "updated_by": updated_by or "",
            "updated_at": _to_utc_naive(updated_at),
            "record_version": int(record_version) if record_version is not None else 1,
            "is_deleted": 1 if is_deleted else 0,
        }
        if not loaded:
            try:
                connection.execute(
                    text(
                        "INSERT INTO demo_project "
                        "(id, name, company_id, revision, tender_number, deadline, is_sensitive, "
                        "tender_type, budget_amount_cents, deadline_at, security_level, industry, is_archived, "
                        "created_by, created_at, updated_by, updated_at, record_version, is_deleted) "
                        "VALUES (:id, :name, :company_id, :revision, :tender_number, :deadline, :is_sensitive, "
                        ":tender_type, :budget_amount_cents, :deadline_at, :security_level, :industry, :is_archived, "
                        ":created_by, :created_at, :updated_by, :updated_at, :record_version, :is_deleted)"
                    ),
                    payload,
                )
            except Exception:
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
            try:
                result = connection.execute(
                    text(
                        "UPDATE demo_project SET name = :name, company_id = :company_id, revision = :revision, "
                        "tender_number = :tender_number, deadline = :deadline, is_sensitive = :is_sensitive, "
                        "tender_type = :tender_type, budget_amount_cents = :budget_amount_cents, "
                        "deadline_at = :deadline_at, security_level = :security_level, industry = :industry, "
                        "is_archived = :is_archived, created_by = :created_by, created_at = :created_at, "
                        "updated_by = :updated_by, updated_at = :updated_at, "
                        "record_version = :record_version, is_deleted = :is_deleted "
                        "WHERE id = :id AND revision = :expected"
                    ),
                    {**payload, "expected": expected},
                )
            except Exception:
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


def read_chapter(target, chapter_id: str) -> dict | None:
    from sqlalchemy import text

    def _execute_read(connection) -> dict | None:
        row = connection.execute(
            text(
                "SELECT id, project_id, volume, title, content, revision, assignee_id, updated_at "
                "FROM demo_chapter WHERE id = :id"
            ),
            {"id": chapter_id},
        ).one_or_none()
        if row is None:
            return None

        version_rows = connection.execute(
            text(
                "SELECT id, chapter_id, version_number, content, created_by, created_at "
                "FROM demo_chapter_version WHERE chapter_id = :chapter_id ORDER BY version_number ASC"
            ),
            {"chapter_id": chapter_id},
        ).all()

        versions = [
            {
                "id": v.id,
                "chapter_id": v.chapter_id,
                "revision": int(v.version_number),
                "version_number": int(v.version_number),
                "content": v.content,
                "actor_id": v.created_by,
                "created_by": v.created_by,
                "created_at": iso_time(_as_timestamp(v.created_at)) if isinstance(v.created_at, datetime) else str(v.created_at),
            }
            for v in version_rows
        ]

        return {
            "id": row.id,
            "project_id": row.project_id,
            "volume": row.volume,
            "title": row.title,
            "content": row.content,
            "revision": int(row.revision),
            "assignee_id": row.assignee_id,
            "updated_at": row.updated_at,
            "versions": versions,
        }

    engine = target.engine if hasattr(target, "engine") else target
    if hasattr(engine, "connect"):
        with engine.connect() as connection:
            return _execute_read(connection)
    return _execute_read(engine)


def save_chapter(target, chapter: Chapter | dict, expected_revision: int | None = None, updated_at: datetime | None = None) -> None:
    from sqlalchemy import text
    from uuid import uuid4

    if hasattr(chapter, "id"):
        cid = chapter.id
        pid = chapter.project_id
        volume = chapter.volume
        title = chapter.title
        content = chapter.content
        revision = int(chapter.revision)
        assignee_id = chapter.assignee_id
        versions = list(getattr(chapter, "versions", []))
    else:
        cid = chapter["id"]
        pid = chapter["project_id"]
        volume = chapter["volume"]
        title = chapter["title"]
        content = chapter.get("content", "")
        revision = int(chapter.get("revision", 1))
        assignee_id = chapter.get("assignee_id")
        versions = list(chapter.get("versions", []))

    now = updated_at or datetime.now(timezone.utc).replace(tzinfo=None)
    if isinstance(now, datetime) and now.tzinfo is not None:
        now = now.astimezone(timezone.utc).replace(tzinfo=None)

    def _execute_save(connection) -> None:
        existing = connection.execute(
            text("SELECT revision FROM demo_chapter WHERE id = :id"),
            {"id": cid},
        ).one_or_none()

        payload = {
            "id": cid,
            "project_id": pid,
            "volume": volume,
            "title": title,
            "content": content,
            "revision": revision,
            "assignee_id": assignee_id,
            "updated_at": now,
        }

        if existing is None:
            connection.execute(
                text(
                    "INSERT INTO demo_chapter (id, project_id, volume, title, content, revision, assignee_id, updated_at) "
                    "VALUES (:id, :project_id, :volume, :title, :content, :revision, :assignee_id, :updated_at)"
                ),
                payload,
            )
        else:
            if expected_revision is not None:
                result = connection.execute(
                    text(
                        "UPDATE demo_chapter SET project_id = :project_id, volume = :volume, "
                        "title = :title, content = :content, revision = :revision, "
                        "assignee_id = :assignee_id, updated_at = :updated_at "
                        "WHERE id = :id AND revision = :expected_revision"
                    ),
                    {**payload, "expected_revision": int(expected_revision)},
                )
                if result.rowcount != 1:
                    raise DomainError(409, "REVISION_CONFLICT", "章节已被其他会话更新，请刷新并核对最新版本。")
            else:
                connection.execute(
                    text(
                        "UPDATE demo_chapter SET project_id = :project_id, volume = :volume, "
                        "title = :title, content = :content, revision = :revision, "
                        "assignee_id = :assignee_id, updated_at = :updated_at "
                        "WHERE id = :id"
                    ),
                    payload,
                )

        for v in versions:
            v_num = int(v.get("revision", v.get("version_number", 1)))
            v_content = v.get("content", "")
            v_actor = v.get("actor_id", v.get("created_by", "system"))
            v_created = v.get("created_at")
            if v_created is None:
                v_time = now
            elif isinstance(v_created, datetime):
                v_time = _utc_naive(v_created)
            else:
                try:
                    v_time = datetime.fromisoformat(v_created).astimezone(timezone.utc).replace(tzinfo=None)
                except Exception:
                    v_time = now

            exists = connection.execute(
                text("SELECT 1 FROM demo_chapter_version WHERE chapter_id = :chapter_id AND version_number = :v_num"),
                {"chapter_id": cid, "v_num": v_num},
            ).scalar()
            if not exists:
                v_id = v.get("id") or f"ver-{uuid4().hex}"
                connection.execute(
                    text(
                        "INSERT INTO demo_chapter_version (id, chapter_id, version_number, content, created_by, created_at) "
                        "VALUES (:id, :chapter_id, :version_number, :content, :created_by, :created_at)"
                    ),
                    {
                        "id": v_id,
                        "chapter_id": cid,
                        "version_number": v_num,
                        "content": v_content,
                        "created_by": v_actor,
                        "created_at": v_time,
                    },
                )

    engine = target.engine if hasattr(target, "engine") else target
    if hasattr(engine, "begin"):
        with engine.begin() as connection:
            _execute_save(connection)
    else:
        _execute_save(engine)


def commit_chapter_version(
    target,
    chapter_id: str,
    content: str,
    expected_revision: int,
    new_revision: int,
    created_by: str,
    updated_at: datetime | None = None,
) -> dict:
    from sqlalchemy import text
    from uuid import uuid4

    now = updated_at or datetime.now(timezone.utc).replace(tzinfo=None)
    if isinstance(now, datetime) and now.tzinfo is not None:
        now = now.astimezone(timezone.utc).replace(tzinfo=None)

    def _execute_commit(connection) -> dict:
        result = connection.execute(
            text(
                "UPDATE demo_chapter SET content = :content, revision = :new_rev, updated_at = :updated_at "
                "WHERE id = :id AND revision = :old_rev"
            ),
            {
                "id": chapter_id,
                "content": content,
                "new_rev": int(new_revision),
                "old_rev": int(expected_revision),
                "updated_at": now,
            },
        )
        if result.rowcount != 1:
            raise DomainError(409, "REVISION_CONFLICT", "章节已被其他会话更新，请刷新并核对最新版本。")

        version_id = f"ver-{uuid4().hex}"
        connection.execute(
            text(
                "INSERT INTO demo_chapter_version (id, chapter_id, version_number, content, created_by, created_at) "
                "VALUES (:id, :chapter_id, :version_number, :content, :created_by, :created_at)"
            ),
            {
                "id": version_id,
                "chapter_id": chapter_id,
                "version_number": int(new_revision),
                "content": content,
                "created_by": created_by,
                "created_at": now,
            },
        )
        return {
            "id": version_id,
            "chapter_id": chapter_id,
            "revision": int(new_revision),
            "version_number": int(new_revision),
            "content": content,
            "actor_id": created_by,
            "created_by": created_by,
            "created_at": iso_time(_as_timestamp(now)),
        }

    engine = target.engine if hasattr(target, "engine") else target
    if hasattr(engine, "begin"):
        with engine.begin() as connection:
            return _execute_commit(connection)
    return _execute_commit(engine)


def save_check(target, check_data: dict, updated_at: datetime | None = None) -> None:
    from sqlalchemy import text

    cid = check_data["id"]
    pid = check_data["project_id"]
    issues = list(check_data.get("issues_json", check_data.get("issues", [])))
    if "blocking_count" in check_data:
        blocking_count = int(check_data["blocking_count"])
    else:
        blocking_count = sum(1 for i in issues if i.get("severity") in ("blocking", "blocker"))
    if "warning_count" in check_data:
        warning_count = int(check_data["warning_count"])
    else:
        warning_count = sum(1 for i in issues if i.get("severity") == "warning")
    status = check_data.get("status")
    if not status:
        if blocking_count > 0:
            status = "blocked"
        elif warning_count > 0:
            status = "warning"
        else:
            status = "passed"
    issues_json_str = json.dumps(issues, ensure_ascii=False)

    now = updated_at or datetime.now(timezone.utc).replace(tzinfo=None)
    if isinstance(now, datetime) and now.tzinfo is not None:
        now = now.astimezone(timezone.utc).replace(tzinfo=None)

    raw_created = check_data.get("created_at") or now
    if isinstance(raw_created, datetime):
        created_at = raw_created.astimezone(timezone.utc).replace(tzinfo=None) if raw_created.tzinfo else raw_created
    elif isinstance(raw_created, str):
        try:
            created_at = datetime.fromisoformat(raw_created).astimezone(timezone.utc).replace(tzinfo=None)
        except Exception:
            created_at = now
    else:
        created_at = now

    def _execute_save(connection) -> None:
        connection.execute(
            text(
                "INSERT INTO demo_check (id, project_id, volume_id, status, blocking_count, warning_count, "
                "issues_json, created_at, updated_at) "
                "VALUES (:id, :project_id, :volume_id, :status, :blocking_count, :warning_count, "
                "CAST(:issues_json AS JSON), :created_at, :updated_at) "
                "ON DUPLICATE KEY UPDATE "
                "project_id = VALUES(project_id), "
                "volume_id = VALUES(volume_id), "
                "status = VALUES(status), "
                "blocking_count = VALUES(blocking_count), "
                "warning_count = VALUES(warning_count), "
                "issues_json = VALUES(issues_json), "
                "updated_at = VALUES(updated_at)"
            ),
            {
                "id": cid,
                "project_id": pid,
                "volume_id": volume_id,
                "status": status,
                "blocking_count": blocking_count,
                "warning_count": warning_count,
                "issues_json": issues_json_str,
                "created_at": created_at,
                "updated_at": now,
            },
        )

    engine = target.engine if hasattr(target, "engine") else target
    if hasattr(engine, "begin"):
        with engine.begin() as connection:
            _execute_save(connection)
    else:
        _execute_save(engine)


def read_check(target, check_id: str) -> dict | None:
    from sqlalchemy import text

    def _execute_read(connection) -> dict | None:
        row = connection.execute(
            text(
                "SELECT id, project_id, volume_id, status, blocking_count, warning_count, "
                "issues_json, created_at, updated_at FROM demo_check WHERE id = :id"
            ),
            {"id": check_id},
        ).one_or_none()
        if row is None:
            return None
        issues = _json_value(row.issues_json) if row.issues_json is not None else []
        return {
            "id": row.id,
            "project_id": row.project_id,
            "volume_id": row.volume_id,
            "status": row.status,
            "blocking_count": int(row.blocking_count),
            "warning_count": int(row.warning_count),
            "issues": issues,
            "issues_json": issues,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }

    engine = target.engine if hasattr(target, "engine") else target
    if hasattr(engine, "connect"):
        with engine.connect() as connection:
            return _execute_read(connection)
    return _execute_read(engine)


def list_checks_by_project(target, project_id: str, volume_id: str | None = None, limit: int = 50, offset: int = 0) -> list[dict]:
    from sqlalchemy import text

    def _execute_list(connection) -> list[dict]:
        params = {"project_id": project_id, "limit": limit, "offset": offset}
        where_clause = "WHERE project_id = :project_id"
        if volume_id is not None:
            where_clause += " AND volume_id = :volume_id"
            params["volume_id"] = volume_id

        sql = (
            f"SELECT id, project_id, volume_id, status, blocking_count, warning_count, "
            f"issues_json, created_at, updated_at FROM demo_check "
            f"{where_clause} ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
        )
        rows = connection.execute(text(sql), params).all()
        result = []
        for row in rows:
            issues = _json_value(row.issues_json) if row.issues_json is not None else []
            result.append({
                "id": row.id,
                "project_id": row.project_id,
                "volume_id": row.volume_id,
                "status": row.status,
                "blocking_count": int(row.blocking_count),
                "warning_count": int(row.warning_count),
                "issues": issues,
                "issues_json": issues,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            })
        return result

    engine = target.engine if hasattr(target, "engine") else target
    if hasattr(engine, "connect"):
        with engine.connect() as connection:
            return _execute_list(connection)
    return _execute_list(engine)


def delete_check(target, check_id: str) -> bool:
    from sqlalchemy import text

    def _execute_delete(connection) -> bool:
        result = connection.execute(text("DELETE FROM demo_check WHERE id = :id"), {"id": check_id})
        return result.rowcount > 0

    engine = target.engine if hasattr(target, "engine") else target
    if hasattr(engine, "begin"):
        with engine.begin() as connection:
            return _execute_delete(connection)
    return _execute_delete(engine)


def save_export(target, export_data: dict, updated_at: datetime | None = None) -> None:
    from sqlalchemy import text

    eid = export_data["id"]
    pid = export_data["project_id"]
    export_type = export_data.get("export_type", "internal")
    status = export_data.get("status", "pending")
    format_type = export_data.get("format", "docx")
    file_path = export_data.get("file_path")
    file_size = export_data.get("file_size")
    snapshot = export_data.get("snapshot_json", export_data.get("snapshot"))
    snapshot_json_str = json.dumps(snapshot, ensure_ascii=False) if snapshot is not None else None
    created_by = export_data.get("created_by", "system")

    now = updated_at or datetime.now(timezone.utc).replace(tzinfo=None)
    if isinstance(now, datetime) and now.tzinfo is not None:
        now = now.astimezone(timezone.utc).replace(tzinfo=None)

    raw_created = export_data.get("created_at") or now
    if isinstance(raw_created, datetime):
        created_at = raw_created.astimezone(timezone.utc).replace(tzinfo=None) if raw_created.tzinfo else raw_created
    elif isinstance(raw_created, str):
        try:
            created_at = datetime.fromisoformat(raw_created).astimezone(timezone.utc).replace(tzinfo=None)
        except Exception:
            created_at = now
    else:
        created_at = now

    def _execute_save(connection) -> None:
        connection.execute(
            text(
                "INSERT INTO demo_export (id, project_id, export_type, status, format, file_path, "
                "file_size, snapshot_json, created_by, created_at) "
                "VALUES (:id, :project_id, :export_type, :status, :format, :file_path, "
                ":file_size, CAST(:snapshot_json AS JSON), :created_by, :created_at) "
                "ON DUPLICATE KEY UPDATE "
                "project_id = VALUES(project_id), "
                "export_type = VALUES(export_type), "
                "status = VALUES(status), "
                "format = VALUES(format), "
                "file_path = VALUES(file_path), "
                "file_size = VALUES(file_size), "
                "snapshot_json = VALUES(snapshot_json), "
                "created_by = VALUES(created_by)"
            ),
            {
                "id": eid,
                "project_id": pid,
                "export_type": export_type,
                "status": status,
                "format": format_type,
                "file_path": file_path,
                "file_size": file_size,
                "snapshot_json": snapshot_json_str,
                "created_by": created_by,
                "created_at": created_at,
            },
        )

    engine = target.engine if hasattr(target, "engine") else target
    if hasattr(engine, "begin"):
        with engine.begin() as connection:
            _execute_save(connection)
    else:
        _execute_save(engine)


def read_export(target, export_id: str) -> dict | None:
    from sqlalchemy import text

    def _execute_read(connection) -> dict | None:
        row = connection.execute(
            text(
                "SELECT id, project_id, export_type, status, format, file_path, file_size, "
                "snapshot_json, created_by, created_at FROM demo_export WHERE id = :id"
            ),
            {"id": export_id},
        ).one_or_none()
        if row is None:
            return None
        snapshot = _json_value(row.snapshot_json) if row.snapshot_json is not None else None
        return {
            "id": row.id,
            "project_id": row.project_id,
            "export_type": row.export_type,
            "status": row.status,
            "format": row.format,
            "file_path": row.file_path,
            "file_size": row.file_size,
            "snapshot": snapshot,
            "snapshot_json": snapshot,
            "created_by": row.created_by,
            "created_at": row.created_at,
        }

    engine = target.engine if hasattr(target, "engine") else target
    if hasattr(engine, "connect"):
        with engine.connect() as connection:
            return _execute_read(connection)
    return _execute_read(engine)


def update_export_status(target, export_id: str, status: str, file_path: str | None = None, file_size: int | None = None) -> bool:
    from sqlalchemy import text

    def _execute_update(connection) -> bool:
        clauses = ["status = :status"]
        params: dict = {"id": export_id, "status": status}
        if file_path is not None:
            clauses.append("file_path = :file_path")
            params["file_path"] = file_path
        if file_size is not None:
            clauses.append("file_size = :file_size")
            params["file_size"] = file_size

        sql = f"UPDATE demo_export SET {', '.join(clauses)} WHERE id = :id"
        result = connection.execute(text(sql), params)
        return result.rowcount > 0

    engine = target.engine if hasattr(target, "engine") else target
    if hasattr(engine, "begin"):
        with engine.begin() as connection:
            return _execute_update(connection)
    return _execute_update(engine)


def list_exports_by_project(target, project_id: str, export_type: str | None = None, limit: int = 50, offset: int = 0) -> tuple[list[dict], int]:
    from sqlalchemy import text

    def _execute_list(connection) -> tuple[list[dict], int]:
        params: dict = {"project_id": project_id}
        where_clause = "WHERE project_id = :project_id"
        if export_type is not None:
            where_clause += " AND export_type = :export_type"
            params["export_type"] = export_type

        count_sql = f"SELECT COUNT(*) FROM demo_export {where_clause}"
        total = connection.execute(text(count_sql), params).scalar() or 0

        data_params = {**params, "limit": limit, "offset": offset}
        data_sql = (
            f"SELECT id, project_id, export_type, status, format, file_path, file_size, snapshot_json, "
            f"created_by, created_at FROM demo_export {where_clause} ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
        )
        rows = connection.execute(text(data_sql), data_params).all()
        result = []
        for row in rows:
            snapshot = _json_value(row.snapshot_json) if row.snapshot_json is not None else None
            result.append({
                "id": row.id,
                "project_id": row.project_id,
                "export_type": row.export_type,
                "status": row.status,
                "format": row.format,
                "file_path": row.file_path,
                "file_size": row.file_size,
                "snapshot": snapshot,
                "snapshot_json": snapshot,
                "created_by": row.created_by,
                "created_at": row.created_at,
            })
        return result, total

    engine = target.engine if hasattr(target, "engine") else target
    if hasattr(engine, "connect"):
        with engine.connect() as connection:
            return _execute_list(connection)
    return _execute_list(engine)


def delete_export(target, export_id: str) -> bool:
    from sqlalchemy import text

    def _execute_delete(connection) -> bool:
        result = connection.execute(text("DELETE FROM demo_export WHERE id = :id"), {"id": export_id})
        return result.rowcount > 0

    engine = target.engine if hasattr(target, "engine") else target
    if hasattr(engine, "begin"):
        with engine.begin() as connection:
            return _execute_delete(connection)
    return _execute_delete(engine)


def save_library_item(target, item_data: dict, expected_revision: int | None = None, updated_at: datetime | None = None) -> None:
    from sqlalchemy import text

    iid = item_data["id"]
    company_id = item_data["company_id"]
    category = item_data.get("category", "qualification")
    name = item_data.get("name", "")
    status = item_data.get("status", "draft")
    is_starred = 1 if item_data.get("is_starred", False) else 0
    can_insert = 1 if item_data.get("can_insert", True) else 0
    is_sensitive = 1 if item_data.get("is_sensitive", False) else 0
    payload = item_data.get("payload_json", item_data.get("payload", {}))
    payload_json_str = json.dumps(payload, ensure_ascii=False)
    revision = int(item_data.get("revision", 1))

    now = updated_at or datetime.now(timezone.utc).replace(tzinfo=None)
    if isinstance(now, datetime) and now.tzinfo is not None:
        now = now.astimezone(timezone.utc).replace(tzinfo=None)

    raw_created = item_data.get("created_at") or now
    if isinstance(raw_created, datetime):
        created_at = raw_created.astimezone(timezone.utc).replace(tzinfo=None) if raw_created.tzinfo else raw_created
    elif isinstance(raw_created, str):
        try:
            created_at = datetime.fromisoformat(raw_created).astimezone(timezone.utc).replace(tzinfo=None)
        except Exception:
            created_at = now
    else:
        created_at = now

    def _execute(connection) -> None:
        existing = connection.execute(
            text("SELECT revision FROM demo_library_item WHERE id = :id"),
            {"id": iid},
        ).one_or_none()

        payload_map = {
            "id": iid,
            "company_id": company_id,
            "category": category,
            "name": name,
            "status": status,
            "is_starred": is_starred,
            "can_insert": can_insert,
            "is_sensitive": is_sensitive,
            "payload_json": payload_json_str,
            "revision": revision,
            "created_at": created_at,
            "updated_at": now,
        }

        if existing is None:
            connection.execute(
                text(
                    "INSERT INTO demo_library_item (id, company_id, category, name, status, "
                    "is_starred, can_insert, is_sensitive, payload_json, revision, created_at, updated_at) "
                    "VALUES (:id, :company_id, :category, :name, :status, :is_starred, :can_insert, "
                    ":is_sensitive, CAST(:payload_json AS JSON), :revision, :created_at, :updated_at)"
                ),
                payload_map,
            )
        else:
            if expected_revision is not None:
                result = connection.execute(
                    text(
                        "UPDATE demo_library_item SET company_id = :company_id, category = :category, "
                        "name = :name, status = :status, is_starred = :is_starred, can_insert = :can_insert, "
                        "is_sensitive = :is_sensitive, payload_json = CAST(:payload_json AS JSON), "
                        "revision = :revision, updated_at = :updated_at "
                        "WHERE id = :id AND revision = :expected_revision"
                    ),
                    {**payload_map, "expected_revision": int(expected_revision)},
                )
                if result.rowcount != 1:
                    raise DomainError(409, "REVISION_CONFLICT", "资料已被其他会话更新，请刷新并核对最新版本。")
            else:
                connection.execute(
                    text(
                        "UPDATE demo_library_item SET company_id = :company_id, category = :category, "
                        "name = :name, status = :status, is_starred = :is_starred, can_insert = :can_insert, "
                        "is_sensitive = :is_sensitive, payload_json = CAST(:payload_json AS JSON), "
                        "revision = :revision, updated_at = :updated_at WHERE id = :id"
                    ),
                    payload_map,
                )

    engine = target.engine if hasattr(target, "engine") else target
    if hasattr(engine, "begin"):
        with engine.begin() as connection:
            _execute(connection)
    else:
        _execute(engine)


def read_library_item(target, item_id: str) -> dict | None:
    from sqlalchemy import text

    def _execute(connection) -> dict | None:
        row = connection.execute(
            text(
                "SELECT id, company_id, category, name, status, is_starred, can_insert, is_sensitive, "
                "payload_json, revision, created_at, updated_at FROM demo_library_item WHERE id = :id"
            ),
            {"id": item_id},
        ).one_or_none()
        if row is None:
            return None
        payload = _json_value(row.payload_json) if row.payload_json is not None else {}
        return {
            "id": row.id,
            "company_id": row.company_id,
            "category": row.category,
            "name": row.name,
            "status": row.status,
            "is_starred": bool(row.is_starred),
            "can_insert": bool(row.can_insert),
            "is_sensitive": bool(row.is_sensitive),
            "payload_json": payload,
            "payload": payload,
            "revision": int(row.revision),
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }

    engine = target.engine if hasattr(target, "engine") else target
    if hasattr(engine, "connect"):
        with engine.connect() as connection:
            return _execute(connection)
    return _execute(engine)


def list_library_items(
    target,
    company_id: str,
    category: str | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    from sqlalchemy import text

    def _execute(connection) -> tuple[list[dict], int]:
        params: dict = {"company_id": company_id}
        where_clauses = ["company_id = :company_id"]
        if category is not None:
            where_clauses.append("category = :category")
            params["category"] = category
        if status is not None:
            where_clauses.append("status = :status")
            params["status"] = status

        where_str = "WHERE " + " AND ".join(where_clauses)
        count_sql = f"SELECT COUNT(*) FROM demo_library_item {where_str}"
        total = connection.execute(text(count_sql), params).scalar() or 0

        data_params = {**params, "limit": limit, "offset": offset}
        data_sql = (
            f"SELECT id, company_id, category, name, status, is_starred, can_insert, is_sensitive, "
            f"payload_json, revision, created_at, updated_at FROM demo_library_item "
            f"{where_str} ORDER BY updated_at DESC LIMIT :limit OFFSET :offset"
        )
        rows = connection.execute(text(data_sql), data_params).all()
        items = []
        for row in rows:
            payload = _json_value(row.payload_json) if row.payload_json is not None else {}
            items.append({
                "id": row.id,
                "company_id": row.company_id,
                "category": row.category,
                "name": row.name,
                "status": row.status,
                "is_starred": bool(row.is_starred),
                "can_insert": bool(row.can_insert),
                "is_sensitive": bool(row.is_sensitive),
                "payload_json": payload,
                "payload": payload,
                "revision": int(row.revision),
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            })
        return items, total

    engine = target.engine if hasattr(target, "engine") else target
    if hasattr(engine, "connect"):
        with engine.connect() as connection:
            return _execute(connection)
    return _execute(engine)


def delete_library_item(target, item_id: str) -> bool:
    from sqlalchemy import text

    def _execute(connection) -> bool:
        connection.execute(text("DELETE FROM demo_library_revision WHERE item_id = :id"), {"id": item_id})
        res = connection.execute(text("DELETE FROM demo_library_item WHERE id = :id"), {"id": item_id})
        return res.rowcount > 0

    engine = target.engine if hasattr(target, "engine") else target
    if hasattr(engine, "begin"):
        with engine.begin() as connection:
            return _execute(connection)
    return _execute(engine)


def commit_library_revision(
    target,
    item_id: str,
    payload: dict,
    expected_revision: int,
    new_revision: int,
    changed_by: str,
    change_reason: str | None = None,
    updated_at: datetime | None = None,
) -> dict:
    from sqlalchemy import text
    from uuid import uuid4

    now = updated_at or datetime.now(timezone.utc).replace(tzinfo=None)
    if isinstance(now, datetime) and now.tzinfo is not None:
        now = now.astimezone(timezone.utc).replace(tzinfo=None)

    payload_json_str = json.dumps(payload, ensure_ascii=False)

    def _execute(connection) -> dict:
        result = connection.execute(
            text(
                "UPDATE demo_library_item SET payload_json = CAST(:payload_json AS JSON), "
                "revision = :new_revision, updated_at = :updated_at "
                "WHERE id = :id AND revision = :expected_revision"
            ),
            {
                "id": item_id,
                "payload_json": payload_json_str,
                "new_revision": int(new_revision),
                "expected_revision": int(expected_revision),
                "updated_at": now,
            },
        )
        if result.rowcount != 1:
            raise DomainError(409, "REVISION_CONFLICT", "资料已被其他会话更新，请刷新并核对最新版本。")

        rev_id = f"rev-{uuid4().hex}"
        connection.execute(
            text(
                "INSERT INTO demo_library_revision (id, item_id, version_number, payload_json, changed_by, change_reason, created_at) "
                "VALUES (:id, :item_id, :version_number, CAST(:payload_json AS JSON), :changed_by, :change_reason, :created_at)"
            ),
            {
                "id": rev_id,
                "item_id": item_id,
                "version_number": int(new_revision),
                "payload_json": payload_json_str,
                "changed_by": changed_by,
                "change_reason": change_reason,
                "created_at": now,
            },
        )
        return {
            "id": rev_id,
            "item_id": item_id,
            "version_number": int(new_revision),
            "revision": int(new_revision),
            "payload_json": deepcopy(payload),
            "payload": deepcopy(payload),
            "changed_by": changed_by,
            "change_reason": change_reason,
            "created_at": now,
        }

    engine = target.engine if hasattr(target, "engine") else target
    if hasattr(engine, "begin"):
        with engine.begin() as connection:
            return _execute(connection)
    return _execute(engine)


def list_library_revisions(target, item_id: str) -> list[dict]:
    from sqlalchemy import text

    def _execute(connection) -> list[dict]:
        rows = connection.execute(
            text(
                "SELECT id, item_id, version_number, payload_json, changed_by, change_reason, created_at "
                "FROM demo_library_revision WHERE item_id = :item_id ORDER BY version_number ASC"
            ),
            {"item_id": item_id},
        ).all()
        result = []
        for row in rows:
            payload = _json_value(row.payload_json) if row.payload_json is not None else {}
            result.append({
                "id": row.id,
                "item_id": row.item_id,
                "version_number": int(row.version_number),
                "revision": int(row.version_number),
                "payload_json": payload,
                "payload": payload,
                "changed_by": row.changed_by,
                "change_reason": row.change_reason,
                "created_at": row.created_at,
            })
        return result

    engine = target.engine if hasattr(target, "engine") else target
    if hasattr(engine, "connect"):
        with engine.connect() as connection:
            return _execute(connection)
    return _execute(engine)


def save_sla_template(target, template_data: dict, expected_revision: int | None = None, updated_at: datetime | None = None) -> None:
    from sqlalchemy import text

    tid = template_data["id"]
    company_id = template_data["company_id"]
    level = template_data.get("level", "standard")
    name = template_data.get("name", "")
    rules = template_data.get("rules_json", template_data.get("rules", template_data.get("variables", {})))
    rules_json_str = json.dumps(rules, ensure_ascii=False)
    revision = int(template_data.get("revision", 1))

    now = updated_at or datetime.now(timezone.utc).replace(tzinfo=None)
    if isinstance(now, datetime) and now.tzinfo is not None:
        now = now.astimezone(timezone.utc).replace(tzinfo=None)

    raw_created = template_data.get("created_at") or now
    if isinstance(raw_created, datetime):
        created_at = raw_created.astimezone(timezone.utc).replace(tzinfo=None) if raw_created.tzinfo else raw_created
    elif isinstance(raw_created, str):
        try:
            created_at = datetime.fromisoformat(raw_created).astimezone(timezone.utc).replace(tzinfo=None)
        except Exception:
            created_at = now
    else:
        created_at = now

    def _execute(connection) -> None:
        existing = connection.execute(
            text("SELECT revision FROM demo_sla_template WHERE id = :id"),
            {"id": tid},
        ).one_or_none()

        payload_map = {
            "id": tid,
            "company_id": company_id,
            "level": level,
            "name": name,
            "rules_json": rules_json_str,
            "revision": revision,
            "created_at": created_at,
            "updated_at": now,
        }

        if existing is None:
            connection.execute(
                text(
                    "INSERT INTO demo_sla_template (id, company_id, level, name, rules_json, revision, created_at, updated_at) "
                    "VALUES (:id, :company_id, :level, :name, CAST(:rules_json AS JSON), :revision, :created_at, :updated_at)"
                ),
                payload_map,
            )
        else:
            if expected_revision is not None:
                result = connection.execute(
                    text(
                        "UPDATE demo_sla_template SET company_id = :company_id, level = :level, "
                        "name = :name, rules_json = CAST(:rules_json AS JSON), revision = :revision, "
                        "updated_at = :updated_at WHERE id = :id AND revision = :expected_revision"
                    ),
                    {**payload_map, "expected_revision": int(expected_revision)},
                )
                if result.rowcount != 1:
                    raise DomainError(409, "REVISION_CONFLICT", "SLA 模板已被其他会话更新，请刷新并核对最新版本。")
            else:
                connection.execute(
                    text(
                        "UPDATE demo_sla_template SET company_id = :company_id, level = :level, "
                        "name = :name, rules_json = CAST(:rules_json AS JSON), revision = :revision, "
                        "updated_at = :updated_at WHERE id = :id"
                    ),
                    payload_map,
                )

    engine = target.engine if hasattr(target, "engine") else target
    if hasattr(engine, "begin"):
        with engine.begin() as connection:
            _execute(connection)
    else:
        _execute(engine)


def read_sla_template(target, template_id: str) -> dict | None:
    from sqlalchemy import text

    def _execute(connection) -> dict | None:
        row = connection.execute(
            text(
                "SELECT id, company_id, level, name, rules_json, revision, created_at, updated_at "
                "FROM demo_sla_template WHERE id = :id"
            ),
            {"id": template_id},
        ).one_or_none()
        if row is None:
            return None
        rules = _json_value(row.rules_json) if row.rules_json is not None else {}
        return {
            "id": row.id,
            "company_id": row.company_id,
            "level": row.level,
            "name": row.name,
            "rules_json": rules,
            "rules": rules,
            "revision": int(row.revision),
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }

    engine = target.engine if hasattr(target, "engine") else target
    if hasattr(engine, "connect"):
        with engine.connect() as connection:
            return _execute(connection)
    return _execute(engine)


def list_sla_templates(target, company_id: str, level: str | None = None) -> list[dict]:
    from sqlalchemy import text

    def _execute(connection) -> list[dict]:
        params: dict = {"company_id": company_id}
        where_clauses = ["company_id = :company_id"]
        if level is not None:
            where_clauses.append("level = :level")
            params["level"] = level

        sql = (
            f"SELECT id, company_id, level, name, rules_json, revision, created_at, updated_at "
            f"FROM demo_sla_template WHERE {' AND '.join(where_clauses)} ORDER BY updated_at DESC"
        )
        rows = connection.execute(text(sql), params).all()
        result = []
        for row in rows:
            rules = _json_value(row.rules_json) if row.rules_json is not None else {}
            result.append({
                "id": row.id,
                "company_id": row.company_id,
                "level": row.level,
                "name": row.name,
                "rules_json": rules,
                "rules": rules,
                "revision": int(row.revision),
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            })
        return result

    engine = target.engine if hasattr(target, "engine") else target
    if hasattr(engine, "connect"):
        with engine.connect() as connection:
            return _execute(connection)
    return _execute(engine)


def delete_sla_template(target, template_id: str) -> bool:
    from sqlalchemy import text

    def _execute(connection) -> bool:
        res = connection.execute(text("DELETE FROM demo_sla_template WHERE id = :id"), {"id": template_id})
        return res.rowcount > 0

    engine = target.engine if hasattr(target, "engine") else target
    if hasattr(engine, "begin"):
        with engine.begin() as connection:
            return _execute(connection)
    return _execute(engine)


def save_workflow(target, workflow_data: dict, expected_revision: int | None = None, updated_at: datetime | None = None) -> None:
    from sqlalchemy import text

    pid = workflow_data["project_id"]
    current_stage = workflow_data.get("current_stage", "parsing")
    stages = workflow_data.get("stages_json", workflow_data.get("stages", {}))
    stages_json_str = json.dumps(stages, ensure_ascii=False)
    incremental = workflow_data.get("incremental_checks_json", workflow_data.get("incremental_checks", []))
    incremental_json_str = json.dumps(incremental, ensure_ascii=False)

    if expected_revision is not None:
        revision = int(workflow_data.get("revision", int(expected_revision) + 1))
        if revision == int(expected_revision):
            revision = int(expected_revision) + 1
    else:
        revision = int(workflow_data.get("revision", 1))

    now = updated_at or datetime.now(timezone.utc).replace(tzinfo=None)
    if isinstance(now, datetime) and now.tzinfo is not None:
        now = now.astimezone(timezone.utc).replace(tzinfo=None)

    def _execute(connection) -> None:
        existing = connection.execute(
            text("SELECT revision FROM demo_workflow WHERE project_id = :project_id"),
            {"project_id": pid},
        ).one_or_none()

        payload_map = {
            "project_id": pid,
            "current_stage": current_stage,
            "stages_json": stages_json_str,
            "incremental_checks_json": incremental_json_str,
            "revision": revision,
            "updated_at": now,
        }

        if existing is None:
            connection.execute(
                text(
                    "INSERT INTO demo_workflow (project_id, current_stage, stages_json, incremental_checks_json, revision, updated_at) "
                    "VALUES (:project_id, :current_stage, CAST(:stages_json AS JSON), CAST(:incremental_checks_json AS JSON), :revision, :updated_at)"
                ),
                payload_map,
            )
        else:
            if expected_revision is not None:
                result = connection.execute(
                    text(
                        "UPDATE demo_workflow SET current_stage = :current_stage, "
                        "stages_json = CAST(:stages_json AS JSON), incremental_checks_json = CAST(:incremental_checks_json AS JSON), "
                        "revision = :revision, updated_at = :updated_at "
                        "WHERE project_id = :project_id AND revision = :expected_revision"
                    ),
                    {**payload_map, "expected_revision": int(expected_revision)},
                )
                if result.rowcount != 1:
                    raise DomainError(409, "REVISION_CONFLICT", "工作流已被其他会话更新，请刷新并核对最新版本。")
            else:
                connection.execute(
                    text(
                        "UPDATE demo_workflow SET current_stage = :current_stage, "
                        "stages_json = CAST(:stages_json AS JSON), incremental_checks_json = CAST(:incremental_checks_json AS JSON), "
                        "revision = :revision, updated_at = :updated_at WHERE project_id = :project_id"
                    ),
                    payload_map,
                )

    engine = target.engine if hasattr(target, "engine") else target
    if hasattr(engine, "begin"):
        with engine.begin() as connection:
            _execute(connection)
    else:
        _execute(engine)


def read_workflow(target, project_id: str) -> dict | None:
    from sqlalchemy import text

    def _execute(connection) -> dict | None:
        row = connection.execute(
            text(
                "SELECT project_id, current_stage, stages_json, incremental_checks_json, revision, updated_at "
                "FROM demo_workflow WHERE project_id = :project_id"
            ),
            {"project_id": project_id},
        ).one_or_none()
        if row is None:
            return None
        stages = _json_value(row.stages_json) if row.stages_json is not None else {}
        incremental = _json_value(row.incremental_checks_json) if row.incremental_checks_json is not None else []
        return {
            "project_id": row.project_id,
            "current_stage": row.current_stage,
            "stages_json": stages,
            "stages": stages,
            "incremental_checks_json": incremental,
            "incremental_checks": incremental,
            "revision": int(row.revision),
            "updated_at": row.updated_at,
        }

    engine = target.engine if hasattr(target, "engine") else target
    if hasattr(engine, "connect"):
        with engine.connect() as connection:
            return _execute(connection)
    return _execute(engine)


def delete_workflow(target, project_id: str) -> bool:
    from sqlalchemy import text

    def _execute(connection) -> bool:
        res = connection.execute(text("DELETE FROM demo_workflow WHERE project_id = :project_id"), {"project_id": project_id})
        return res.rowcount > 0

    engine = target.engine if hasattr(target, "engine") else target
    if hasattr(engine, "begin"):
        with engine.begin() as connection:
            return _execute(connection)
    return _execute(engine)


def save_job(target, job_data: dict, updated_at: datetime | None = None) -> None:
    from sqlalchemy import text

    jid = job_data["id"]
    job_type = job_data.get("job_type", job_data.get("type", "parse_tender"))
    project_id = job_data["project_id"]
    status = job_data.get("status", "pending")
    progress = int(job_data.get("progress", 0))
    step_name = job_data.get("step_name")

    error = job_data.get("error_json", job_data.get("error"))
    error_json_str = json.dumps(error, ensure_ascii=False) if error is not None else None

    result = job_data.get("result_json", job_data.get("result"))
    result_json_str = json.dumps(result, ensure_ascii=False) if result is not None else None

    created_by = job_data.get("created_by", "system")

    now = updated_at or datetime.now(timezone.utc).replace(tzinfo=None)
    if isinstance(now, datetime) and now.tzinfo is not None:
        now = now.astimezone(timezone.utc).replace(tzinfo=None)

    raw_created = job_data.get("created_at") or now
    if isinstance(raw_created, datetime):
        created_at = raw_created.astimezone(timezone.utc).replace(tzinfo=None) if raw_created.tzinfo else raw_created
    elif isinstance(raw_created, str):
        try:
            created_at = datetime.fromisoformat(raw_created).astimezone(timezone.utc).replace(tzinfo=None)
        except Exception:
            created_at = now
    else:
        created_at = now

    def _execute(connection) -> None:
        connection.execute(
            text(
                "INSERT INTO demo_job (id, job_type, project_id, status, progress, step_name, "
                "error_json, result_json, created_by, created_at, updated_at) "
                "VALUES (:id, :job_type, :project_id, :status, :progress, :step_name, "
                "CAST(:error_json AS JSON), CAST(:result_json AS JSON), :created_by, :created_at, :updated_at) "
                "ON DUPLICATE KEY UPDATE "
                "job_type = VALUES(job_type), "
                "project_id = VALUES(project_id), "
                "status = VALUES(status), "
                "progress = VALUES(progress), "
                "step_name = VALUES(step_name), "
                "error_json = VALUES(error_json), "
                "result_json = VALUES(result_json), "
                "updated_at = VALUES(updated_at)"
            ),
            {
                "id": jid,
                "job_type": job_type,
                "project_id": project_id,
                "status": status,
                "progress": progress,
                "step_name": step_name,
                "error_json": error_json_str,
                "result_json": result_json_str,
                "created_by": created_by,
                "created_at": created_at,
                "updated_at": now,
            },
        )

    engine = target.engine if hasattr(target, "engine") else target
    if hasattr(engine, "begin"):
        with engine.begin() as connection:
            _execute(connection)
    else:
        _execute(engine)


def read_job(target, job_id: str) -> dict | None:
    from sqlalchemy import text

    def _execute(connection) -> dict | None:
        row = connection.execute(
            text(
                "SELECT id, job_type, project_id, status, progress, step_name, "
                "error_json, result_json, created_by, created_at, updated_at "
                "FROM demo_job WHERE id = :id"
            ),
            {"id": job_id},
        ).one_or_none()
        if row is None:
            return None
        error = _json_value(row.error_json) if row.error_json is not None else None
        result = _json_value(row.result_json) if row.result_json is not None else None
        return {
            "id": row.id,
            "job_type": row.job_type,
            "type": row.job_type,
            "project_id": row.project_id,
            "status": row.status,
            "progress": int(row.progress),
            "step_name": row.step_name,
            "error_json": error,
            "error": error,
            "result_json": result,
            "result": result,
            "created_by": row.created_by,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }

    engine = target.engine if hasattr(target, "engine") else target
    if hasattr(engine, "connect"):
        with engine.connect() as connection:
            return _execute(connection)
    return _execute(engine)


def update_job_progress(
    target,
    job_id: str,
    progress: int,
    status: str | None = None,
    step_name: str | None = None,
    error_json: dict | list | str | None = None,
    result_json: dict | list | None = None,
    updated_at: datetime | None = None,
) -> bool:
    from sqlalchemy import text

    now = updated_at or datetime.now(timezone.utc).replace(tzinfo=None)
    if isinstance(now, datetime) and now.tzinfo is not None:
        now = now.astimezone(timezone.utc).replace(tzinfo=None)

    set_clauses = ["progress = :progress", "updated_at = :updated_at"]
    params: dict = {"id": job_id, "progress": int(progress), "updated_at": now}

    if status is not None:
        set_clauses.append("status = :status")
        params["status"] = status

    if step_name is not None:
        set_clauses.append("step_name = :step_name")
        params["step_name"] = step_name

    if error_json is not None:
        set_clauses.append("error_json = CAST(:error_json AS JSON)")
        params["error_json"] = json.dumps(error_json, ensure_ascii=False)

    if result_json is not None:
        set_clauses.append("result_json = CAST(:result_json AS JSON)")
        params["result_json"] = json.dumps(result_json, ensure_ascii=False)

    sql = f"UPDATE demo_job SET {', '.join(set_clauses)} WHERE id = :id"

    def _execute(connection) -> bool:
        res = connection.execute(text(sql), params)
        return res.rowcount > 0

    engine = target.engine if hasattr(target, "engine") else target
    if hasattr(engine, "begin"):
        with engine.begin() as connection:
            return _execute(connection)
    return _execute(engine)


def list_jobs_by_project(
    target,
    project_id: str,
    job_type: str | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    from sqlalchemy import text

    def _execute(connection) -> tuple[list[dict], int]:
        params: dict = {"project_id": project_id}
        where_clauses = ["project_id = :project_id"]
        if job_type is not None:
            where_clauses.append("job_type = :job_type")
            params["job_type"] = job_type
        if status is not None:
            where_clauses.append("status = :status")
            params["status"] = status

        where_str = "WHERE " + " AND ".join(where_clauses)
        count_sql = f"SELECT COUNT(*) FROM demo_job {where_str}"
        total = connection.execute(text(count_sql), params).scalar() or 0

        data_params = {**params, "limit": limit, "offset": offset}
        data_sql = (
            f"SELECT id, job_type, project_id, status, progress, step_name, "
            f"error_json, result_json, created_by, created_at, updated_at "
            f"FROM demo_job {where_str} ORDER BY updated_at DESC LIMIT :limit OFFSET :offset"
        )
        rows = connection.execute(text(data_sql), data_params).all()
        jobs = []
        for row in rows:
            error = _json_value(row.error_json) if row.error_json is not None else None
            result = _json_value(row.result_json) if row.result_json is not None else None
            jobs.append({
                "id": row.id,
                "job_type": row.job_type,
                "type": row.job_type,
                "project_id": row.project_id,
                "status": row.status,
                "progress": int(row.progress),
                "step_name": row.step_name,
                "error_json": error,
                "error": error,
                "result_json": result,
                "result": result,
                "created_by": row.created_by,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            })
        return jobs, total

    engine = target.engine if hasattr(target, "engine") else target
    if hasattr(engine, "connect"):
        with engine.connect() as connection:
            return _execute(connection)
    return _execute(engine)


def delete_job(target, job_id: str) -> bool:
    from sqlalchemy import text

    def _execute(connection) -> bool:
        res = connection.execute(text("DELETE FROM demo_job WHERE id = :id"), {"id": job_id})
        return res.rowcount > 0

    engine = target.engine if hasattr(target, "engine") else target
    if hasattr(engine, "begin"):
        with engine.begin() as connection:
            return _execute(connection)
    return _execute(engine)


def decompose_paragraphs(
    content: str,
    chapter_id: str,
    citations: list[dict] | None = None,
    created_at: str | None = None,
    updated_at: str | None = None,
) -> list[dict]:
    """将章节正文切分为带编号段落，并精准关联引用与时间戳。"""
    if not content:
        return []
    normalized = content.replace("\r\n", "\n").replace("\r", "\n")
    raw_blocks = [p for p in normalized.split("\n") if p.strip()]
    cites = citations or []

    from datetime import datetime, timezone
    now_iso = datetime.now(timezone.utc).isoformat()
    c_at = created_at or now_iso
    u_at = updated_at or now_iso

    paragraphs = []
    for idx, p_text in enumerate(raw_blocks, start=1):
        p_cites = []
        for c in cites:
            cid = str(c.get("id", ""))
            cname = str(c.get("name", ""))
            ctag = f"[证:{cid}]"
            ctext = str(c.get("cite_text", ""))
            if (ctag in p_text or (cid and cid in p_text) or
                (cname and cname in p_text) or (ctext and ctext in p_text)):
                p_cites.append(c)
        if not p_cites and len(raw_blocks) == 1 and cites:
            p_cites = list(cites)
        paragraphs.append({
            "id": f"{chapter_id}-p{idx}",
            "order": idx,
            "text": p_text,
            "citations": p_cites,
            "created_at": c_at,
            "updated_at": u_at,
        })
    return paragraphs



