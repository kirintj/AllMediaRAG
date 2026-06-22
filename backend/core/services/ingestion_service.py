import os
import uuid
import logging

from core.index_manager import IndexManager

logger = logging.getLogger(__name__)


class IngestionService:
    """文档摄入服务：负责文档的索引、删除与增量同步。"""

    def __init__(self, infra):
        self._infra = infra
        self._document_processor = infra.document_processor
        self._embedding_service = infra.embedding_service
        self._vector_store = infra.vector_store
        self._bm25_retriever = infra.bm25_retriever
        self._index_manager = infra.index_manager
        self._cache_manager = infra.cache_manager

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def ingest_document(self, file_path: str) -> int:
        """导入文档，返回 chunk 数量

        Args:
            file_path: 文档文件路径

        Returns:
            处理的 chunk 数量
        """
        source = os.path.basename(file_path)
        chunks, precomputed_embeddings = self._document_processor.process_file(file_path)

        if not chunks:
            return 0

        texts = [c["text"] for c in chunks]
        metadatas = [c["metadata"] for c in chunks]

        # 复用语义分块时的 embedding（均值池化），仅编码缺失部分
        embeddings: list[list[float]] = []
        missing_idx: list[int] = []
        for i, emb in enumerate(precomputed_embeddings):
            if emb is not None:
                embeddings.append(emb)
            else:
                embeddings.append([])  # 占位
                missing_idx.append(i)

        if missing_idx:
            missing_texts = [texts[i] for i in missing_idx]
            missing_embs = self._embedding_service.encode(missing_texts)
            for i, emb in zip(missing_idx, missing_embs):
                embeddings[i] = emb

        # 写入向量库
        self._vector_store.add_documents(texts, embeddings, metadatas)

        # 写入 BM25 索引
        doc_ids = [str(uuid.uuid4()) for _ in range(len(texts))]
        bm25_docs = [
            {"id": doc_id, "text": text, "metadata": meta}
            for doc_id, text, meta in zip(doc_ids, texts, metadatas)
        ]
        self._bm25_retriever.add_documents(bm25_docs)

        return len(chunks)

    def delete_by_source(self, source: str):
        """按来源删除文档（向量库 + BM25 + 缓存失效）"""
        self._vector_store.delete_by_source(source)
        self._bm25_retriever.delete_by_source(source)
        # 缓存失效
        self._cache_manager.invalidate_by_source(source)

    def delete_all(self):
        """清空所有文档"""
        self._vector_store.delete_all()
        self._bm25_retriever.delete_all()
        # 删除持久化文件
        if self._bm25_retriever.persist_path and os.path.exists(self._bm25_retriever.persist_path):
            os.remove(self._bm25_retriever.persist_path)
        # 清空缓存
        self._cache_manager.clear()

    def sync_index(self, data_dir: str) -> dict:
        """增量同步索引

        扫描 data_dir 目录，对比已索引文档的 Hash，
        只处理新增、修改、删除的文档。

        Args:
            data_dir: 数据目录路径

        Returns:
            {"added": int, "modified": int, "deleted": int, "unchanged": int}
        """
        changes = self._index_manager.detect_changes(data_dir)
        stats = {
            "added": 0,
            "modified": 0,
            "deleted": 0,
            "unchanged": len(changes["unchanged"])
        }

        # 处理删除
        for filename in changes["deleted"]:
            try:
                self.delete_by_source(filename)
                self._index_manager.remove_record(filename)
                stats["deleted"] += 1
                logger.info("Deleted from index: %s", filename)
            except Exception as e:
                logger.warning("Failed to delete %s: %s", filename, e)

        # 处理新增和修改
        for filename in changes["added"] + changes["modified"]:
            file_path = os.path.join(data_dir, filename)
            try:
                # 修改场景：先删旧的
                if filename in changes["modified"]:
                    self.delete_by_source(filename)

                # 索引新文档
                chunks = self.ingest_document(file_path)
                file_hash = IndexManager.compute_file_hash(file_path)
                self._index_manager.record_indexed(filename, file_hash, chunks)

                if filename in changes["added"]:
                    stats["added"] += 1
                    logger.info("Added to index: %s (%d chunks)", filename, chunks)
                else:
                    stats["modified"] += 1
                    logger.info("Updated index: %s (%d chunks)", filename, chunks)
            except Exception as e:
                logger.warning("Failed to index %s: %s", filename, e)

        logger.info("Sync completed: %s", stats)
        return stats

    def get_index_stats(self) -> dict:
        """获取索引统计信息"""
        return {
            "indexed_documents": self._index_manager.get_record_count(),
            "vector_count": self._vector_store.get_document_count(),
            "bm25_ready": self._infra.bm25_ready,
        }

    def close(self):
        """释放资源（当前无需特殊清理）。"""
        pass
