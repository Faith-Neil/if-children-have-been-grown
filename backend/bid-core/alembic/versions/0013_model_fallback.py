# 为什么有这个文件：模型配置增加备用模型（PRD v1.8 §6.4、§6.5；字典 llm_model.fallback_model_id；APP-M2-T177）。
# 它解决什么问题：主模型超时、连接失败、5xx 或限流时改用同公司的备用模型；本地主模型只能配本地备用，保存时核对。

"""model config fallback

Revision ID: 0013_model_fallback
Revises: 0012_workflow_state
Create Date: 2026-10-30

"""

from alembic import op

revision = "0013_model_fallback"
down_revision = "0012_workflow_state"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE demo_model_config ADD COLUMN fallback_config_id VARCHAR(120) NULL")


def downgrade() -> None:
    op.execute("ALTER TABLE demo_model_config DROP COLUMN fallback_config_id")
