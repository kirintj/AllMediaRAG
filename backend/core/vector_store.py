import uuid

import chromadb


class VectorStore:
    """向量存储服务：封装 Chroma 向量数据库操作"""

    def __init__(self, persist_dir: str):
        """初始化 Chroma 客户端

        Args:
            persist_dir: 持久化目录
        """
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection(
            name="python_docs",
            metadata={"hnsw:space": "cosine"}
        )

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

    def get_all_sources(self) -> list[str]:
        """获取所有文档来源

        Returns:
            去重后的来源列表
        """
        results = self.collection.get()
        sources = set()
        for metadata in results["metadatas"]:
            if metadata and "source" in metadata:
                sources.add(metadata["source"])
        return list(sources)

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

    def close(self):
        """关闭客户端，释放资源"""
        self.client.close()

    def get_all_documents(self) -> list[dict]:
        """获取所有文档（用于重建 BM25 索引）

        Returns:
            [{"id": str, "text": str, "metadata": dict}, ...]
        """
        results = self.collection.get(include=["documents", "metadatas"])
        docs = []
        for doc_id, text, meta in zip(results["ids"], results["documents"], results["metadatas"]):
            docs.append({
                "id": doc_id,
                "text": text,
                "metadata": meta or {},
            })
        return docs
