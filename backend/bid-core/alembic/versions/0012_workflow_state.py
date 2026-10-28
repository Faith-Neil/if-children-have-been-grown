# 为什么有这个文件：为仍只在进程内存里的业务状态建通用条目表（Wave 11/12，ISSUE-040、ISSUE-041）。
# 它解决什么问题：项目工作流、账号、资料库、SLA 模板、任务、审计、RAGFlow 配置与服务存储按“范围 + 条目”保存，
# 每条带 rev 做乐观锁，重启和多进程下不丢失、不静默覆盖。

"""generic state entries (workflow, accounts, library, jobs, audit, service stores)

Revision ID: 0012_workflow_state
Revises: 0011_bid_project_alignment
Create Date: 2026-10-28

"""

from alembic import op

revision = "0012_workflow_state"
down_revision = "0011_bid_project_alignment"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE demo_state_entry (
          scope VARCHAR(40) NOT NULL,
          entry_id VARCHAR(190) NOT NULL,
          rev INT NOT NULL,
          body LONGTEXT NOT NULL,
          updated_at DATETIME(6) NOT NULL,
          PRIMARY KEY (scope, entry_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS demo_state_entry")
