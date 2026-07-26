"""添加对话收藏和分享字段

Revision ID: 003_conversation_enhancements
Revises: 002_create_tables
Create Date: 2026-07-26

新增字段：
- conversations.is_favorite: 布尔，是否收藏
- conversations.shared_token: 字符串，分享令牌（唯一索引）
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003_conversation_enhancements"
down_revision: Union[str, None] = "002_create_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("conversations", sa.Column("is_favorite", sa.Boolean(), server_default="false", nullable=False, comment="是否收藏"))
    op.add_column("conversations", sa.Column("shared_token", sa.String(64), nullable=True, comment="分享令牌"))
    op.create_index("idx_conversations_shared_token", "conversations", ["shared_token"], unique=True)


def downgrade() -> None:
    op.drop_index("idx_conversations_shared_token", table_name="conversations")
    op.drop_column("conversations", "shared_token")
    op.drop_column("conversations", "is_favorite")
