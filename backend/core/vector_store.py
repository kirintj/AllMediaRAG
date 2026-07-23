import uuid

from core.providers.base import VectorStoreProvider


class VectorStore(VectorStoreProvider):
    """向量存储服务：封装 Chroma 向量数据库操作"""

    def __init__(self, persist_dir: str):
        """初始化向量存储（延迟加载 ChromaDB）

        Args:
            persist_dir: 持久化目录
        """
        self._persist_dir = persist_dir
        self._client = None
        self._collection = None
        # source -> chunk count 的增量索引（避免每次请求遍历全量 metadata）
        self._source_stats: dict[str, int] | None = None

    def _ensure_initialized(self):
        """首次使用时初始化 ChromaDB 客户端"""
        if self._client is None:
            import chromadb
            self._client = chromadb.PersistentClient(path=self._persist_dir)
            self._collection = self._client.get_or_create_collection(
                name="python_docs",
                metadata={"hnsw:space": "cosine"}
            )

    @property
    def client(self):
        self._ensure_initialized()
        return self._client

    @property
    def collection(self):
        self._ensure_initialized()
        return self._collection

    def _build_source_stats(self) -> dict[str, int]:
        """一次遍历全量 metadata 构建 source -> chunk_count 索引。仅冷启动时调用。"""
        stats: dict[str, int] = {}
        for metadata in self._iter_metadatas():
            if metadata and "source" in metadata:
                src = metadata["source"]
                stats[src] = stats.get(src, 0) + 1
        return stats

    def _ensure_source_stats(self):
        """确保 source 索引已构建（延迟初始化）"""
        if self._source_stats is None:
            self._source_stats = self._build_source_stats()

    def add_documents(self, texts: list[str], embeddings: list, metadatas: list):
        """添加文档到向量库

        Args:
            texts: 文本列表
            embeddings: 向量列表
            metadatas: 元数据列表
        """
        ids = [str(uuid.uuid4()) for _ in range(len(texts))]
        self.collection.add(
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )
        # 增量更新 source 索引，无需全量遍历
        if self._source_stats is not None:
            for meta in metadatas:
                if meta and "source" in meta:
                    src = meta["source"]
                    self._source_stats[src] = self._source_stats.get(src, 0) + 1

    def query(self, embedding: list[float], top_k: int) -> dict:
        """检索最相似的文档

        Args:
            embedding: 查询向量
            top_k: 返回数量

        Returns:
            检索结果，包含 documents, metadatas, distances
        """
        results = self.collection.query(
            query_embeddings=[embedding],
            n_results=top_k
        )

        return {
            "documents": results["documents"][0] if results["documents"] else [],
            "metadatas": results["metadatas"][0] if results["metadatas"] else [],
            "distances": results["distances"][0] if results["distances"] else []
        }

    def delete_by_source(self, source: str):
        """按来源删除文档

        Args:
            source: 文档来源标识
        """
        results = self.collection.get(
            where={"source": source}
        )
        if results["ids"]:
            self.collection.delete(ids=results["ids"])
            # 增量更新 source 索引
            if self._source_stats is not None:
                self._source_stats.pop(source, None)

    # 分页读取每页大小。Chroma 默认使用 SQLite 存储，
    # SQLITE_MAX_VARIABLE_NUMBER 限制单条语句占位符数量（约 999）；
    # 当集合中 chunk 数很大（数万）时，一次性 get 会触发 "too many SQL variables"。
    _BATCH_SIZE: int = 500

    def _iter_metadatas(self):
        """分页读取所有 metadatas，避免单次查询过大。

        Yields:
            每条 metadata（dict 或 None）
        """
        total = self.collection.count()
        if total == 0:
            return
        limit = self._BATCH_SIZE
        offset = 0
        while offset < total:
            batch = self.collection.get(
                limit=limit,
                offset=offset,
                include=["metadatas"],
            )
            metadatas = batch.get("metadatas") or []
            if not metadatas:
                break
            for metadata in metadatas:
                yield metadata
            if len(metadatas) < limit:
                break
            offset += limit

    def get_all_sources(self) -> list[str]:
        """获取所有文档来源（O(1) 读取，从增量索引返回）"""
        self._ensure_source_stats()
        return list(self._source_stats.keys())

    def get_document_count(self) -> int:
        """获取文档总数

        Returns:
            文档数量
        """
        return self.collection.count()

    def delete_all(self):
        """清空所有文档"""
        self.client.delete_collection("python_docs")
        self.collection = self.client.get_or_create_collection(
            name="python_docs",
            metadata={"hnsw:space": "cosine"}
        )
        self._source_stats = {}

    def get_source_details(self) -> list[dict]:
        """获取每个来源的 chunk 数量（O(1) 读取，从增量索引返回）"""
        self._ensure_source_stats()
        return [{"source": src, "chunks": cnt} for src, cnt in self._source_stats.items()]

    def get_overview(self) -> dict:
        """一次返回前端需要的所有 source 数据，避免多次调用"""
        self._ensure_source_stats()
        return {
            "sources": list(self._source_stats.keys()),
            "source_details": [
                {"source": src, "chunks": cnt}
                for src, cnt in self._source_stats.items()
            ],
            "document_count": self.collection.count(),
        }

    def close(self):
        """关闭客户端，释放资源"""
        if self._client is not None:
            self._client.close()

    def _iter_documents(self, include):
        """分页读取指定字段，返回 (id, text, metadata 列表。

        Args:
            include: chromadb.get() 的 include 参数（如 ["documents", "metadatas"]）

        Yields:
            (doc_id, text, metadata) 元组
        """
        total = self.collection.count()
        if total == 0:
            return
        limit = self._BATCH_SIZE
        offset = 0
        want_documents = "documents" in include
        want_metadatas = "metadatas" in include
        while offset < total:
            batch = self.collection.get(
                limit=limit,
                offset=offset,
                include=include,
            )
            ids = batch.get("ids") or []
            if not ids:
                break
            documents = batch.get("documents") or [None] * len(ids)
            metadatas = batch.get("metadatas") or [None] * len(ids)
            for i in range(len(ids)):
                doc_id = ids[i]
                text = documents[i] if want_documents else None
                meta = metadatas[i] if want_metadatas else None
                yield doc_id, text, meta
            if len(ids) < limit:
                break
            offset += limit

    def get_all_documents(self) -> list[dict]:
        """获取所有文档（用于重建 BM25 索引，分页读取避免 SQLite 变量限制）

        Returns:
            [{"id": str, "text": str, "metadata": dict}, ...]
        """
        docs = []
        for doc_id, text, meta in self._iter_documents(["documents", "metadatas"]):
            docs.append({
                "id": doc_id,
                "text": text,
                "metadata": meta or {},
            })
        return docs
