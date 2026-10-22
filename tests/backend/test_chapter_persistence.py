# 为什么有这个文件：用真实 MySQL 8 核对章节聚合持久化、版本历史记录与乐观锁并发控制。
# 它解决什么问题：确保章节正文和历史版本原子写入 MySQL，stale revision 无法静默覆盖，事务失败时原子回滚，并验证迁移 downgrade/upgrade 往返。

import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from icg_demo.adapters import MemoryRepository
from icg_demo.database import (
    commit_chapter_version,
    database_url,
    mysql_gate,
    read_chapter,
    save_chapter,
)
from icg_demo.domain import Chapter, DomainError
from icg_demo.main import create_app

pytestmark = pytest.mark.mysql

ROOT = Path(__file__).resolve().parents[2]


def _alembic_config() -> Config:
    cfg = Config()
    cfg.set_main_option("script_location", str(ROOT / "backend" / "bid-core" / "alembic"))
    return cfg


def _upgrade() -> None:
    command.upgrade(_alembic_config(), "head")


def _downgrade(revision: str = "base") -> None:
    command.downgrade(_alembic_config(), revision)


@pytest.fixture
def ensure_mysql():
    gate = mysql_gate()
    if gate.action == "skip":
        pytest.skip(gate.reason)
    if gate.action == "fail":
        pytest.fail(gate.reason)


def test_chapter_save_and_read(ensure_mysql):
    _upgrade()
    repository = create_app().state.service.repository
    assert repository.mode == "mysql"

    chapter_id = f"ch-{uuid4().hex}"
    project_id = f"proj-{uuid4().hex}"
    chapter = Chapter(
        id=chapter_id,
        project_id=project_id,
        title="技术实施方案",
        volume="technical",
        content="第1版本初始正文内容",
        revision=1,
        assignee_id="alpha-editor",
    )

    save_chapter(repository.engine, chapter)

    loaded = read_chapter(repository.engine, chapter_id)
    assert loaded is not None
    assert loaded["id"] == chapter_id
    assert loaded["project_id"] == project_id
    assert loaded["title"] == "技术实施方案"
    assert loaded["volume"] == "technical"
    assert loaded["content"] == "第1版本初始正文内容"
    assert loaded["revision"] == 1
    assert loaded["assignee_id"] == "alpha-editor"
    assert isinstance(loaded["updated_at"], datetime)

    # 验证直接从 MySQL demo_chapter 表读取
    with repository.engine.connect() as connection:
        row = connection.execute(
            text("SELECT id, project_id, volume, title, content, revision, assignee_id FROM demo_chapter WHERE id = :id"),
            {"id": chapter_id},
        ).one()
        assert row.id == chapter_id
        assert row.revision == 1
        assert row.content == "第1版本初始正文内容"


def test_chapter_version_commit_in_same_transaction(ensure_mysql):
    _upgrade()
    repository = create_app().state.service.repository

    chapter_id = f"ch-ver-{uuid4().hex}"
    project_id = f"proj-{uuid4().hex}"
    chapter = Chapter(
        id=chapter_id,
        project_id=project_id,
        title="商务响应章节",
        volume="business",
        content="商务初始草稿",
        revision=1,
        assignee_id="beta-editor",
    )
    save_chapter(repository.engine, chapter)

    record = commit_chapter_version(
        repository.engine,
        chapter_id=chapter_id,
        content="商务响应正文第二版（已确认）",
        expected_revision=1,
        new_revision=2,
        created_by="beta-editor",
    )

    assert record["revision"] == 2
    assert record["version_number"] == 2
    assert record["content"] == "商务响应正文第二版（已确认）"
    assert record["actor_id"] == "beta-editor"
    assert "created_at" in record

    # 验证 demo_chapter 表已被原子更新
    loaded = read_chapter(repository.engine, chapter_id)
    assert loaded is not None
    assert loaded["revision"] == 2
    assert loaded["content"] == "商务响应正文第二版（已确认）"
    assert len(loaded["versions"]) == 1
    assert loaded["versions"][0]["version_number"] == 2
    assert loaded["versions"][0]["content"] == "商务响应正文第二版（已确认）"
    assert loaded["versions"][0]["created_by"] == "beta-editor"

    # 验证 demo_chapter_version 表记录
    with repository.engine.connect() as connection:
        ver_rows = connection.execute(
            text("SELECT version_number, content, created_by FROM demo_chapter_version WHERE chapter_id = :cid"),
            {"cid": chapter_id},
        ).all()
        assert len(ver_rows) == 1
        assert ver_rows[0].version_number == 2
        assert ver_rows[0].content == "商务响应正文第二版（已确认）"
        assert ver_rows[0].created_by == "beta-editor"


def test_optimistic_locking_prevents_stale_revision_overwrite(ensure_mysql):
    _upgrade()
    repository = create_app().state.service.repository

    chapter_id = f"ch-opt-{uuid4().hex}"
    project_id = f"proj-{uuid4().hex}"
    save_chapter(repository.engine, Chapter(
        id=chapter_id,
        project_id=project_id,
        title="并发测试章节",
        volume="technical",
        content="基线正文",
        revision=1,
    ))

    # 会话 A 率先更新到版本 2
    res_a = commit_chapter_version(
        repository.engine,
        chapter_id=chapter_id,
        content="会话 A 成功更新的正文",
        expected_revision=1,
        new_revision=2,
        created_by="writer-A",
    )
    assert res_a["revision"] == 2

    # 会话 B 持有过期版本 1，尝试提交更新 -> 乐观锁拦截
    with pytest.raises(DomainError) as exc_info:
        commit_chapter_version(
            repository.engine,
            chapter_id=chapter_id,
            content="会话 B 冲突提交的正文",
            expected_revision=1,
            new_revision=2,
            created_by="writer-B",
        )

    assert exc_info.value.status == 409
    assert exc_info.value.code == "REVISION_CONFLICT"

    # 验证库中 demo_chapter 未被静默覆盖，版本历史也未留存冲突数据
    loaded = read_chapter(repository.engine, chapter_id)
    assert loaded is not None
    assert loaded["revision"] == 2
    assert loaded["content"] == "会话 A 成功更新的正文"
    assert len(loaded["versions"]) == 1
    assert loaded["versions"][0]["created_by"] == "writer-A"


def test_transaction_failure_rolls_back_chapter_and_versions(ensure_mysql):
    _upgrade()
    repository = create_app().state.service.repository

    chapter_id = f"ch-tx-{uuid4().hex}"
    project_id = f"proj-{uuid4().hex}"
    save_chapter(repository.engine, Chapter(
        id=chapter_id,
        project_id=project_id,
        title="事务回滚测试章节",
        volume="technical",
        content="原版完整正文",
        revision=1,
    ))

    # 模拟在同一个事务中更新章节后发生异常
    with pytest.raises(RuntimeError, match="simulated failure"):
        with repository.engine.begin() as conn:
            conn.execute(
                text("UPDATE demo_chapter SET content = '未提交脏数据', revision = 99 WHERE id = :id"),
                {"id": chapter_id},
            )
            conn.execute(
                text(
                    "INSERT INTO demo_chapter_version (id, chapter_id, version_number, content, created_by, created_at) "
                    "VALUES (:id, :cid, 99, '未提交脏版本', 'bad-user', UTC_TIMESTAMP(6))"
                ),
                {"id": f"bad-{uuid4().hex}", "cid": chapter_id},
            )
            raise RuntimeError("simulated failure")

    # 验证整个事务已回滚，demo_chapter 和 demo_chapter_version 均恢复原状
    loaded = read_chapter(repository.engine, chapter_id)
    assert loaded is not None
    assert loaded["revision"] == 1
    assert loaded["content"] == "原版完整正文"

    with repository.engine.connect() as conn:
        bad_versions = conn.execute(
            text("SELECT COUNT(*) FROM demo_chapter_version WHERE chapter_id = :cid AND version_number = 99"),
            {"cid": chapter_id},
        ).scalar()
        assert bad_versions == 0


def test_alembic_downgrade_base_and_upgrade_head_roundtrip(ensure_mysql):
    # 测试能够从 head 降回 base，再升级恢复
    _upgrade()
    try:
        _downgrade("base")
        repository = create_app().state.service.repository
        with repository.engine.connect() as connection:
            remaining = sorted(connection.execute(text("SHOW TABLES")).scalars().all())
        assert "demo_chapter" not in remaining
        assert "demo_chapter_version" not in remaining
    finally:
        _upgrade()

    repository = create_app().state.service.repository
    with repository.engine.connect() as connection:
        tables = sorted(connection.execute(text("SHOW TABLES")).scalars().all())
        assert "demo_chapter" in tables
        assert "demo_chapter_version" in tables

        # 验证字符集与排序规则
        table_status = connection.execute(
            text(
                "SELECT TABLE_NAME, TABLE_COLLATION "
                "FROM information_schema.TABLES "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME IN ('demo_chapter', 'demo_chapter_version')"
            )
        ).all()
        for row in table_status:
            assert "utf8mb4" in row.TABLE_COLLATION


def test_memory_repository_polymorphism_and_optimistic_locking():
    # 纯内存模式纯洁性测试：未设置数据库连接串时，内存仓库具备完全一致的接口和乐观锁拦截行为
    repo = MemoryRepository()
    ch_id = "mem-tech-001"
    repo.save_chapter({
        "id": ch_id,
        "project_id": "mem-p1",
        "title": "内存技术章节",
        "volume": "technical",
        "content": "初始内存正文",
        "revision": 1,
        "assignee_id": "mem-writer",
    })

    read_back = repo.read_chapter(ch_id)
    assert read_back is not None
    assert read_back["revision"] == 1
    assert read_back["content"] == "初始内存正文"

    # 提交新版本
    committed = repo.commit_chapter_version(ch_id, "第二版内存正文", expected_revision=1, new_revision=2, created_by="writer-01")
    assert committed["revision"] == 2
    assert len(repo.read_chapter(ch_id)["versions"]) == 1

    # 过期版本拦截
    with pytest.raises(DomainError) as exc:
        repo.commit_chapter_version(ch_id, "冲突提交", expected_revision=1, new_revision=3, created_by="writer-02")
    assert exc.value.status == 409
    assert exc.value.code == "REVISION_CONFLICT"
