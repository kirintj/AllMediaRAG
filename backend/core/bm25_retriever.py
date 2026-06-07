import os
import pickle
import logging
import threading
import jieba
from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)


class BM25Retriever:
    """BM25 关键词检索器（支持磁盘持久化）"""

    def __init__(self, persist_path: str = None):
        self.bm25 = None
        self.doc_ids = []
        self.doc_map = {}
        self.persist_path = persist_path
        self._lock = threading.Lock()

    def _tokenize(self, text: str) -> list[str]:
        """jieba 分词，过滤空白 token"""
        return [w for w in jieba.lcut(text) if w.strip()]

    def build_index(self, documents: list[dict]):
        """从文档列表构建 BM25 索引

        Args:
            documents: [{"id": str, "text": str, "metadata": dict}, ...]
        """
        self.doc_ids = []
        self.doc_map = {}
        tokenized_corpus = []

        for doc in documents:
            doc_id = doc["id"]
            self.doc_ids.append(doc_id)
            self.doc_map[doc_id] = {
                "text": doc["text"],
                "metadata": doc["metadata"],
            }
            tokenized_corpus.append(self._tokenize(doc["text"]))

        self.bm25 = BM25Okapi(tokenized_corpus)

    def search(self, query: str, top_k: int) -> list[dict]:
        """检索最相似的文档

        Args:
            query: 查询文本
            top_k: 返回数量

        Returns:
            [{"id": str, "score": float, "text": str, "metadata": dict}, ...]
        """
        with self._lock:
            if not self.bm25 or not self.doc_ids:
                return []

            tokenized_query = self._tokenize(query)
            scores = self.bm25.get_scores(tokenized_query)

            # 按分数降序取 top_k
            ranked = sorted(
                enumerate(scores), key=lambda x: x[1], reverse=True
            )[:top_k]

            results = []
            for idx, score in ranked:
                doc_id = self.doc_ids[idx]
                doc = self.doc_map[doc_id]
                results.append({
                    "id": doc_id,
                    "score": float(score),
                    "text": doc["text"],
                    "metadata": doc["metadata"],
                })

        return results

    def add_documents(self, documents: list[dict]):
        """增量添加文档（重建索引）

        Args:
            documents: [{"id": str, "text": str, "metadata": dict}, ...]
        """
        with self._lock:
            for doc in documents:
                doc_id = doc["id"]
                if doc_id not in self.doc_map:
                    self.doc_ids.append(doc_id)
                    self.doc_map[doc_id] = {
                        "text": doc["text"],
                        "metadata": doc["metadata"],
                    }

            self._rebuild()

    def delete_by_source(self, source: str):
        """按来源删除文档（重建索引）

        Args:
            source: 文档来源标识
        """
        ids_to_remove = set()
        for doc_id, doc in self.doc_map.items():
            if doc["metadata"].get("source") == source:
                ids_to_remove.add(doc_id)

        self.doc_ids = [i for i in self.doc_ids if i not in ids_to_remove]
        for doc_id in ids_to_remove:
            del self.doc_map[doc_id]

        self._rebuild()

    def delete_all(self):
        """清空索引"""
        self.bm25 = None
        self.doc_ids = []
        self.doc_map = {}

    def _rebuild(self):
        """重建 BM25 索引"""
        if not self.doc_ids:
            self.bm25 = None
            return

        tokenized_corpus = [
            self._tokenize(self.doc_map[doc_id]["text"])
            for doc_id in self.doc_ids
        ]
        self.bm25 = BM25Okapi(tokenized_corpus)
        self.save()

    def save(self):
        """将索引持久化到磁盘"""
        if not self.persist_path:
            return
        try:
            data = {
                "doc_ids": self.doc_ids,
                "doc_map": self.doc_map,
                "tokenized_corpus": [
                    self._tokenize(self.doc_map[did]["text"])
                    for did in self.doc_ids
                ],
            }
            os.makedirs(os.path.dirname(self.persist_path), exist_ok=True)
            with open(self.persist_path, "wb") as f:
                pickle.dump(data, f)
            logger.info("BM25 index saved: %d docs", len(self.doc_ids))
        except Exception as e:
            logger.warning("Failed to save BM25 index: %s", e)

    def load(self) -> bool:
        """从磁盘加载索引，成功返回 True"""
        if not self.persist_path or not os.path.exists(self.persist_path):
            return False
        try:
            with open(self.persist_path, "rb") as f:
                data = pickle.load(f)
            self.doc_ids = data["doc_ids"]
            self.doc_map = data["doc_map"]
            self.bm25 = BM25Okapi(data["tokenized_corpus"])
            logger.info("BM25 index loaded: %d docs", len(self.doc_ids))
            return True
        except Exception as e:
            logger.warning("Failed to load BM25 index: %s", e)
            return False
