# 为什么有这个文件：把模型配置写成 MySQL 表。
# 它解决什么问题：模型配置要在另一个进程里仍能看见，API 密钥加密保存，版本号支持乐观锁。

"""model config aggregate

Revision ID: 0005_model_config
Revises: 0004_demo_project
Create Date: 2026-10-21

"""

from alembic import op

revision = "0005_model_config"
down_revision = "0004_demo_project"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE demo_model_config (
          id VARCHAR(120) NOT NULL,
          company_id VARCHAR(120) NOT NULL,
          name VARCHAR(300) NOT NULL,
          provider VARCHAR(100) NOT NULL,
          base_url VARCHAR(500) NOT NULL,
          model VARCHAR(200) NOT NULL,
          encrypted_api_key TEXT NULL,
          api_key_masked VARCHAR(200) NULL,
          is_local TINYINT(1) NOT NULL,
          allow_sensitive TINYINT(1) NOT NULL,
          stream_enabled TINYINT(1) NOT NULL,
          json_mode_enabled TINYINT(1) NOT NULL,
          revision INT NOT NULL,
          timeout_seconds FLOAT NOT NULL,
          max_tokens INT NOT NULL,
          PRIMARY KEY (id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
        """
    )
    op.execute(
        """
        CREATE TABLE demo_project_model_config (
          project_id VARCHAR(120) NOT NULL,
          model_config_id VARCHAR(120) NOT NULL,
          PRIMARY KEY (project_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS demo_project_model_config")
    op.execute("DROP TABLE IF EXISTS demo_model_config")
