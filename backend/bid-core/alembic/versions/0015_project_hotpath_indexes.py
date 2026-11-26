# 为什么有这个文件：为高频项目列表与会话热路径补齐项目访问时间、列表状态缓存和 MySQL 二级索引（ISSUE-055）。
# 它解决什么问题：项目列表按公司、状态与访问/更新时间排序筛选时不再全表扫描；单项目与章节按外键读取有明确索引支撑。

"""project hot-path columns and indexes

Revision ID: 0015_project_hotpath_indexes
Revises: 0014_chapter_version_meta
Create Date: 2026-11-12

"""

from alembic import op

revision = "0015_project_hotpath_indexes"
down_revision = "0014_chapter_version_meta"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE demo_project
          ADD COLUMN last_accessed_at DATETIME(6) NULL,
          ADD COLUMN status VARCHAR(30) NOT NULL DEFAULT 'preparing'
        """
    )
    op.execute("CREATE INDEX idx_demo_project_company ON demo_project (company_id)")
    op.execute("CREATE INDEX idx_demo_project_last_accessed ON demo_project (last_accessed_at)")
    op.execute("CREATE INDEX idx_demo_project_updated ON demo_project (updated_at)")
    op.execute("CREATE INDEX idx_demo_project_status ON demo_project (status)")
    op.execute("CREATE INDEX idx_demo_state_entry_scope_updated ON demo_state_entry (scope, updated_at)")


def downgrade() -> None:
    op.execute("DROP INDEX idx_demo_state_entry_scope_updated ON demo_state_entry")
    op.execute("DROP INDEX idx_demo_project_status ON demo_project")
    op.execute("DROP INDEX idx_demo_project_updated ON demo_project")
    op.execute("DROP INDEX idx_demo_project_last_accessed ON demo_project")
    op.execute("DROP INDEX idx_demo_project_company ON demo_project")
    op.execute("ALTER TABLE demo_project DROP COLUMN status, DROP COLUMN last_accessed_at")
