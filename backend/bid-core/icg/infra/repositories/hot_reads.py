# 为什么有这个文件：高频只读接口的按作用域 MySQL 查询（ISSUE-055）。
# 它解决什么问题：鉴权、会话、项目列表、公司设置与单项目工作台不再通过 repository.read() 加载全部公司、
# 全部项目工作流、全部章节正文与全部历史版本；只按当前令牌、公司、项目或条目精确读取。

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import bindparam, text

from icg.domain.domain import Chapter, DemoState, Lease, Project, iso_time
from icg.infra.repositories.chapters import merge_meta
from icg.infra.repositories.common import as_timestamp, json_value, parse_db_timestamp
from icg.infra.repositories.state_entries import _apply, loads

_PROJECT_COLUMNS = (
    "id", "name", "company_id", "revision", "tender_number", "deadline", "is_sensitive",
    "tender_type", "budget_amount_cents", "deadline_at", "security_level", "industry", "is_archived",
    "created_by", "created_at", "updated_by", "updated_at", "record_version", "is_deleted",
    "last_accessed_at", "status",
)


def project_from_mapping(data: dict) -> Project:
    """从 SELECT 出的列重建项目对象；缺列时保持旧 schema 默认值。"""
    return Project(
        id=data["id"],
        name=data.get("name") or "",
        company_id=data.get("company_id") or "",
        revision=int(data.get("revision") or 1),
        tender_number=data.get("tender_number") or "",
        deadline=data.get("deadline") or "",
        sensitive=bool(data.get("is_sensitive") or 0),
        tender_type=data.get("tender_type") or "comprehensive",
        budget_amount_cents=int(data.get("budget_amount_cents") or 0),
        deadline_at=parse_db_timestamp(data.get("deadline_at")),
        security_level=data.get("security_level") or "internal",
        industry=data.get("industry") or "it",
        is_archived=bool(data.get("is_archived") or 0),
        created_by=data.get("created_by") or "",
        created_at=parse_db_timestamp(data.get("created_at")),
        updated_by=data.get("updated_by") or "",
        updated_at=parse_db_timestamp(data.get("updated_at")),
        record_version=int(data.get("record_version") or 1),
        is_deleted=bool(data.get("is_deleted") or 0),
        last_accessed_at=parse_db_timestamp(data.get("last_accessed_at")),
        status=data.get("status") or "preparing",
    )


def entry(connection: Any, scope: str, entry_id: str) -> Any | None:
    row = connection.execute(
        text("SELECT body FROM demo_state_entry WHERE scope = :scope AND entry_id = :id"),
        {"scope": scope, "id": entry_id},
    ).one_or_none()
    return None if row is None else loads(row[0])


def apply_entry(connection: Any, state: DemoState, scope: str, entry_id: str) -> bool:
    row = connection.execute(
        text("SELECT body FROM demo_state_entry WHERE scope = :scope AND entry_id = :id"),
        {"scope": scope, "id": entry_id},
    ).one_or_none()
    if row is None:
        return False
    _apply(state, scope, entry_id, loads(row[0]))
    return True


def apply_entries(connection: Any, state: DemoState, scope: str, entry_ids: list[str]) -> None:
    ids = sorted({str(item) for item in entry_ids if item})
    if not ids:
        return
    statement = text("SELECT entry_id, body FROM demo_state_entry WHERE scope = :scope AND entry_id IN :ids") \
        .bindparams(bindparam("ids", expanding=True))
    for start in range(0, len(ids), 500):
        rows = connection.execute(statement, {"scope": scope, "ids": ids[start:start + 500]}).all()
        for entry_id, body in rows:
            _apply(state, scope, entry_id, loads(body))



def apply_entries_by_json_field(connection: Any, state: DemoState, scope: str, field: str, value: str) -> None:
    """按条目 JSON 顶层字段精确过滤，只把匹配的行反序列化进热状态。

    不能用 LIKE 依赖紧凑 JSON 字符串：历史行的冒号后空格、键序或 Unicode 转义差异都不是业务差异。
    MySQL 在 SQL 层取顶层键，仍只加载本公司条目；非 MySQL 的单元测试替身按同一语义过滤。
    """
    dialect = getattr(getattr(connection, "dialect", None), "name", "")
    if dialect == "mysql" and field.isidentifier():
        rows = connection.execute(text(
            f"SELECT entry_id, body FROM demo_state_entry WHERE scope = :scope "
            f"AND JSON_UNQUOTE(JSON_EXTRACT(body, '$.{field}')) COLLATE utf8mb4_bin = :value ORDER BY entry_id"
        ), {"scope": scope, "value": value}).all()
    else:
        candidates = connection.execute(text(
            "SELECT entry_id, body FROM demo_state_entry WHERE scope = :scope ORDER BY entry_id"
        ), {"scope": scope}).all()
        rows = []
        for entry_id, body in candidates:
            decoded = loads(body)
            if isinstance(decoded, dict) and decoded.get(field) == value:
                rows.append((entry_id, body))
    for entry_id, body in rows:
        _apply(state, scope, entry_id, loads(body))


def apply_service_stores(connection: Any, state: DemoState) -> None:
    rows = connection.execute(text("SELECT entry_id, body FROM demo_state_entry WHERE scope = 'service_store'")).all()
    for entry_id, body in rows:
        _apply(state, "service_store", entry_id, loads(body))


def apply_accounts(connection: Any, state: DemoState) -> None:
    rows = connection.execute(text("SELECT entry_id, body FROM demo_state_entry WHERE scope = 'account'")).all()
    for entry_id, body in rows:
        _apply(state, "account", entry_id, loads(body))


def apply_development_seed_accounts(repository: Any, state: DemoState) -> None:
    """非生产 MySQL 开发库补齐内存种子账号；只填空缺，绝不覆盖条目表里的真实账号。

    种子账号从未写入 demo_state_entry，但登录会话写在 user_session 表。生产模式
    MysqlConnectionRepository 的内存态为空，因此这里自然不会把合成账号带进生产。
    """
    seeded = getattr(repository, "_development_seed_accounts", None)
    if seeded is None:
        memory = getattr(repository, "_memory", None)
        if memory is None:
            return
        try:
            seeded = memory.read().accounts
        except Exception:
            return
    for account_id, account in seeded.items():
        if account_id not in state.accounts and getattr(account, "_DEMO_ONLY", False):
            state.accounts[account_id] = account


def project_column_names(repository: Any, connection: Any) -> set[str]:
    cached = getattr(repository, "_project_columns_cache", None)
    if cached is not None:
        return cached
    rows = connection.execute(text(
        "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'demo_project'"
    )).all()
    columns = {row[0] for row in rows}
    repository._project_columns_cache = columns
    return columns


def load_projects(connection: Any, repository: Any, state: DemoState, project_id: str | None = None) -> None:
    available = project_column_names(repository, connection)
    columns = [column for column in _PROJECT_COLUMNS if column in available]
    sql = "SELECT " + ", ".join(columns) + " FROM demo_project"
    params: dict[str, Any] = {}
    if project_id is not None:
        sql += " WHERE id = :id"
        params["id"] = project_id
    rows = connection.execute(text(sql), params).all()
    for row in rows:
        project = project_from_mapping(dict(row._mapping))
        state.projects[project.id] = project
    team_sql = "SELECT project_id, team_json FROM demo_project_team"
    if project_id is not None:
        team_sql += " WHERE project_id = :id"
    for team_project_id, team_json in connection.execute(text(team_sql), params).all():
        state.project_teams[team_project_id] = json_value(team_json)


def load_project_chapters(connection: Any, state: DemoState, project_id: str, *,
                          include_content: bool, include_versions: bool) -> None:
    rows = connection.execute(text(
        "SELECT id, project_id, volume, title, content, revision, assignee_id "
        "FROM demo_chapter WHERE project_id = :project_id ORDER BY id"
    ), {"project_id": project_id}).all()
    chapter_ids = []
    for cid, pid, volume, title, content, revision, assignee_id in rows:
        chapter_ids.append(cid)
        state.chapters[cid] = Chapter(
            id=cid, project_id=pid, title=title, volume=volume,
            content=content if include_content else "", revision=int(revision),
            assignee_id=assignee_id, versions=[],
        )
    if not chapter_ids:
        return
    try:
        lease_rows = connection.execute(text(
            "SELECT chapter_id, token, owner_id, session_token, expires_at, acquired_at, heartbeat_at, "
            "lock_reason, taken_over_from_user_id, takeover_reason, released_at, release_reason, company_id, record_version "
            "FROM chapter_lease WHERE released_at IS NULL AND chapter_id IN :ids"
        ).bindparams(bindparam("ids", expanding=True)), {"ids": chapter_ids}).all()
    except Exception:
        lease_rows = connection.execute(text(
            "SELECT chapter_id, token, owner_id, session_token, expires_at FROM chapter_lease WHERE chapter_id IN :ids"
        ).bindparams(bindparam("ids", expanding=True)), {"ids": chapter_ids}).all()
    for row in lease_rows:
        if len(row) >= 14:
            lease = Lease(
                token=row[1], owner_id=row[2], session_token=row[3], expires_at=as_timestamp(row[4]),
                acquired_at=as_timestamp(row[5]) if row[5] else None,
                heartbeat_at=as_timestamp(row[6]) if row[6] else None,
                lock_reason=row[7], taken_over_from_user_id=row[8], takeover_reason=row[9],
                released_at=as_timestamp(row[10]) if row[10] else None,
                release_reason=row[11], company_id=row[12],
                record_version=int(row[13]) if row[13] is not None else 1,
            )
        else:
            lease = Lease(row[1], row[2], row[3], as_timestamp(row[4]))
        if row[0] in state.chapters:
            state.chapters[row[0]].lock = lease
    if not include_versions:
        return
    version_statement = text(
        "SELECT id, chapter_id, version_number, content, created_by, created_at, meta "
        "FROM demo_chapter_version WHERE chapter_id IN :ids ORDER BY version_number ASC"
    ).bindparams(bindparam("ids", expanding=True))
    versions_by_cid: dict[str, list[dict]] = {}
    for vid, cid, version_number, content, created_by, created_at, meta in connection.execute(
            version_statement, {"ids": chapter_ids}).all():
        versions_by_cid.setdefault(cid, []).append(merge_meta({
            "id": vid, "chapter_id": cid, "revision": int(version_number),
            "version_number": int(version_number), "content": content,
            "actor_id": created_by, "created_by": created_by,
            "created_at": iso_time(as_timestamp(created_at)) if isinstance(created_at, datetime) else str(created_at),
        }, meta))
    for cid, versions in versions_by_cid.items():
        if cid in state.chapters:
            state.chapters[cid].versions = versions


def read_auth_state(repository: Any, token: str) -> DemoState:
    """登录态鉴权只读会话行、账号条目与公司状态；绝不加载项目、章节正文或工作流。"""
    state = DemoState()
    with repository.engine.begin() as connection:
        row = connection.execute(
            text("SELECT user_id FROM user_session WHERE token = :token"), {"token": token}
        ).one_or_none()
        if row is None:
            return state
        user_id = row[0]
        state.sessions[token] = user_id
        apply_entry(connection, state, "account", user_id)
        apply_entry(connection, state, "service_store", "companies")
        apply_entry(connection, state, "service_store", "platform_security")
        apply_entry(connection, state, "service_store", "session_times")
    apply_development_seed_accounts(repository, state)
    return state


def read_session_state(repository: Any, principal: Any, project_id: str | None = None) -> DemoState:
    """会话上下文读取项目/团队元数据；只有指定项目时读取章节元数据，不读章节正文和历史版本。"""
    state = DemoState()
    state.sessions[principal.session_token] = principal.user.id
    with repository.engine.begin() as connection:
        apply_accounts(connection, state)
        apply_service_stores(connection, state)
        load_projects(connection, repository, state)
        if project_id:
            load_project_chapters(connection, state, project_id, include_content=False, include_versions=False)
    apply_development_seed_accounts(repository, state)
    return state


def read_project_brief_state(repository: Any, project_id: str, principal: Any) -> DemoState:
    """单项目摘要读取：项目行、团队与账号，不读章节、版本、工作流或全库条目。"""
    state = DemoState()
    state.sessions[principal.session_token] = principal.user.id
    with repository.engine.begin() as connection:
        apply_accounts(connection, state)
        apply_service_stores(connection, state)
        load_projects(connection, repository, state, project_id=project_id)
    apply_development_seed_accounts(repository, state)
    return state


def read_project_state(repository: Any, project_id: str, principal: Any) -> DemoState:
    """项目工作台读取：限定本项目的工作流、章节正文与版本、团队成员和项目任务。"""
    state = DemoState()
    state.sessions[principal.session_token] = principal.user.id
    with repository.engine.begin() as connection:
        apply_accounts(connection, state)
        apply_service_stores(connection, state)
        load_projects(connection, repository, state, project_id=project_id)
        load_project_chapters(connection, state, project_id, include_content=True, include_versions=True)
        apply_entry(connection, state, "workflow", project_id)
        workflow = state.workflows.get(project_id) or {}
        evidence_ids = sorted({
            str(item) for row in (workflow.get("requirements") or {}).values()
            for item in (row.get("evidence_ids") or []) if item
        })
        company_id = state.projects[project_id].company_id if project_id in state.projects else "__missing__"
        # 输入指纹历来包含本公司全部资料与 SLA 模板； scoped read 必须保持同一真相源，不能把旧检查/导出误判过期。
        apply_entries_by_json_field(connection, state, "library", "company_id", company_id)
        apply_entries_by_json_field(connection, state, "sla_template", "company_id", company_id)
        # 兼容历史条目缺 company_id 或证据被显式挂载但公司字段异常的情况。
        apply_entries(connection, state, "library", evidence_ids)
        template_id = ((workflow.get("sla") or {}).get("template_id") or "")
        if template_id:
            apply_entry(connection, state, "sla_template", template_id)
        apply_entries_by_json_field(connection, state, "job", "project_id", project_id)
    apply_development_seed_accounts(repository, state)
    return state


def read_service_store(repository: Any, entry_id: str) -> dict:
    with repository.engine.begin() as connection:
        value = entry(connection, "service_store", entry_id)
    return value if isinstance(value, dict) else {}
