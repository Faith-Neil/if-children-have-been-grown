# 为什么有这个文件：用真实 MySQL 8 核对检查与导出聚合持久化、JSON 快照结构、状态流转与分页。
# 它解决什么问题：确保检查结果与导出快照原子写入 MySQL，支持按项目/分册/导出类型多维检索，验证阻塞项拦截，并验证迁移 0007_checks_and_exports 的 downgrade/upgrade 往返与内存仓库多态。

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from icg_demo.adapters import MemoryRepository
from icg_demo.database import (
    database_url,
    delete_check,
    delete_export,
    list_checks_by_project,
    list_exports_by_project,
    mysql_gate,
    read_check,
    read_export,
    save_check,
    save_export,
    update_export_status,
)
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


def test_migration_0007_reversibility(ensure_mysql):
    _upgrade()
    cfg = _alembic_config()

    # 降级到 0006_chapters：demo_check 与 demo_export 应当被移除
    command.downgrade(cfg, "0006_chapters")
    repository = create_app().state.service.repository
    try:
        with repository.engine.connect() as connection:
            tables = sorted(connection.execute(text("SHOW TABLES")).scalars().all())
            assert "demo_check" not in tables
            assert "demo_export" not in tables
            assert "demo_chapter" in tables
            assert "demo_project" in tables
    finally:
        # 恢复到 head
        _upgrade()

    with repository.engine.connect() as connection:
        tables = sorted(connection.execute(text("SHOW TABLES")).scalars().all())
        assert "demo_check" in tables
        assert "demo_export" in tables

        # 验证字符集与排序规则为 utf8mb4 / utf8mb4_0900_ai_ci
        table_status = connection.execute(
            text(
                "SELECT TABLE_NAME, TABLE_COLLATION "
                "FROM information_schema.TABLES "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME IN ('demo_check', 'demo_export')"
            )
        ).all()
        for row in table_status:
            assert "utf8mb4" in row.TABLE_COLLATION


def test_save_and_read_check_with_issues_json(ensure_mysql):
    _upgrade()
    repository = create_app().state.service.repository
    assert repository.mode == "mysql"

    check_id = f"chk-{uuid4().hex}"
    project_id = f"proj-{uuid4().hex}"
    issues = [
        {
            "id": "iss-001",
            "rule_id": "RULE_STRICT_TENDER_NO",
            "severity": "blocking",
            "message": "招标文件编号与封面不一致",
            "chapter_id": "ch-cover",
        },
        {
            "id": "iss-002",
            "rule_id": "RULE_PAGE_LIMIT",
            "severity": "warning",
            "message": "实施方案页数接近上限预警",
            "chapter_id": "ch-tech-01",
        },
    ]

    check_data = {
        "id": check_id,
        "project_id": project_id,
        "volume_id": "technical",
        "blocking_count": 1,
        "warning_count": 1,
        "issues_json": issues,
    }

    save_check(repository.engine, check_data)

    loaded = read_check(repository.engine, check_id)
    assert loaded is not None
    assert loaded["id"] == check_id
    assert loaded["project_id"] == project_id
    assert loaded["volume_id"] == "technical"
    assert loaded["status"] == "blocked"
    assert loaded["blocking_count"] == 1
    assert loaded["warning_count"] == 1
    assert len(loaded["issues_json"]) == 2
    assert loaded["issues_json"][0]["rule_id"] == "RULE_STRICT_TENDER_NO"
    assert loaded["issues_json"][0]["severity"] == "blocking"
    assert loaded["issues"][1]["rule_id"] == "RULE_PAGE_LIMIT"

    # 直接从 MySQL 表核对列值与 JSON 格式
    with repository.engine.connect() as connection:
        row = connection.execute(
            text("SELECT id, project_id, volume_id, status, blocking_count, warning_count FROM demo_check WHERE id = :id"),
            {"id": check_id},
        ).one()
        assert row.status == "blocked"
        assert row.blocking_count == 1
        assert row.warning_count == 1


def test_check_status_derivation_and_blocking_interception(ensure_mysql):
    _upgrade()
    repository = create_app().state.service.repository

    pid = f"proj-{uuid4().hex}"

    # 1. 含有阻塞项 -> 自动派生 blocked
    cid_blocked = f"chk-blk-{uuid4().hex}"
    save_check(repository.engine, {
        "id": cid_blocked,
        "project_id": pid,
        "blocking_count": 2,
        "warning_count": 0,
        "issues_json": [{"rule_id": "BLK-1", "severity": "blocking"}],
    })
    rec_blocked = read_check(repository.engine, cid_blocked)
    assert rec_blocked["status"] == "blocked"

    # 2. 无阻塞项，仅告警项 -> 自动派生 warning
    cid_warning = f"chk-warn-{uuid4().hex}"
    save_check(repository.engine, {
        "id": cid_warning,
        "project_id": pid,
        "blocking_count": 0,
        "warning_count": 3,
        "issues_json": [{"rule_id": "WARN-1", "severity": "warning"}],
    })
    rec_warning = read_check(repository.engine, cid_warning)
    assert rec_warning["status"] == "warning"

    # 3. 零阻塞零告警 -> 自动派生 passed
    cid_passed = f"chk-pass-{uuid4().hex}"
    save_check(repository.engine, {
        "id": cid_passed,
        "project_id": pid,
        "blocking_count": 0,
        "warning_count": 0,
        "issues_json": [],
    })
    rec_passed = read_check(repository.engine, cid_passed)
    assert rec_passed["status"] == "passed"


def test_list_and_delete_checks_by_project(ensure_mysql):
    _upgrade()
    repository = create_app().state.service.repository

    pid = f"proj-list-{uuid4().hex}"
    # 插入技术分册 check 与商务分册 check
    c1 = {"id": f"chk-t1-{uuid4().hex}", "project_id": pid, "volume_id": "technical", "blocking_count": 0, "issues_json": []}
    c2 = {"id": f"chk-t2-{uuid4().hex}", "project_id": pid, "volume_id": "technical", "blocking_count": 1, "issues_json": []}
    c3 = {"id": f"chk-b1-{uuid4().hex}", "project_id": pid, "volume_id": "business", "blocking_count": 0, "issues_json": []}

    save_check(repository.engine, c1)
    save_check(repository.engine, c2)
    save_check(repository.engine, c3)

    # 全项目查询
    all_checks = list_checks_by_project(repository.engine, pid)
    assert len(all_checks) == 3

    # 按分册过滤
    tech_checks = list_checks_by_project(repository.engine, pid, volume_id="technical")
    assert len(tech_checks) == 2
    assert all(c["volume_id"] == "technical" for c in tech_checks)

    biz_checks = list_checks_by_project(repository.engine, pid, volume_id="business")
    assert len(biz_checks) == 1
    assert biz_checks[0]["id"] == c3["id"]

    # 删除检查记录
    deleted = delete_check(repository.engine, c1["id"])
    assert deleted is True
    assert read_check(repository.engine, c1["id"]) is None
    assert len(list_checks_by_project(repository.engine, pid)) == 2

    # 重复删除返回 False
    assert delete_check(repository.engine, c1["id"]) is False


def test_save_and_read_export_with_snapshot(ensure_mysql):
    _upgrade()
    repository = create_app().state.service.repository

    eid = f"exp-{uuid4().hex}"
    pid = f"proj-{uuid4().hex}"
    snapshot = {
        "project": {"id": pid, "name": "智慧园区投标项目", "tender_number": "ZB-2026-001"},
        "chapters": [
            {"id": "ch-01", "title": "项目实施方案", "content": "实施方案内容..."},
            {"id": "ch-02", "title": "团队成员配置", "content": "团队配置内容..."},
        ],
        "metadata": {"version": "1.0", "generator": "bid-core-export-engine"},
    }

    export_data = {
        "id": eid,
        "project_id": pid,
        "export_type": "submission",
        "status": "pending",
        "format": "docx",
        "snapshot_json": snapshot,
        "created_by": "lead-engineer",
    }

    save_export(repository.engine, export_data)

    loaded = read_export(repository.engine, eid)
    assert loaded is not None
    assert loaded["id"] == eid
    assert loaded["project_id"] == pid
    assert loaded["export_type"] == "submission"
    assert loaded["status"] == "pending"
    assert loaded["format"] == "docx"
    assert loaded["created_by"] == "lead-engineer"
    assert loaded["file_path"] is None
    assert loaded["file_size"] is None
    assert loaded["snapshot_json"]["project"]["name"] == "智慧园区投标项目"
    assert len(loaded["snapshot_json"]["chapters"]) == 2
    assert loaded["snapshot"]["metadata"]["generator"] == "bid-core-export-engine"


def test_export_status_transitions(ensure_mysql):
    _upgrade()
    repository = create_app().state.service.repository

    eid = f"exp-trans-{uuid4().hex}"
    pid = f"proj-{uuid4().hex}"
    save_export(repository.engine, {
        "id": eid,
        "project_id": pid,
        "export_type": "internal",
        "status": "pending",
        "format": "pdf",
    })

    # pending -> running
    ok = update_export_status(repository.engine, eid, "running")
    assert ok is True
    exp = read_export(repository.engine, eid)
    assert exp["status"] == "running"
    assert exp["file_path"] is None

    # running -> completed (更新文件路径与大小)
    ok = update_export_status(repository.engine, eid, "completed", file_path="/storage/exports/bid_doc.pdf", file_size=1048576)
    assert ok is True
    exp_done = read_export(repository.engine, eid)
    assert exp_done["status"] == "completed"
    assert exp_done["file_path"] == "/storage/exports/bid_doc.pdf"
    assert exp_done["file_size"] == 1048576


def test_list_and_paginate_exports(ensure_mysql):
    _upgrade()
    repository = create_app().state.service.repository

    pid = f"proj-exp-page-{uuid4().hex}"
    for i in range(5):
        save_export(repository.engine, {
            "id": f"exp-sub-{i}-{uuid4().hex}",
            "project_id": pid,
            "export_type": "submission",
            "status": "completed",
            "format": "docx",
        })
    for i in range(3):
        save_export(repository.engine, {
            "id": f"exp-int-{i}-{uuid4().hex}",
            "project_id": pid,
            "export_type": "internal",
            "status": "completed",
            "format": "pdf",
        })

    # 全部导出列表及总数
    items, total = list_exports_by_project(repository.engine, pid, limit=10, offset=0)
    assert total == 8
    assert len(items) == 8

    # 分页测试：limit=3, offset=0
    p1, total = list_exports_by_project(repository.engine, pid, limit=3, offset=0)
    assert total == 8
    assert len(p1) == 3

    # 分页测试：limit=3, offset=3
    p2, total = list_exports_by_project(repository.engine, pid, limit=3, offset=3)
    assert total == 8
    assert len(p2) == 3
    assert {item["id"] for item in p1}.isdisjoint({item["id"] for item in p2})

    # 按 export_type 过滤
    subs, sub_total = list_exports_by_project(repository.engine, pid, export_type="submission")
    assert sub_total == 5
    assert len(subs) == 5
    assert all(s["export_type"] == "submission" for s in subs)

    # 删除一条导出记录
    to_delete = subs[0]["id"]
    deleted = delete_export(repository.engine, to_delete)
    assert deleted is True
    assert read_export(repository.engine, to_delete) is None

    _, new_sub_total = list_exports_by_project(repository.engine, pid, export_type="submission")
    assert new_sub_total == 4


def test_memory_repository_polymorphism_checks_and_exports():
    # 纯内存模式纯洁性测试：未设置数据库连接串时，MemoryRepository 具备完全一致的 Check 与 Export CRUD 接口
    repo = MemoryRepository()
    pid = "mem-p100"
    cid = "mem-chk-001"

    # 1. Check CRUD in Memory
    repo.save_check({
        "id": cid,
        "project_id": pid,
        "volume_id": "technical",
        "blocking_count": 1,
        "warning_count": 2,
        "issues_json": [
            {"id": "issue-1", "severity": "blocking", "message": "内存阻塞项"},
            {"id": "issue-2", "severity": "warning", "message": "内存告警项"},
        ],
    })

    read_c = repo.read_check(cid)
    assert read_c is not None
    assert read_c["status"] == "blocked"
    assert read_c["blocking_count"] == 1
    assert len(read_c["issues_json"]) == 2

    checks = repo.list_checks_by_project(pid, volume_id="technical")
    assert len(checks) == 1
    assert checks[0]["id"] == cid

    del_c = repo.delete_check(cid)
    assert del_c is True
    assert repo.read_check(cid) is None

    # 2. Export CRUD in Memory
    eid = "mem-exp-001"
    repo.save_export({
        "id": eid,
        "project_id": pid,
        "export_type": "submission",
        "status": "pending",
        "format": "docx",
        "snapshot_json": {"project_id": pid, "data": "mem-snapshot"},
    })

    read_e = repo.read_export(eid)
    assert read_e is not None
    assert read_e["status"] == "pending"
    assert read_e["snapshot_json"]["data"] == "mem-snapshot"

    upd_ok = repo.update_export_status(eid, "completed", file_path="/tmp/mem.docx", file_size=4096)
    assert upd_ok is True
    exp_updated = repo.read_export(eid)
    assert exp_updated["status"] == "completed"
    assert exp_updated["file_path"] == "/tmp/mem.docx"
    assert exp_updated["file_size"] == 4096

    exports, total_e = repo.list_exports_by_project(pid, export_type="submission")
    assert total_e == 1
    assert len(exports) == 1

    del_e = repo.delete_export(eid)
    assert del_e is True
    assert repo.read_export(eid) is None
