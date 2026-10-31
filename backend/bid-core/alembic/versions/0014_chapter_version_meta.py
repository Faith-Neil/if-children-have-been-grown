# 为什么有这个文件：章节版本增加元数据列（APP-M2-T161 段落键与逐段来源）。
# 它解决什么问题：版本表原来只存正文，写入方式（人工/对话助手/章节循环/系统生成）、粘贴识别记录与段落键在 MySQL 重新加载后全部丢失；
# 现在这些放进 meta（JSON），读回时合并到版本记录。旧行 meta 为空，段落键按版本链补算，结果与当初一致。

"""chapter version meta

Revision ID: 0014_chapter_version_meta
Revises: 0013_model_fallback
Create Date: 2026-10-30

"""

from alembic import op

revision = "0014_chapter_version_meta"
down_revision = "0013_model_fallback"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE demo_chapter_version ADD COLUMN meta JSON NULL")


def downgrade() -> None:
    op.execute("ALTER TABLE demo_chapter_version DROP COLUMN meta")
