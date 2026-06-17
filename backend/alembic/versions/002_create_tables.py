"""创建 documents 和 document_chunks 表

Revision ID: 002_create_tables
Revises: 001_enable_pgvector
Create Date: 2026-06-11
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector

revision: str = "002_create_tables"
down_revision: Union[str, None] = "001_enable_pgvector"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建 documents 表
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

    # 创建 document_chunks 表
    op.create_table(
        "document_chunks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, comment="所属文件 ID"),
        sa.Column("source", sa.String(500), nullable=False, comment="文件名（冗余）"),
        sa.Column("section", sa.String(500), nullable=False, server_default="", comment="章节标题"),
        sa.Column("chunk_index", sa.Integer, nullable=False, server_default="0", comment="chunk 序号"),
        sa.Column("text", sa.Text, nullable=False, comment="chunk 文本"),
        sa.Column("embedding", Vector(1024), nullable=False, comment="BGE-M3 向量"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), comment="创建时间"),
        comment="文档 chunk 表",
    )
    op.create_index("idx_chunks_document_id", "document_chunks", ["document_id"])
    op.create_index("idx_chunks_source", "document_chunks", ["source"])

    # 创建 HNSW 向量索引（余弦距离）
    op.execute(
        "CREATE INDEX idx_chunks_embedding_cosine ON document_chunks "
        "USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)"
    )


def downgrade() -> None:
    op.drop_table("document_chunks")
    op.drop_table("documents")
