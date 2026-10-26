# 为什么有这个文件：资料库条目与修订版本历史的 MySQL 持久化。
# 它解决什么问题：集中管理 demo_library_item 与 demo_library_revision 表的增删改查与乐观并发控制。

from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import text

from icg.domain.domain import DomainError
from icg.infra.repositories.common import json_value


def save_library_item(
    target: Any,
    item_data: dict,
    expected_revision: int | None = None,
    updated_at: datetime | None = None,
) -> None:
    """保存或更新资料库条目。"""
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


def read_library_item(target: Any, item_id: str) -> dict | None:
    """按 ID 读取单个资料条目详情。"""
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
        payload = json_value(row.payload_json) if row.payload_json is not None else {}
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
    target: Any,
    company_id: str,
    category: str | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """按公司、分类及状态分页筛选资料条目。"""
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
            payload = json_value(row.payload_json) if row.payload_json is not None else {}
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


def delete_library_item(target: Any, item_id: str) -> bool:
    """物理删除资料条目及其全量修订版本。"""
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
    target: Any,
    item_id: str,
    payload: dict,
    expected_revision: int,
    new_revision: int,
    changed_by: str,
    change_reason: str | None = None,
    updated_at: datetime | None = None,
) -> dict:
    """提交资料条目新修订版本快照并更新主条目。"""
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


def list_library_revisions(target: Any, item_id: str) -> list[dict]:
    """查询指定资料条目的全部历史修订记录。"""
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
            payload = json_value(row.payload_json) if row.payload_json is not None else {}
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
