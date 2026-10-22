# 为什么有这个文件：向下兼容已有的 icg_demo.database 导入路径。
# 它解决什么问题：将历史导入平滑代理到 icg.infra 模块，保持单文件 < 600 行并消除巨石冗余。

from __future__ import annotations

from icg.infra.mysql_gate import (
    DATABASE_URL_ENV,
    REQUIRE_MYSQL_ENV,
    CHARSET,
    COLLATION,
    CONNECT_TIMEOUT_SECONDS,
    RECEIPT_TTL,
    MysqlGate,
    database_url,
    mysql_required,
    create_mysql_engine,
    mysql_gate,
    repository_from_environment,
)
from icg.infra.repositories.common import (
    utc_naive, as_timestamp, parse_db_timestamp, to_utc_naive, json_value,
    _utc_naive, _as_timestamp, _parse_db_timestamp, _to_utc_naive, _json_value,
)
from icg.infra.repositories.chapters import (
    read_chapter, save_chapter, commit_chapter_version, decompose_paragraphs,
)
from icg.infra.repositories.checks_exports import (
    save_check, read_check, list_checks_by_project, delete_check,
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
from icg.infra.repositories.projects import (
    project_snapshot, team_snapshot, save_projects,
    _project_snapshot, _team_snapshot, _save_projects,
)
from icg.infra.repositories.model_config import (
    save_model_configs, _save_model_configs,
)
from icg.infra.repositories.mysql_repository import (
    MysqlConnectionRepository,
    lease_snapshot, same_receipt,
    _lease_snapshot, _same_receipt,
)

__all__ = [
    "DATABASE_URL_ENV", "REQUIRE_MYSQL_ENV", "CHARSET", "COLLATION",
    "CONNECT_TIMEOUT_SECONDS", "RECEIPT_TTL",
    "MysqlGate", "database_url", "mysql_required", "create_mysql_engine",
    "mysql_gate", "repository_from_environment",
    "MysqlConnectionRepository",
    "read_chapter", "save_chapter", "commit_chapter_version", "decompose_paragraphs",
    "save_check", "read_check", "list_checks_by_project", "delete_check",
    "save_export", "read_export", "update_export_status", "list_exports_by_project", "delete_export",
    "save_library_item", "read_library_item", "list_library_items", "delete_library_item",
    "commit_library_revision", "list_library_revisions",
    "save_sla_template", "read_sla_template", "list_sla_templates", "delete_sla_template",
    "save_workflow", "read_workflow", "delete_workflow",
    "save_job", "read_job", "update_job_progress", "list_jobs_by_project", "delete_job",
    "project_snapshot", "team_snapshot", "save_projects",
    "save_model_configs",
    "lease_snapshot", "same_receipt",
    "_lease_snapshot", "_same_receipt",
    "_project_snapshot", "_team_snapshot", "_save_projects",
    "_save_model_configs",
    "_utc_naive", "_as_timestamp", "_parse_db_timestamp", "_to_utc_naive", "_json_value",
]
