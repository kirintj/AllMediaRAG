"""已废弃：document_chunks 表已迁移至 Elasticsearch

Revision ID: 002_create_tables
Revises: 001_enable_pgvector
Create Date: 2026-06-11

注：此迁移保留为空操作以维持迁移链完整性。
document_chunks 表不再使用，向量存储在 Elasticsearch 中。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002_create_tables"
down_revision: Union[str, None] = "001_enable_pgvector"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # document_chunks 表已废弃，数据迁移至 Elasticsearch
    pass


def downgrade() -> None:
    pass
