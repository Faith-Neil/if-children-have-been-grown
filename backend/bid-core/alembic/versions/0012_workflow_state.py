# 为什么有这个文件：为章节循环/人工处理队列、分册定稿与交叉复核、兜底扫描结果建 MySQL 表（Wave 11）。
# 它解决什么问题：这些记录原先只在进程内存里，重启或多进程时会丢；按项目一行 JSON 保存，跨进程可见。

"""project workflow state (human queue, volume finalize and review, scan hits)

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
        CREATE TABLE demo_project_workflow_state (
          project_id VARCHAR(120) NOT NULL,
          state_json JSON NOT NULL,
          updated_at DATETIME(6) NOT NULL,
          PRIMARY KEY (project_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS demo_project_workflow_state")
