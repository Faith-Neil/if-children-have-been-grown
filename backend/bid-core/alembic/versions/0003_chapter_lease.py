# 为什么有这个文件：把编辑租约写成 MySQL 表。
# 它解决什么问题：续期和过期接管要在另一个进程里仍然成立。章节表还没有，所以这里不加外键。

"""chapter edit leases

Revision ID: 0003_chapter_lease
Revises: 0002_sessions_receipts
Create Date: 2026-10-12

"""

from alembic import op

revision = "0003_chapter_lease"
down_revision = "0002_sessions_receipts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE chapter_lease (
          chapter_id VARCHAR(120) NOT NULL,
          token VARCHAR(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,
          owner_id VARCHAR(120) NOT NULL,
          session_token VARCHAR(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,
          expires_at DATETIME(6) NOT NULL,
          PRIMARY KEY (chapter_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS chapter_lease")
