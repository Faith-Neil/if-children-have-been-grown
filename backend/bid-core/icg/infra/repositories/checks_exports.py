# 为什么有这个文件：检查结果与导出记录快照的 MySQL 持久化。
# 它解决什么问题：集中管理 demo_check 与 demo_export 表的数据读写、JSON 结构体反序列化与状态流转。

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text

from icg.infra.repositories.common import json_value, _json_value


def save_check(target: Any, check_data: dict, updated_at: datetime | None = None) -> None:
    """持久化检查结果与阻断项计数。"""
    cid = check_data["id"]
    pid = check_data["project_id"]
    volume_id = check_data.get("volume_id")
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


def read_check(target: Any, check_id: str) -> dict | None:
    """按 ID 读取单次检查详情。"""
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
        issues = json_value(row.issues_json) if row.issues_json is not None else []
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


def list_checks_by_project(target: Any, project_id: str, volume_id: str | None = None, limit: int = 50, offset: int = 0) -> list[dict]:
    """按项目与分册分页拉取历史检查记录。"""
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
            issues = json_value(row.issues_json) if row.issues_json is not None else []
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


def delete_check(target: Any, check_id: str) -> bool:
    """删除检查记录。"""
    def _execute_delete(connection) -> bool:
        result = connection.execute(text("DELETE FROM demo_check WHERE id = :id"), {"id": check_id})
        return result.rowcount > 0

    engine = target.engine if hasattr(target, "engine") else target
    if hasattr(engine, "begin"):
        with engine.begin() as connection:
            return _execute_delete(connection)
    return _execute_delete(engine)


def save_export(target: Any, export_data: dict, updated_at: datetime | None = None) -> None:
    """保存导出记录与结构化正文快照。"""
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


def read_export(target: Any, export_id: str) -> dict | None:
    """按 ID 读取单次导出记录与完整快照。"""
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
        snapshot = json_value(row.snapshot_json) if row.snapshot_json is not None else None
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


def update_export_status(target: Any, export_id: str, status: str, file_path: str | None = None, file_size: int | None = None) -> bool:
    """更新导出记录的状态、文件路径与文件体积。"""
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


def list_exports_by_project(target: Any, project_id: str, export_type: str | None = None, limit: int = 50, offset: int = 0) -> tuple[list[dict], int]:
    """按项目与导出类型分页拉取历史导出记录列表。"""
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
            snapshot = json_value(row.snapshot_json) if row.snapshot_json is not None else None
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


def delete_export(target: Any, export_id: str) -> bool:
    """删除导出记录。"""
    def _execute_delete(connection) -> bool:
        result = connection.execute(text("DELETE FROM demo_export WHERE id = :id"), {"id": export_id})
        return result.rowcount > 0

    engine = target.engine if hasattr(target, "engine") else target
    if hasattr(engine, "begin"):
        with engine.begin() as connection:
            return _execute_delete(connection)
    return _execute_delete(engine)
