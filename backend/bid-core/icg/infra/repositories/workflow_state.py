# 为什么有这个文件：把项目工作流中 Wave 11 新增的聚合（人工处理队列、分册定稿/复核/解锁轮次、兜底扫描）同步到 MySQL。
# 它解决什么问题：这些记录跟着事务前后快照做脏检查，只写有变化的项目；另一个进程读取时合并回本项目工作流。

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text

from icg.infra.repositories.common import json_value

PERSISTED_WORKFLOW_KEYS: tuple[str, ...] = (
    "volumes", "volume_reviews", "volume_epochs", "human_queue", "post_process",
)


def workflow_state_snapshot(state: Any) -> dict[str, str]:
    snapshot: dict[str, str] = {}
    for project_id, workflow in state.workflows.items():
        if not isinstance(workflow, dict):
            continue
        part = {key: workflow[key] for key in PERSISTED_WORKFLOW_KEYS if key in workflow}
        if part:
            snapshot[project_id] = json.dumps(part, sort_keys=True, ensure_ascii=False, default=str)
    return snapshot


def load_workflow_state(connection: Any, state: Any) -> None:
    rows = connection.execute(text("SELECT project_id, state_json FROM demo_project_workflow_state")).all()
    for project_id, raw in rows:
        part = json_value(raw) or {}
        workflow = state.workflows.get(project_id)
        if workflow is None:
            from icg.domain.workflow_orchestrator import _blank_workflow
            workflow = state.workflows.setdefault(project_id, _blank_workflow())
        for key in PERSISTED_WORKFLOW_KEYS:
            if key in part:
                workflow[key] = part[key]


def save_workflow_state_diff(connection: Any, before: dict[str, str], after: dict[str, str]) -> None:
    for project_id in set(before) | set(after):
        previous, current = before.get(project_id), after.get(project_id)
        if previous == current:
            continue
        if current is None:
            connection.execute(text("DELETE FROM demo_project_workflow_state WHERE project_id = :id"),
                               {"id": project_id})
            continue
        connection.execute(
            text(
                "INSERT INTO demo_project_workflow_state (project_id, state_json, updated_at) "
                "VALUES (:id, CAST(:state_json AS JSON), UTC_TIMESTAMP(6)) AS incoming "
                "ON DUPLICATE KEY UPDATE state_json = incoming.state_json, updated_at = incoming.updated_at"
            ),
            {"id": project_id, "state_json": current},
        )
