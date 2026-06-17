"""ChromaDB → PostgreSQL 数据迁移脚本

一次性迁移脚本，将 ChromaDB 中的向量数据迁移到 PostgreSQL + pgvector。

使用方法:
    cd backend
    python scripts/migrate_chroma_to_pg.py [--batch-size 500]

注意事项:
    - 迁移前请确保 PostgreSQL 已启动且表已创建（运行 Alembic 迁移）
    - 迁移期间建议停止 FastAPI 服务
    - 迁移完成后切换 VECTOR_STORE_PROVIDER=pgvector
"""

import os
import sys
import uuid
import argparse
import logging
from pathlib import Path
from collections import defaultdict

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine, func, text
from sqlalchemy.orm import sessionmaker

from core.config import config
from core.vector_store import VectorStore
from core.db.models import DocumentModel, DocumentChunkModel
from core.db.base import Base

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("migrate_chroma_to_pg")


def get_chroma_data(chroma_dir: str) -> tuple[list[dict], list]:
    """从 ChromaDB 读取所有文档和 embedding

    Returns:
        (documents, embeddings) - 文档列表和对应的 embedding 列表
    """
    logger.info("Reading from ChromaDB: %s", chroma_dir)
    store = VectorStore(chroma_dir)

    # 获取所有文档（含 embedding）
    results = store.collection.get(include=["documents", "metadatas", "embeddings"])

    docs = []
    embeddings = []

    for i, doc_id in enumerate(results["ids"]):
        text_content = results["documents"][i] if results["documents"] else ""
        metadata = results["metadatas"][i] if results["metadatas"] else {}
        embedding = results["embeddings"][i] if results["embeddings"] else None

        if text_content and embedding:
            docs.append({
                "id": doc_id,
                "text": text_content,
                "metadata": metadata or {},
            })
            embeddings.append(embedding)

    logger.info("Read %d documents from ChromaDB", len(docs))
    store.close()
    return docs, embeddings


def migrate_to_pg(
    docs: list[dict],
    embeddings: list,
    database_url: str,
    batch_size: int = 500,
):
    """将数据迁移到 PostgreSQL

    Args:
        docs: ChromaDB 文档列表
        embeddings: 对应的 embedding 列表
        database_url: PostgreSQL 连接 URL
        batch_size: 每批写入数量
    """
    logger.info("Connecting to PostgreSQL: %s", database_url.split("@")[-1] if "@" in database_url else database_url)
    engine = create_engine(database_url, pool_size=5, max_overflow=10)
    Session = sessionmaker(bind=engine)

    # 按 source 分组
    source_groups = defaultdict(list)
    for i, doc in enumerate(docs):
        source = doc["metadata"].get("source", "unknown")
        source_groups[source].append((doc, embeddings[i]))

    logger.info("Found %d unique sources to migrate", len(source_groups))

    session = Session()
    try:
        total_chunks = 0

        for source, items in source_groups.items():
            # 创建或获取 document 记录
            doc_record = session.query(DocumentModel).filter_by(source=source).first()
            if doc_record is None:
                doc_record = DocumentModel(
                    source=source,
                    file_hash="",  # 迁移时无法获取原始文件 hash
                    chunk_count=len(items),
                )
                session.add(doc_record)
                session.flush()
                logger.info("Created document record: %s", source)
            else:
                doc_record.chunk_count = len(items)
                logger.info("Updated document record: %s", source)

            # 批量插入 chunks
            for batch_start in range(0, len(items), batch_size):
                batch_items = items[batch_start:batch_start + batch_size]
                records = []

                for doc, embedding in batch_items:
                    records.append(DocumentChunkModel(
                        id=uuid.uuid4(),
                        document_id=doc_record.id,
                        source=source,
                        section=doc["metadata"].get("section", ""),
                        chunk_index=doc["metadata"].get("chunk_index", 0),
                        text=doc["text"],
                        embedding=embedding,
                    ))

                session.bulk_save_objects(records)
                session.commit()
                total_chunks += len(records)
                logger.info("  Migrated %d/%d chunks for source: %s",
                           batch_start + len(batch_items), len(items), source)

        logger.info("Migration complete! Total chunks migrated: %d", total_chunks)

        # 验证
        pg_count = session.query(func.count(DocumentChunkModel.id)).scalar()
        logger.info("Verification: PostgreSQL has %d chunks", pg_count)

    except Exception as e:
        session.rollback()
        logger.exception("Migration failed")
        raise
    finally:
        session.close()
        engine.dispose()


def main():
    parser = argparse.ArgumentParser(description="Migrate ChromaDB data to PostgreSQL + pgvector")
    parser.add_argument("--batch-size", type=int, default=500, help="Batch size for inserts (default: 500)")
    parser.add_argument("--chroma-dir", type=str, default="", help="ChromaDB directory (default: from config)")
    parser.add_argument("--database-url", type=str, default="", help="PostgreSQL URL (default: from config)")
    args = parser.parse_args()

    chroma_dir = args.chroma_dir or config.CHROMA_PERSIST_DIR
    database_url = args.database_url or config.database_url

    if not os.path.exists(chroma_dir):
        logger.error("ChromaDB directory not found: %s", chroma_dir)
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("ChromaDB → PostgreSQL Migration")
    logger.info("=" * 60)
    logger.info("Source (ChromaDB): %s", chroma_dir)
    logger.info("Target (PostgreSQL): %s", database_url.split("@")[-1] if "@" in database_url else database_url)
    logger.info("Batch size: %d", args.batch_size)
    logger.info("=" * 60)

    # 读取 ChromaDB 数据
    docs, embeddings = get_chroma_data(chroma_dir)

    if not docs:
        logger.warning("No documents found in ChromaDB. Nothing to migrate.")
        return

    # 迁移到 PostgreSQL
    migrate_to_pg(docs, embeddings, database_url, args.batch_size)

    logger.info("")
    logger.info("Migration completed successfully!")
    logger.info("Next steps:")
    logger.info("  1. Set VECTOR_STORE_PROVIDER=pgvector in .env")
    logger.info("  2. Restart the backend service")
    logger.info("  3. Verify the application works correctly")


if __name__ == "__main__":
    main()
