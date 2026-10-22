# 为什么有这个文件：把资料与承诺聚合（demo_library_item, demo_sla_template, demo_library_revision）写成 MySQL 表。
# 它解决什么问题：企业资质、人员、业绩等知识库资料、SLA服务承诺模板及不可变修订历史跨进程持久化共享与并发乐观锁控制。

"""library and sla aggregate

Revision ID: 0008_library_and_sla
Revises: 0007_checks_and_exports
Create Date: 2026-10-21

"""

from alembic import op

revision = "0008_library_and_sla"
down_revision = "0007_checks_and_exports"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE demo_library_item (
          id VARCHAR(120) NOT NULL,
          company_id VARCHAR(120) NOT NULL,
          category VARCHAR(50) NOT NULL,
          name VARCHAR(300) NOT NULL,
          status VARCHAR(50) NOT NULL,
          is_starred TINYINT(1) NOT NULL DEFAULT 0,
          can_insert TINYINT(1) NOT NULL DEFAULT 1,
          is_sensitive TINYINT(1) NOT NULL DEFAULT 0,
          payload_json JSON NOT NULL,
          revision INT NOT NULL DEFAULT 1,
          created_at DATETIME(6) NOT NULL,
          updated_at DATETIME(6) NOT NULL,
          PRIMARY KEY (id),
          KEY idx_lib_company (company_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
        """
    )
    op.execute(
        """
        CREATE TABLE demo_sla_template (
          id VARCHAR(120) NOT NULL,
          company_id VARCHAR(120) NOT NULL,
          level VARCHAR(20) NOT NULL,
          name VARCHAR(200) NOT NULL,
          rules_json JSON NOT NULL,
          revision INT NOT NULL DEFAULT 1,
          created_at DATETIME(6) NOT NULL,
          updated_at DATETIME(6) NOT NULL,
          PRIMARY KEY (id),
          KEY idx_sla_company (company_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
        """
    )
    op.execute(
        """
        CREATE TABLE demo_library_revision (
          id VARCHAR(120) NOT NULL,
          item_id VARCHAR(120) NOT NULL,
          version_number INT NOT NULL,
          payload_json JSON NOT NULL,
          changed_by VARCHAR(120) NOT NULL,
          change_reason VARCHAR(500) NULL,
          created_at DATETIME(6) NOT NULL,
          PRIMARY KEY (id),
          KEY idx_lib_rev_item (item_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS demo_library_revision")
    op.execute("DROP TABLE IF EXISTS demo_sla_template")
    op.execute("DROP TABLE IF EXISTS demo_library_item")
