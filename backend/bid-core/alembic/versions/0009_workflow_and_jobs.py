# 为什么有这个文件：把工作流状态（demo_workflow）与异步任务（demo_job）写成 MySQL 表。
# 它解决什么问题：项目编制六阶段推进、增量复查队列及长耗时异步任务跨进程持久化共享、断点恢复与进度状态流转。

"""workflow and async jobs aggregate

Revision ID: 0009_workflow_and_jobs
Revises: 0008_library_and_sla
Create Date: 2026-10-21

"""

from alembic import op

revision = "0009_workflow_and_jobs"
down_revision = "0008_library_and_sla"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE demo_workflow (
          project_id VARCHAR(120) NOT NULL,
          current_stage VARCHAR(50) NOT NULL,
          stages_json JSON NOT NULL,
          incremental_checks_json JSON NOT NULL,
          revision INT NOT NULL DEFAULT 1,
          updated_at DATETIME(6) NOT NULL,
          PRIMARY KEY (project_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
        """
    )
    op.execute(
        """
        CREATE TABLE demo_job (
          id VARCHAR(120) NOT NULL,
          job_type VARCHAR(50) NOT NULL,
          project_id VARCHAR(120) NOT NULL,
          status VARCHAR(50) NOT NULL,
          progress INT NOT NULL DEFAULT 0,
          step_name VARCHAR(100) NULL,
          error_json JSON NULL,
          result_json JSON NULL,
          created_by VARCHAR(120) NOT NULL,
          created_at DATETIME(6) NOT NULL,
          updated_at DATETIME(6) NOT NULL,
          PRIMARY KEY (id),
          KEY idx_job_project (project_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS demo_job")
    op.execute("DROP TABLE IF EXISTS demo_workflow")
