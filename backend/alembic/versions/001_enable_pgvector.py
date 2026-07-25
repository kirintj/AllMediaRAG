"""创建 documents 表

Revision ID: 001_enable_pgvector
Revises:
Create Date: 2026-06-11

注：原 pgvector 迁移已废弃，向量存储已迁移至 Elasticsearch。
此迁移仅创建 documents 元数据表。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "001_enable_pgvector"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("source", sa.String(500), nullable=False, unique=True, comment="文件名"),
        sa.Column("file_hash", sa.String(64), nullable=False, comment="SHA-256 文件哈希"),
        sa.Column("chunk_count", sa.Integer, nullable=False, server_default="0", comment="chunk 数量"),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), comment="索引时间"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), comment="更新时间"),
        comment="文件级元数据表",
    )
    op.create_index("idx_documents_file_hash", "documents", ["file_hash"])


def downgrade() -> None:
    op.drop_table("documents")
