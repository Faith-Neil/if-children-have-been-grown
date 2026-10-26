# 为什么有这个文件：项目与项目团队成员的 MySQL 持久化与快照比较。
# 它解决什么问题：集中管理 demo_project 与 demo_project_team 表的批量同步、乐观锁更新与脏检查。

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text

from icg.domain.domain import DemoState, DomainError
from icg.infra.repositories.common import to_utc_naive, _to_utc_naive


def project_snapshot(state: DemoState) -> dict:
    """提取状态中所有项目的快照元组，用于前后状态脏检查。"""
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


def team_snapshot(state: DemoState) -> dict:
    """提取状态中所有团队配置的序列化快照。"""
    return {
        project_id: json.dumps(team, ensure_ascii=False, sort_keys=True)
        for project_id, team in state.project_teams.items()
    }


def save_projects(
    connection: Any,
    before_projects: dict,
    after_projects: dict,
    before_teams: dict,
    after_teams: dict,
    loaded_project_ids: set[str],
) -> None:
    """执行事务内项目与团队配置的增量差异持久化，支持版本乐观锁校验。"""
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
            "deadline_at": to_utc_naive(deadline_at),
            "security_level": security_level or "internal",
            "industry": industry or "it",
            "is_archived": 1 if is_archived else 0,
            "created_by": created_by or "",
            "created_at": to_utc_naive(created_at),
            "updated_by": updated_by or "",
            "updated_at": to_utc_naive(updated_at),
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


# 兼容既有测试与内部私有引用
_project_snapshot = project_snapshot
_team_snapshot = team_snapshot
_save_projects = save_projects
