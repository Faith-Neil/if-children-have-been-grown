# 为什么有这个文件：MySQL 连接与全量聚合持久化仓储（MysqlConnectionRepository）。
# 它解决什么问题：集中管理 MySQL 事务、连接池惰性初始化、会话/租约/回执同步，并代理至各领域实体的子仓储。

from __future__ import annotations

import json
from datetime import datetime
from threading import Lock
from typing import Any, Callable, TypeVar

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from icg.domain.domain import Chapter, DemoState, DomainError, Lease, Project, iso_time
from icg.infra.mysql_gate import create_mysql_engine, RECEIPT_TTL
from icg.infra.memory_repository import MemoryRepository
from icg.infra.repositories.common import as_timestamp, parse_db_timestamp, utc_naive, json_value
from icg.infra.repositories.chapters import read_chapter, save_chapter, commit_chapter_version, chapter_snapshot, save_chapters_diff
from icg.infra.repositories.checks_exports import (
    save_check, read_check, list_checks_by_project, delete_check, check_snapshot, save_checks_diff,
    save_export, read_export, update_export_status, list_exports_by_project, delete_export,
)
from icg.infra.repositories.library import (
    save_library_item, read_library_item, list_library_items, delete_library_item,
    commit_library_revision, list_library_revisions,
)
from icg.infra.repositories.sla import (
    save_sla_template, read_sla_template, list_sla_templates, delete_sla_template,
)
from icg.infra.repositories.jobs import (
    save_workflow, read_workflow, delete_workflow,
    save_job, read_job, update_job_progress, list_jobs_by_project, delete_job,
)
from icg.infra.repositories.projects import project_snapshot, team_snapshot, save_projects
from icg.infra.repositories.model_config import save_model_configs

T = TypeVar("T")


def lease_snapshot(state: DemoState) -> dict:
    """提取状态中所有租约快照。"""
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


def same_receipt(previous: dict, receipt: dict) -> bool:
    """比对两个幂等回执是否完全一致。"""
    return (previous.get("fingerprint") == receipt.get("fingerprint")
            and previous.get("result") == receipt.get("result"))


_lease_snapshot = lease_snapshot
_same_receipt = same_receipt


class MysqlConnectionRepository:
    """MySQL 持久化仓储。"""
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
        loaded_chapter_ids: set[str] = set()
        loaded_check_ids: set[str] = set()

        def wrapped(state: DemoState) -> T:
            self._load_shared(state, loaded_project_ids, loaded_chapter_ids, loaded_check_ids)
            state.cap_receipts = False
            before_sessions = dict(state.sessions)
            before_receipts = {key: dict(receipt) for key, receipt in state.workflow_receipts.items()}
            before_leases = lease_snapshot(state)
            before_projects = project_snapshot(state)
            before_teams = team_snapshot(state)
            before_configs = dict(state.model_configs)
            before_bindings = dict(state.project_model_configs)
            before_chapters = chapter_snapshot(state)
            before_checks = check_snapshot(state)
            result = operation(state)
            self._save_shared(
                before_sessions, dict(state.sessions), before_receipts, state.workflow_receipts,
                before_leases, lease_snapshot(state),
                before_projects, project_snapshot(state), before_teams, team_snapshot(state),
                loaded_project_ids,
                before_configs, dict(state.model_configs),
                before_bindings, dict(state.project_model_configs),
                before_chapters, chapter_snapshot(state), state.chapters, loaded_chapter_ids,
                before_checks, check_snapshot(state), state.checks, loaded_check_ids,
            )
            state.sessions.clear()
            state.workflow_receipts.clear()
            for chapter in state.chapters.values():
                chapter.lock = None
            state.cap_receipts = True
            return result

        return self._memory.transaction(wrapped)

    def _load_shared(self, state: DemoState, loaded_project_ids: set[str],
                     loaded_chapter_ids: set[str] | None = None,
                     loaded_check_ids: set[str] | None = None) -> None:
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
                        expires_at=as_timestamp(row[4]),
                        acquired_at=as_timestamp(row[5]) if row[5] else None,
                        heartbeat_at=as_timestamp(row[6]) if row[6] else None,
                        lock_reason=row[7],
                        taken_over_from_user_id=row[8],
                        takeover_reason=row[9],
                        released_at=as_timestamp(row[10]) if row[10] else None,
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
                    chapter_id: Lease(token, owner_id, session_token, as_timestamp(expires_at))
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
                "result": json_value(result_json),
                "created_at": as_timestamp(created_at),
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
                    deadline_at=parse_db_timestamp(deadline_at),
                    security_level=security_level or "internal",
                    industry=industry or "it",
                    is_archived=bool(is_archived),
                    created_by=created_by or "",
                    created_at=parse_db_timestamp(created_at),
                    updated_by=updated_by or "",
                    updated_at=parse_db_timestamp(updated_at),
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
            state.project_teams[project_id] = json_value(team_json)
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
            from icg.infra.model_config_storage import ModelConfig
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
                    "created_at": iso_time(as_timestamp(v_created)) if isinstance(v_created, datetime) else str(v_created),
                })
            if loaded_chapter_ids is not None:
                loaded_chapter_ids.clear()
                loaded_chapter_ids.update(r[0] for r in chapters_rows)
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
            # 加载历史 checks 记录
            try:
                with self.engine.begin() as connection:
                    check_rows = connection.execute(text(
                        "SELECT id, project_id, volume_id, status, blocking_count, warning_count, issues_json FROM demo_check"
                    )).all()
                if loaded_check_ids is not None:
                    loaded_check_ids.clear()
                    loaded_check_ids.update(r[0] for r in check_rows)
                from icg.domain.domain import Check
                for chk_id, p_id, v_id, status_val, blk_cnt, wrn_cnt, issues_raw in check_rows:
                    if chk_id not in state.checks:
                        issues_list = json_value(issues_raw) if issues_raw else []
                        state.checks[chk_id] = Check(
                            id=chk_id,
                            chapter_id=p_id or "",
                            passed=(status_val == "passed"),
                            revision=1,
                            content_hash="",
                            issues=issues_list if isinstance(issues_list, list) else [],
                        )
            except Exception:
                pass
        except Exception:
            pass

    def _save_shared(self, before_sessions: dict, after_sessions: dict,
                     before_receipts: dict, after_receipts: dict,
                     before_leases: dict, after_leases: dict,
                     before_projects: dict, after_projects: dict,
                     before_teams: dict, after_teams: dict,
                     loaded_project_ids: set[str],
                     before_configs: dict | None = None, after_configs: dict | None = None,
                     before_bindings: dict | None = None, after_bindings: dict | None = None,
                     before_chapters: dict | None = None, after_chapters: dict | None = None,
                     state_chapters: dict | None = None, loaded_chapter_ids: set[str] | None = None,
                     before_checks: dict | None = None, after_checks: dict | None = None,
                     state_checks: dict | None = None, loaded_check_ids: set[str] | None = None) -> None:
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
                         "created_at": utc_naive(previous["created_at"]), "fingerprint": previous["fingerprint"]},
                    )
            for key, receipt in after_receipts.items():
                previous = before_receipts.get(key)
                if previous is not None and same_receipt(previous, receipt):
                    continue
                scope_id, user_id, idempotency_key = key
                created_at = utc_naive(receipt["created_at"])
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
                condition = ("chapter_id = :chapter_id AND token = :previous_token "
                             "AND owner_id = :previous_owner_id AND session_token = :previous_session_token "
                             "AND expires_at = :previous_expires_at")
                comparison = {} if previous is None else {
                    "chapter_id": chapter_id,
                    "previous_token": previous[0],
                    "previous_owner_id": previous[1],
                    "previous_session_token": previous[2],
                    "previous_expires_at": utc_naive(previous[3]),
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
                    "expires_at": utc_naive(expires_at),
                    "acquired_at": utc_naive(current[4]) if len(current) > 4 and current[4] else None,
                    "heartbeat_at": utc_naive(current[5]) if len(current) > 5 and current[5] else None,
                    "lock_reason": current[6] if len(current) > 6 else None,
                    "taken_over_from_user_id": current[7] if len(current) > 7 else None,
                    "takeover_reason": current[8] if len(current) > 8 else None,
                    "released_at": utc_naive(current[9]) if len(current) > 9 and current[9] else None,
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
            save_projects(
                connection, before_projects, after_projects, before_teams, after_teams, loaded_project_ids,
            )
            if before_configs is not None and after_configs is not None:
                save_model_configs(
                    connection, before_configs, after_configs,
                    before_bindings or {}, after_bindings or {},
                )
            if before_chapters is not None and after_chapters is not None and state_chapters is not None:
                save_chapters_diff(
                    connection, before_chapters, after_chapters,
                    state_chapters, loaded_chapter_ids or set(),
                )
            if before_checks is not None and after_checks is not None and state_checks is not None:
                save_checks_diff(
                    connection, before_checks, after_checks,
                    state_checks, loaded_check_ids or set(),
                )
