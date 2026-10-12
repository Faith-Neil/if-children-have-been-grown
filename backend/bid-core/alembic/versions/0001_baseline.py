# 为什么有这个文件：给后续迁移一个空的起点。
# 它解决什么问题：先记下 Alembic 版本，本卡还不创建业务表。

"""empty baseline

Revision ID: 0001_baseline
Revises:
Create Date: 2026-10-12

"""

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
