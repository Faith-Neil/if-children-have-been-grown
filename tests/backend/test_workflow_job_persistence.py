# 为什么有这个文件：用真实 MySQL 8 核对工作流状态（demo_workflow）与异步任务（demo_job）的聚合持久化、JSON 结构存储、状态流转、原子进度更新与乐观并发锁。
# 它解决什么问题：确保编制六阶段状态推进与增量复查队列原子写入 MySQL，stale revision 无法并发脏写覆盖，长耗时异步任务跨进程共享断点恢复与进度状态流转，并验证 Alembic 0009 迁移升降级往返与内存仓库多态。

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
    delete_job,
    delete_workflow,
    list_jobs_by_project,
    mysql_gate,
    read_job,
    read_workflow,
    save_job,
    save_workflow,
    update_job_progress,
)
from icg_demo.domain import DomainError
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


def test_alembic_0009_offline_sql_generation():
    # 验证无需真实 MySQL 连接即可通过 Alembic 生成符合 MySQL 8 规范的离线 DDL 与回滚脚本
    import contextlib
    import io
    import os

    cfg = Config()
    cfg.set_main_option("script_location", str(ROOT / "backend" / "bid-core" / "alembic"))

    env_backup = os.environ.get("ICG_DATABASE_URL")
    os.environ["ICG_DATABASE_URL"] = "mysql+pymysql://root:test@127.0.0.1:3306/icg_demo?charset=utf8mb4"
    try:
        buf_up = io.StringIO()
        with contextlib.redirect_stdout(buf_up):
            command.upgrade(cfg, "0008_library_and_sla:0009_workflow_and_jobs", sql=True)
        sql_up = buf_up.getvalue()
        assert "CREATE TABLE demo_workflow" in sql_up
        assert "CREATE TABLE demo_job" in sql_up
        assert "utf8mb4_0900_ai_ci" in sql_up
        assert "PRIMARY KEY (project_id)" in sql_up
        assert "KEY idx_job_project (project_id)" in sql_up

        buf_down = io.StringIO()
        with contextlib.redirect_stdout(buf_down):
            command.downgrade(cfg, "0009_workflow_and_jobs:0008_library_and_sla", sql=True)
        sql_down = buf_down.getvalue()
        assert "DROP TABLE IF EXISTS demo_job" in sql_down
        assert "DROP TABLE IF EXISTS demo_workflow" in sql_down
    finally:
        if env_backup is not None:
            os.environ["ICG_DATABASE_URL"] = env_backup
        else:
            os.environ.pop("ICG_DATABASE_URL", None)


@pytest.fixture
def ensure_mysql():
    gate = mysql_gate()
    if gate.action == "skip":
        pytest.skip(gate.reason)
    if gate.action == "fail":
        pytest.fail(gate.reason)


def test_migration_0009_reversibility(ensure_mysql):
    _upgrade()
    cfg = _alembic_config()

    # 降级到 0008_library_and_sla：demo_workflow 与 demo_job 两张新表应当被干净移除
    command.downgrade(cfg, "0008_library_and_sla")
    repository = create_app().state.service.repository
    try:
        with repository.engine.connect() as connection:
            tables = sorted(connection.execute(text("SHOW TABLES")).scalars().all())
            assert "demo_workflow" not in tables
            assert "demo_job" not in tables
            assert "demo_library_item" in tables
            assert "demo_library_revision" in tables
            assert "demo_sla_template" in tables
            assert "demo_check" in tables
            assert "demo_export" in tables
            assert "demo_chapter" in tables
    finally:
        # 恢复到 head
        _upgrade()

    with repository.engine.connect() as connection:
        tables = sorted(connection.execute(text("SHOW TABLES")).scalars().all())
        assert "demo_workflow" in tables
        assert "demo_job" in tables

        # 验证字符集与排序规则为 utf8mb4 / utf8mb4_0900_ai_ci
        table_status = connection.execute(
            text(
                "SELECT TABLE_NAME, TABLE_COLLATION "
                "FROM information_schema.TABLES "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME IN ('demo_workflow', 'demo_job')"
            )
        ).all()
        for row in table_status:
            assert "utf8mb4" in row.TABLE_COLLATION


def test_workflow_persistence_and_optimistic_locking(ensure_mysql):
    _upgrade()
    repository = create_app().state.service.repository

    project_id = f"proj-wf-{uuid4().hex[:8]}"
    stages_payload = {
        "parsing": {"status": "completed", "parsed_at": "2026-10-21T10:00:00Z"},
        "matrix": {"status": "in_progress", "total_requirements": 42, "matched_requirements": 38},
        "outline": {"status": "pending"},
        "drafting": {"status": "pending"},
        "checking": {"status": "pending"},
        "exporting": {"status": "pending"},
    }
    incremental_checks = [
        {"check_id": "chk-01", "rule": "security_qualification", "passed": True},
        {"check_id": "chk-02", "rule": "financial_audit", "passed": False, "issue": "Missing 2025 audit report"},
    ]

    workflow_data = {
        "project_id": project_id,
        "current_stage": "matrix",
        "stages_json": stages_payload,
        "incremental_checks_json": incremental_checks,
        "revision": 1,
    }

    # 1. 首次保存工作流
    save_workflow(repository.engine, workflow_data)

    record = read_workflow(repository.engine, project_id)
    assert record is not None
    assert record["project_id"] == project_id
    assert record["current_stage"] == "matrix"
    assert record["revision"] == 1
    assert record["stages_json"]["matrix"]["matched_requirements"] == 38
    assert len(record["incremental_checks_json"]) == 2
    assert record["incremental_checks_json"][0]["rule"] == "security_qualification"

    # 2. 正常推进工作流（带期望版本号 revision=1 -> revision=2）
    stages_payload["matrix"]["status"] = "completed"
    stages_payload["outline"]["status"] = "in_progress"
    incremental_checks.append({"check_id": "chk-03", "rule": "sla_consistency", "passed": True})

    save_workflow(
        repository.engine,
        {
            "project_id": project_id,
            "current_stage": "outline",
            "stages_json": stages_payload,
            "incremental_checks_json": incremental_checks,
        },
        expected_revision=1,
    )

    record_v2 = read_workflow(repository.engine, project_id)
    assert record_v2 is not None
    assert record_v2["current_stage"] == "outline"
    assert record_v2["revision"] == 2
    assert len(record_v2["incremental_checks_json"]) == 3

    # 3. 乐观锁冲突拦截（传入陈旧版本 expected_revision=1）
    with pytest.raises(DomainError) as exc_info:
        save_workflow(
            repository.engine,
            {
                "project_id": project_id,
                "current_stage": "drafting",
                "stages_json": stages_payload,
                "incremental_checks_json": incremental_checks,
            },
            expected_revision=1,
        )
    assert exc_info.value.status == 409
    assert exc_info.value.code == "REVISION_CONFLICT"

    # 4. 删除工作流
    del_ok = delete_workflow(repository.engine, project_id)
    assert del_ok is True
    assert read_workflow(repository.engine, project_id) is None


def test_job_persistence_lifecycle_and_progress_update(ensure_mysql):
    _upgrade()
    repository = create_app().state.service.repository

    job_id = f"job-{uuid4().hex}"
    project_id = f"proj-job-{uuid4().hex[:8]}"

    job_data = {
        "id": job_id,
        "job_type": "generate_chapter",
        "project_id": project_id,
        "status": "pending",
        "progress": 0,
        "step_name": "context_building",
        "created_by": "user-writer-01",
    }

    # 1. 创建异步任务
    save_job(repository.engine, job_data)

    job = read_job(repository.engine, job_id)
    assert job is not None
    assert job["id"] == job_id
    assert job["job_type"] == "generate_chapter"
    assert job["project_id"] == project_id
    assert job["status"] == "pending"
    assert job["progress"] == 0
    assert job["step_name"] == "context_building"
    assert job["error_json"] is None
    assert job["result_json"] is None

    # 2. 更新进度为 45% (running)
    upd_ok = update_job_progress(
        repository.engine,
        job_id,
        progress=45,
        status="running",
        step_name="model_inference",
    )
    assert upd_ok is True

    job_running = read_job(repository.engine, job_id)
    assert job_running["progress"] == 45
    assert job_running["status"] == "running"
    assert job_running["step_name"] == "model_inference"

    # 3. 更新进度为 100% 成功完成 (completed)
    result_data = {
        "chapter_id": "ch-tech-01",
        "token_usage": {"prompt": 1200, "completion": 850},
        "fingerprint": "fp-abc-123",
    }
    upd_ok = update_job_progress(
        repository.engine,
        job_id,
        progress=100,
        status="completed",
        step_name="saved_and_indexed",
        result_json=result_data,
    )
    assert upd_ok is True

    job_completed = read_job(repository.engine, job_id)
    assert job_completed["progress"] == 100
    assert job_completed["status"] == "completed"
    assert job_completed["step_name"] == "saved_and_indexed"
    assert job_completed["result_json"]["chapter_id"] == "ch-tech-01"

    # 4. 创建第二个任务并测试失败状态流转与 error_json 记录
    job_failed_id = f"job-{uuid4().hex}"
    save_job(repository.engine, {
        "id": job_failed_id,
        "job_type": "compliance_check",
        "project_id": project_id,
        "status": "running",
        "progress": 20,
        "step_name": "parsing_tender_rules",
        "created_by": "user-writer-01",
    })

    err_payload = {
        "code": "MODEL_TIMEOUT",
        "message": "Gateway timeout connecting to DeepSeek inference engine",
        "retryable": True,
    }
    update_job_progress(
        repository.engine,
        job_failed_id,
        progress=20,
        status="failed",
        step_name="aborted",
        error_json=err_payload,
    )

    job_failed = read_job(repository.engine, job_failed_id)
    assert job_failed["status"] == "failed"
    assert job_failed["error_json"]["code"] == "MODEL_TIMEOUT"

    # 5. 按项目查询任务列表与分页
    jobs, total = list_jobs_by_project(repository.engine, project_id)
    assert total == 2
    assert len(jobs) == 2

    # 按类型过滤
    jobs_gen, total_gen = list_jobs_by_project(repository.engine, project_id, job_type="generate_chapter")
    assert total_gen == 1
    assert jobs_gen[0]["id"] == job_id

    # 按状态过滤
    jobs_fail, total_fail = list_jobs_by_project(repository.engine, project_id, status="failed")
    assert total_fail == 1
    assert jobs_fail[0]["id"] == job_failed_id

    # 6. 删除任务
    assert delete_job(repository.engine, job_id) is True
    assert read_job(repository.engine, job_id) is None
    assert delete_job(repository.engine, job_failed_id) is True
    assert read_job(repository.engine, job_failed_id) is None


def test_memory_repository_polymorphism_workflow_and_jobs():
    # 纯内存模式多态纯洁性测试：未设置数据库连接串时，MemoryRepository 具备完全一致的接口与行为
    repo = MemoryRepository()
    pid = "mem-proj-wf-01"

    # 1. 工作流 CRUD 与乐观锁拦截
    repo.save_workflow({
        "project_id": pid,
        "current_stage": "parsing",
        "stages_json": {"parsing": {"status": "in_progress"}},
        "incremental_checks_json": [{"rule": "format", "passed": True}],
        "revision": 1,
    })

    wf = repo.read_workflow(pid)
    assert wf is not None
    assert wf["current_stage"] == "parsing"
    assert wf["revision"] == 1
    assert wf["stages_json"]["parsing"]["status"] == "in_progress"

    # 乐观并发锁拦截
    with pytest.raises(DomainError) as exc_info:
        repo.save_workflow(
            {"project_id": pid, "current_stage": "matrix"},
            expected_revision=99,
        )
    assert exc_info.value.status == 409
    assert exc_info.value.code == "REVISION_CONFLICT"

    # 正确版本推进
    repo.save_workflow(
        {"project_id": pid, "current_stage": "matrix"},
        expected_revision=1,
    )
    wf_v2 = repo.read_workflow(pid)
    assert wf_v2["revision"] == 2
    assert wf_v2["current_stage"] == "matrix"

    assert repo.delete_workflow(pid) is True
    assert repo.read_workflow(pid) is None

    # 2. 异步任务 CRUD、进度更新与列表分页
    job_id = "mem-job-01"
    repo.save_job({
        "id": job_id,
        "job_type": "export_document",
        "project_id": pid,
        "status": "pending",
        "progress": 0,
        "created_by": "mem-user",
    })

    job = repo.read_job(job_id)
    assert job is not None
    assert job["status"] == "pending"
    assert job["progress"] == 0

    upd_ok = repo.update_job_progress(
        job_id,
        progress=80,
        status="running",
        step_name="rendering_docx",
    )
    assert upd_ok is True

    job_upd = repo.read_job(job_id)
    assert job_upd["progress"] == 80
    assert job_upd["status"] == "running"
    assert job_upd["step_name"] == "rendering_docx"

    jobs, total = repo.list_jobs_by_project(pid, job_type="export_document")
    assert total == 1
    assert jobs[0]["id"] == job_id

    assert repo.delete_job(job_id) is True
    assert repo.read_job(job_id) is None
