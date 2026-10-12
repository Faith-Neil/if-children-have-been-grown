# 为什么有这个文件：把项目和项目分工写成 MySQL 表。
# 它解决什么问题：已提交的项目要在另一个进程里仍能看见；章节和其他聚合不进这两张表。

"""demo project aggregate

Revision ID: 0004_demo_project
Revises: 0003_chapter_lease
Create Date: 2026-10-12

"""

from alembic import op

revision = "0004_demo_project"
down_revision = "0003_chapter_lease"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE demo_project (
          id VARCHAR(120) NOT NULL,
          name VARCHAR(300) NOT NULL,
          company_id VARCHAR(120) NOT NULL,
          revision INT NOT NULL,
          tender_number VARCHAR(100) NOT NULL,
          deadline VARCHAR(50) NOT NULL,
          is_sensitive TINYINT(1) NOT NULL,
          PRIMARY KEY (id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
        """
    )
    op.execute(
        """
        CREATE TABLE demo_project_team (
          project_id VARCHAR(120) NOT NULL,
          team_json JSON NOT NULL,
          PRIMARY KEY (project_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS demo_project_team")
    op.execute("DROP TABLE IF EXISTS demo_project")
