# 为什么有这个文件：把 chapter_lease 租约表对齐字典 v1.9 的 edit_lock 结构。
# 它解决什么问题：对齐大纲节点、持锁人、心跳、取得时间、接管历史、释放原因和 A/C 组审计列，保留历史锁行不删除。

"""align chapter_lease with edit_lock data dictionary

Revision ID: 0010_edit_lock_alignment
Revises: 0009_workflow_and_jobs
Create Date: 2026-10-22

"""

from alembic import op

revision = "0010_edit_lock_alignment"
down_revision = "0009_workflow_and_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 对齐字典 edit_lock：增加审计列、公司隔离、心跳与释放枚举，保留已有租约行
    op.execute(
        """
        ALTER TABLE chapter_lease
          ADD COLUMN id VARCHAR(120) NULL,
          ADD COLUMN company_id VARCHAR(120) NULL,
          ADD COLUMN acquired_at DATETIME(6) NULL,
          ADD COLUMN heartbeat_at DATETIME(6) NULL,
          ADD COLUMN lock_reason VARCHAR(50) NULL,
          ADD COLUMN taken_over_from_user_id VARCHAR(120) NULL,
          ADD COLUMN takeover_reason VARCHAR(300) NULL,
          ADD COLUMN released_at DATETIME(6) NULL,
          ADD COLUMN release_reason VARCHAR(50) NULL,
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
        ALTER TABLE chapter_lease
          DROP COLUMN is_deleted,
          DROP COLUMN record_version,
          DROP COLUMN updated_at,
          DROP COLUMN updated_by,
          DROP COLUMN created_at,
          DROP COLUMN created_by,
          DROP COLUMN release_reason,
          DROP COLUMN released_at,
          DROP COLUMN takeover_reason,
          DROP COLUMN taken_over_from_user_id,
          DROP COLUMN lock_reason,
          DROP COLUMN heartbeat_at,
          DROP COLUMN acquired_at,
          DROP COLUMN company_id,
          DROP COLUMN id
        """
    )
