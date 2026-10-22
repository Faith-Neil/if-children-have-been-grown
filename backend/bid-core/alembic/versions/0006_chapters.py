# 为什么有这个文件：把章节聚合和章节版本历史写成 MySQL 表。
# 它解决什么问题：章节正文和版本历史要在多个进程间持久化共享，支持版本乐观锁控制。

"""chapters and versions aggregate

Revision ID: 0006_chapters
Revises: 0005_model_config
Create Date: 2026-10-21

"""

from alembic import op

revision = "0006_chapters"
down_revision = "0005_model_config"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE demo_chapter (
          id VARCHAR(120) NOT NULL,
          project_id VARCHAR(120) NOT NULL,
          volume VARCHAR(30) NOT NULL,
          title VARCHAR(300) NOT NULL,
          content LONGTEXT NOT NULL,
          revision INT NOT NULL DEFAULT 1,
          assignee_id VARCHAR(120) NULL,
          updated_at DATETIME(6) NOT NULL,
          PRIMARY KEY (id),
          KEY idx_demo_chapter_project (project_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
        """
    )
    op.execute(
        """
        CREATE TABLE demo_chapter_version (
          id VARCHAR(120) NOT NULL,
          chapter_id VARCHAR(120) NOT NULL,
          version_number INT NOT NULL,
          content LONGTEXT NOT NULL,
          created_by VARCHAR(120) NOT NULL,
          created_at DATETIME(6) NOT NULL,
          PRIMARY KEY (id),
          KEY idx_demo_chapter_version_chapter (chapter_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS demo_chapter_version")
    op.execute("DROP TABLE IF EXISTS demo_chapter")
