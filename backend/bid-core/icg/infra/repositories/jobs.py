# 为什么有这个文件：工作流状态与异步任务的 MySQL 持久化。
# 它解决什么问题：集中管理 demo_workflow 与 demo_job 表的数据读写、进度更新、状态流转与并发控制。

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text

from icg.domain.domain import DomainError
from icg.infra.repositories.common import json_value


def save_workflow(
    target: Any,
    workflow_data: dict,
    expected_revision: int | None = None,
    updated_at: datetime | None = None,
) -> None:
    """保存或更新项目工作流状态，支持乐观并发锁。"""
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


def read_workflow(target: Any, project_id: str) -> dict | None:
    """按项目 ID 获取当前工作流阶段与增量检查。"""
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
        stages = json_value(row.stages_json) if row.stages_json is not None else {}
        incremental = json_value(row.incremental_checks_json) if row.incremental_checks_json is not None else []
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


def delete_workflow(target: Any, project_id: str) -> bool:
    """物理删除项目工作流记录。"""
    def _execute(connection) -> bool:
        res = connection.execute(text("DELETE FROM demo_workflow WHERE project_id = :project_id"), {"project_id": project_id})
        return res.rowcount > 0

    engine = target.engine if hasattr(target, "engine") else target
    if hasattr(engine, "begin"):
        with engine.begin() as connection:
            return _execute(connection)
    return _execute(engine)


def save_job(target: Any, job_data: dict, updated_at: datetime | None = None) -> None:
    """保存或更新异步任务状态与执行结果。"""
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


def read_job(target: Any, job_id: str) -> dict | None:
    """按 ID 获取单个异步任务详情。"""
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
        error = json_value(row.error_json) if row.error_json is not None else None
        result = json_value(row.result_json) if row.result_json is not None else None
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
    target: Any,
    job_id: str,
    progress: int,
    status: str | None = None,
    step_name: str | None = None,
    error_json: dict | list | str | None = None,
    result_json: dict | list | None = None,
    updated_at: datetime | None = None,
) -> bool:
    """原子更新异步任务进度、当前阶段名与结果/错误。"""
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
    target: Any,
    project_id: str,
    job_type: str | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """按项目、类型与状态分页拉取任务列表。"""
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
            error = json_value(row.error_json) if row.error_json is not None else None
            result = json_value(row.result_json) if row.result_json is not None else None
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


def delete_job(target: Any, job_id: str) -> bool:
    """删除指定的异步任务。"""
    def _execute(connection) -> bool:
        res = connection.execute(text("DELETE FROM demo_job WHERE id = :id"), {"id": job_id})
        return res.rowcount > 0

    engine = target.engine if hasattr(target, "engine") else target
    if hasattr(engine, "begin"):
        with engine.begin() as connection:
            return _execute(connection)
    return _execute(engine)
