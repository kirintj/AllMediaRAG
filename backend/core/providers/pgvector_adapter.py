"""PostgreSQL + pgvector 向量存储适配器

实现 VectorStoreProvider 抽象接口，使用同步 SQLAlchemy engine。
调用方 rag_engine.py 已用 asyncio.to_thread 包裹，保持同步接口语义。
"""

import uuid
import logging

from sqlalchemy import create_engine, text, func
from sqlalchemy.orm import sessionmaker, Session

from core.providers.base import VectorStoreProvider
from core.db.models import DocumentModel, DocumentChunkModel

logger = logging.getLogger(__name__)


class PgVectorStoreAdapter(VectorStoreProvider):
    """PostgreSQL + pgvector 向量存储适配器

    实现 VectorStoreProvider 的全部 7 个抽象方法。
    使用同步 SQLAlchemy engine，兼容现有调用链。
    """

    def __init__(self, database_url: str = "", **kwargs):
        """初始化 pgvector 适配器

        Args:
            database_url: PostgreSQL 连接 URL
            **kwargs: 忽略其他参数（工厂模式传入时可能包含 persist_dir 等）
        """
        if not database_url:
            raise ValueError("database_url is required for PgVectorStoreAdapter")

        self._engine = create_engine(
            database_url,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=1800,
            echo=False,
        )
        self._session_factory = sessionmaker(bind=self._engine, expire_on_commit=False)
        logger.info("PgVectorStoreAdapter initialized: %s", database_url.split("@")[-1] if "@" in database_url else database_url)

    def _get_session(self) -> Session:
        """获取数据库会话"""
        return self._session_factory()

    def add_documents(self, texts: list[str], embeddings: list, metadatas: list) -> None:
        """添加文档到向量库

        Args:
            texts: 文档文本列表
            embeddings: 向量列表
            metadatas: 元数据列表（每个 dict 包含 source, section, chunk_index）
        """
        if not texts:
            return

        session = self._get_session()
        try:
            # 批量插入，每批 500 条
            batch_size = 500
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                batch_embeddings = embeddings[i:i + batch_size]
                batch_metadatas = metadatas[i:i + batch_size]

                records = []
                for text_content, embedding, metadata in zip(batch_texts, batch_embeddings, batch_metadatas):
                    source = metadata.get("source", "")
                    # 查找或创建 document 记录
                    doc = session.query(DocumentModel).filter_by(source=source).first()
                    if doc is None:
                        doc = DocumentModel(
                            source=source,
                            file_hash="",
                            chunk_count=0,
                        )
                        session.add(doc)
                        session.flush()

                    records.append(DocumentChunkModel(
                        id=uuid.uuid4(),
                        document_id=doc.id,
                        source=source,
                        section=metadata.get("section", ""),
                        chunk_index=metadata.get("chunk_index", 0),
                        text=text_content,
                        embedding=embedding,
                    ))

                session.bulk_save_objects(records)
                session.commit()
                logger.debug("Inserted %d chunks", len(records))

        except Exception as e:
            session.rollback()
            logger.exception("Failed to add documents")
            raise
        finally:
            session.close()

    def query(self, embedding: list[float], top_k: int) -> dict:
        """查询相似文档

        Args:
            embedding: 查询向量
            top_k: 返回数量

        Returns:
            {"documents": [...], "metadatas": [...], "distances": [...]}
        """
        session = self._get_session()
        try:
            # 使用原生 SQL 进行余弦距离查询
            # cosine_distance = 1 - cosine_similarity
            embedding_str = str(embedding)
            sql = text("""
                SELECT text, source, section, chunk_index,
                       embedding <=> :embedding::vector AS distance
                FROM document_chunks
                ORDER BY embedding <=> :embedding::vector
                LIMIT :top_k
            """)

            results = session.execute(sql, {
                "embedding": embedding_str,
                "top_k": top_k,
            }).fetchall()

            documents = []
            metadatas = []
            distances = []

            for row in results:
                documents.append(row.text)
                metadatas.append({
                    "source": row.source,
                    "section": row.section,
                    "chunk_index": row.chunk_index,
                })
                distances.append(row.distance)

            return {
                "documents": documents,
                "metadatas": metadatas,
                "distances": distances,
            }

        except Exception as e:
            logger.exception("Failed to query documents")
            raise
        finally:
            session.close()

    def delete_by_source(self, source: str) -> None:
        """按来源删除文档

        Args:
            source: 文档来源标识（文件名）
        """
        session = self._get_session()
        try:
            # 删除 chunks
            deleted_count = (
                session.query(DocumentChunkModel)
                .filter(DocumentChunkModel.source == source)
                .delete()
            )

            # 更新或删除 document 记录
            doc = session.query(DocumentModel).filter_by(source=source).first()
            if doc:
                remaining = (
                    session.query(func.count(DocumentChunkModel.id))
                    .filter(DocumentChunkModel.document_id == doc.id)
                    .scalar()
                )
                if remaining == 0:
                    session.delete(doc)
                else:
                    doc.chunk_count = remaining

            session.commit()
            logger.info("Deleted %d chunks for source: %s", deleted_count, source)

        except Exception as e:
            session.rollback()
            logger.exception("Failed to delete by source: %s", source)
            raise
        finally:
            session.close()

    def get_all_sources(self) -> list[str]:
        """获取所有文档来源

        Returns:
            去重后的来源列表
        """
        session = self._get_session()
        try:
            sources = (
                session.query(DocumentChunkModel.source)
                .distinct()
                .all()
            )
            return [s[0] for s in sources]
        except Exception as e:
            logger.exception("Failed to get all sources")
            raise
        finally:
            session.close()

    def get_document_count(self) -> int:
        """获取文档总数

        Returns:
            chunk 数量
        """
        session = self._get_session()
        try:
            return session.query(func.count(DocumentChunkModel.id)).scalar()
        except Exception as e:
            logger.exception("Failed to get document count")
            raise
        finally:
            session.close()

    def delete_all(self) -> None:
        """清空所有文档"""
        session = self._get_session()
        try:
            session.execute(text("TRUNCATE document_chunks, documents CASCADE"))
            session.commit()
            logger.info("All documents deleted")
        except Exception as e:
            session.rollback()
            logger.exception("Failed to delete all documents")
            raise
        finally:
            session.close()

    def get_all_documents(self) -> list[dict]:
        """获取所有文档（用于重建 BM25 索引）

        Returns:
            [{"id": str, "text": str, "metadata": dict}, ...]
        """
        session = self._get_session()
        try:
            chunks = session.query(DocumentChunkModel).all()
            docs = []
            for chunk in chunks:
                docs.append({
                    "id": str(chunk.id),
                    "text": chunk.text,
                    "metadata": {
                        "source": chunk.source,
                        "section": chunk.section,
                        "chunk_index": chunk.chunk_index,
                    },
                })
            return docs
        except Exception as e:
            logger.exception("Failed to get all documents")
            raise
        finally:
            session.close()

    def close(self) -> None:
        """关闭数据库连接池"""
        if self._engine:
            self._engine.dispose()
            logger.info("PgVectorStoreAdapter closed")

    def get_source_details(self) -> list[dict]:
        """获取每个来源的 chunk 数量

        Returns:
            [{"source": str, "chunks": int}, ...]
        """
        session = self._get_session()
        try:
            rows = (
                session.query(
                    DocumentChunkModel.source,
                    func.count(DocumentChunkModel.id).label("chunks")
                )
                .group_by(DocumentChunkModel.source)
                .all()
            )
            return [{"source": r.source, "chunks": r.chunks} for r in rows]
        except Exception as e:
            logger.exception("Failed to get source details")
            raise
        finally:
            session.close()
