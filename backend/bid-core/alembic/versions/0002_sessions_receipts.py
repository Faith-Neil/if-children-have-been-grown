# 为什么有这个文件：把登录会话和幂等回执写成 MySQL 表。
# 它解决什么问题：多个进程能读到同一份回执和会话，进程重启后未过期数据还在。

"""sessions and idempotency receipts

Revision ID: 0002_sessions_receipts
Revises: 0001_baseline
Create Date: 2026-10-12

"""

from alembic import op

revision = "0002_sessions_receipts"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE idempotency_receipt (
          scope_id VARCHAR(160) NOT NULL,
          user_id VARCHAR(120) NOT NULL,
          idempotency_key VARCHAR(120) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,
          fingerprint CHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,
          result_json JSON NOT NULL,
          created_at DATETIME(6) NOT NULL,
          expires_at DATETIME(6) NOT NULL,
          PRIMARY KEY (scope_id, user_id, idempotency_key),
          KEY idx_idempotency_expires (expires_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
        """
    )
    op.execute(
        """
        CREATE TABLE user_session (
          token VARCHAR(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,
          user_id VARCHAR(120) NOT NULL,
          created_at DATETIME(6) NOT NULL,
          PRIMARY KEY (token),
          KEY idx_session_user (user_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS user_session")
    op.execute("DROP TABLE IF EXISTS idempotency_receipt")
