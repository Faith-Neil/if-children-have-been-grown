# 为什么有这个文件：SLA 服务水平协议模板的 MySQL 持久化。
# 它解决什么问题：集中管理 demo_sla_template 表的增删改查与乐观并发控制。

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text

from icg_demo.domain import DomainError
from icg.infra.repositories.common import json_value


def save_sla_template(
    target: Any,
    template_data: dict,
    expected_revision: int | None = None,
    updated_at: datetime | None = None,
) -> None:
    """保存或更新 SLA 模板规则定义。"""
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


def read_sla_template(target: Any, template_id: str) -> dict | None:
    """按 ID 获取 SLA 模板详情与规则定义。"""
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
        rules = json_value(row.rules_json) if row.rules_json is not None else {}
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


def list_sla_templates(target: Any, company_id: str, level: str | None = None) -> list[dict]:
    """按公司和级别获取 SLA 模板列表。"""
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
            rules = json_value(row.rules_json) if row.rules_json is not None else {}
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


def delete_sla_template(target: Any, template_id: str) -> bool:
    """删除指定的 SLA 模板。"""
    def _execute(connection) -> bool:
        res = connection.execute(text("DELETE FROM demo_sla_template WHERE id = :id"), {"id": template_id})
        return res.rowcount > 0

    engine = target.engine if hasattr(target, "engine") else target
    if hasattr(engine, "begin"):
        with engine.begin() as connection:
            return _execute(connection)
    return _execute(engine)
