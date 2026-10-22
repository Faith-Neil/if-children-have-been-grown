# 为什么有这个文件：把检查聚合（demo_check）与导出聚合（demo_export）写成 MySQL 表。
# 它解决什么问题：合规检查结果与导出文档快照跨进程持久化共享，支持状态流转追踪与历史分页查询。

"""checks and exports aggregate

Revision ID: 0007_checks_and_exports
Revises: 0006_chapters
Create Date: 2026-10-21

"""

from alembic import op

revision = "0007_checks_and_exports"
down_revision = "0006_chapters"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE demo_check (
          id VARCHAR(120) NOT NULL,
          project_id VARCHAR(120) NOT NULL,
          volume_id VARCHAR(120) NULL,
          status VARCHAR(50) NOT NULL,
          blocking_count INT NOT NULL DEFAULT 0,
          warning_count INT NOT NULL DEFAULT 0,
          issues_json JSON NOT NULL,
          created_at DATETIME(6) NOT NULL,
          updated_at DATETIME(6) NOT NULL,
          PRIMARY KEY (id),
          KEY idx_check_project (project_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
        """
    )
    op.execute(
        """
        CREATE TABLE demo_export (
          id VARCHAR(120) NOT NULL,
          project_id VARCHAR(120) NOT NULL,
          export_type VARCHAR(50) NOT NULL,
          status VARCHAR(50) NOT NULL,
          format VARCHAR(20) NOT NULL,
          file_path VARCHAR(500) NULL,
          file_size BIGINT NULL,
          snapshot_json JSON NULL,
          created_by VARCHAR(120) NOT NULL,
          created_at DATETIME(6) NOT NULL,
          PRIMARY KEY (id),
          KEY idx_export_project (project_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS demo_export")
    op.execute("DROP TABLE IF EXISTS demo_check")
