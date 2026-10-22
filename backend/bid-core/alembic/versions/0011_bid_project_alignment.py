# 为什么有这个文件：把 demo_project 项目表对齐字典 v1.9 的 bid_project 结构。
# 它解决什么问题：对齐标段类型、预算、截止时间戳、密级、行业、归档状态以及 A 组系统审计列，保留历史项目行不删除。

"""align demo_project with bid_project data dictionary

Revision ID: 0011_bid_project_alignment
Revises: 0010_edit_lock_alignment
Create Date: 2026-10-22

"""

from alembic import op

revision = "0011_bid_project_alignment"
down_revision = "0010_edit_lock_alignment"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 对齐字典 bid_project：增加标段类型、预算（分）、截止时间、密级、行业、归档状态与 A 组审计列，保留已有项目行
    op.execute(
        """
        ALTER TABLE demo_project
          ADD COLUMN tender_type VARCHAR(50) NULL DEFAULT 'comprehensive',
          ADD COLUMN budget_amount_cents BIGINT NULL,
          ADD COLUMN deadline_at DATETIME(6) NULL,
          ADD COLUMN security_level VARCHAR(50) NULL DEFAULT 'internal',
          ADD COLUMN industry VARCHAR(100) NULL DEFAULT 'it',
          ADD COLUMN is_archived TINYINT(1) NOT NULL DEFAULT 0,
          ADD COLUMN created_by VARCHAR(120) NULL,
          ADD COLUMN created_at DATETIME(6) NULL,
          ADD COLUMN updated_by VARCHAR(120) NULL,
          ADD COLUMN updated_at DATETIME(6) NULL,
          ADD COLUMN record_version INT NOT NULL DEFAULT 1,
          ADD COLUMN is_deleted TINYINT(1) NOT NULL DEFAULT 0
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE demo_project
          DROP COLUMN is_deleted,
          DROP COLUMN record_version,
          DROP COLUMN updated_at,
          DROP COLUMN updated_by,
          DROP COLUMN created_at,
          DROP COLUMN created_by,
          DROP COLUMN is_archived,
          DROP COLUMN industry,
          DROP COLUMN security_level,
          DROP COLUMN deadline_at,
          DROP COLUMN budget_amount_cents,
          DROP COLUMN tender_type
        """
    )
