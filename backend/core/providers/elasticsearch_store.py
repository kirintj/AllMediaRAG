"""Elasticsearch 向量存储适配器。

实现 VectorStoreProvider 接口，使用 ES 8.x 原生混合检索（knn + bool）。
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import jieba
from elasticsearch import Elasticsearch

from core.providers.base import (
    VectorStoreProvider, MatchTextExpr, MatchDenseExpr, FusionExpr, OrderByExpr,
)

logger = logging.getLogger(__name__)


class ElasticsearchStore(VectorStoreProvider):
    """Elasticsearch 8.x 向量存储适配器。

    索引命名：{index_prefix}_{tenant_id}（默认 allrag_default）。
    """

    def __init__(
        self,
        hosts: str = "http://localhost:9200",
        index_prefix: str = "allrag",
        tenant_id: str = "default",
        username: str = "",
        password: str = "",
        embedding_dim: int = 1024,
        number_of_shards: int = 1,
        number_of_replicas: int = 0,
    ):
        self._index_prefix = index_prefix
        self._tenant_id = tenant_id
        self._embedding_dim = embedding_dim
        self._number_of_shards = number_of_shards
        self._number_of_replicas = number_of_replicas

        # 连接 ES
        kwargs: dict[str, Any] = {"hosts": hosts}
        if username and password:
            kwargs["basic_auth"] = (username, password)
        self._client = Elasticsearch(**kwargs)

        # 确保索引存在
        self._ensure_index()
        logger.info(
            "ElasticsearchStore initialized: index=%s, dim=%d",
            self._index_name, embedding_dim,
        )

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------

    @property
    def _index_name(self) -> str:
        return f"{self._index_prefix}_{self._tenant_id}"

    def _ensure_index(self):
        """如果索引不存在则创建"""
        if self._client.indices.exists(index=self._index_name).body:
            return
        self.create_idx(self._index_name, self._embedding_dim)

    @staticmethod
    def _tokenize(text: str) -> str:
        """jieba 分词后用空格连接"""
        return " ".join(w for w in jieba.cut(text) if w.strip())

    def _find_expr(self, expressions: list, expr_type: type):
        """从表达式列表中查找指定类型的表达式"""
        for expr in expressions:
            if isinstance(expr, expr_type):
                return expr
        return None

    def _build_condition_filter(self, condition: dict) -> list[dict]:
        """将条件字典转换为 ES term 查询列表"""
        filters = []
        for key, value in condition.items():
            if isinstance(value, list):
                filters.append({"terms": {key: value}})
            else:
                filters.append({"term": {key: value}})
        return filters

    # ------------------------------------------------------------------
    # 连接信息
    # ------------------------------------------------------------------

    def db_type(self) -> str:
        return "elasticsearch"

    def health(self) -> dict:
        try:
            resp = self._client.cluster.health()
            return {
                "status": resp["status"],
                "cluster_name": resp["cluster_name"],
                "number_of_nodes": resp["number_of_nodes"],
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ------------------------------------------------------------------
    # 索引管理
    # ------------------------------------------------------------------

    def create_idx(self, index_name: str, vector_size: int):
        """创建 ES 索引 + mapping"""
        mapping = {
            "settings": {
                "number_of_shards": self._number_of_shards,
                "number_of_replicas": self._number_of_replicas,
            },
            "mappings": {
                "properties": {
                    "text": {"type": "text", "analyzer": "whitespace"},
                    "text_raw": {"type": "text", "index": False},
                    "embedding": {
                        "type": "dense_vector",
                        "dims": vector_size,
                        "index": True,
                        "similarity": "cosine",
                        "index_options": {
                            "type": "hnsw",
                            "m": 16,
                            "ef_construction": 100,
                        },
                    },
                    "source": {"type": "keyword"},
                    "kb_id": {"type": "keyword"},
                    "tenant_id": {"type": "keyword"},
                    "chunk_id": {"type": "keyword"},
                    "metadata": {"type": "object", "enabled": False},
                    "created_at": {"type": "date"},
                }
            },
        }
        self._client.indices.create(index=index_name, body=mapping)
        logger.info("Created ES index: %s (dims=%d)", index_name, vector_size)

    def delete_idx(self, index_name: str = ""):
        """删除索引"""
        target = index_name or self._index_name
        if self._client.indices.exists(index=target).body:
            self._client.indices.delete(index=target)
            logger.info("Deleted ES index: %s", target)

    def index_exist(self, index_name: str) -> bool:
        return self._client.indices.exists(index=index_name).body

    # ------------------------------------------------------------------
    # 统一查询
    # ------------------------------------------------------------------

    def search(
        self,
        select_fields: list[str],
        condition: dict | None,
        match_expressions: list,
        order_by: Any | None = None,
        offset: int = 0,
        limit: int = 10,
    ) -> dict:
        text_expr = self._find_expr(match_expressions, MatchTextExpr)
        dense_expr = self._find_expr(match_expressions, MatchDenseExpr)
        fusion_expr = self._find_expr(match_expressions, FusionExpr)

        # limit=0 表示只取 total（count 语义）
        if limit == 0:
            body: dict[str, Any] = {"query": {"match_all": {}}}
            if condition:
                body["query"] = {"bool": {
                    "must": [{"match_all": {}}],
                    "filter": self._build_condition_filter(condition),
                }}
            resp = self._client.count(index=self._index_name, body=body)
            return {"documents": [], "metadatas": [], "distances": [], "total": resp["count"]}

        # 构建查询体
        body = self._build_search_body(
            text_expr, dense_expr, fusion_expr, condition,
            offset, limit,
        )

        # 执行搜索
        resp = self._client.search(
            index=self._index_name,
            body=body,
            source=select_fields if select_fields else True,
        )

        return self._parse_search_response(resp, select_fields)

    def _build_search_body(
        self,
        text_expr: MatchTextExpr | None,
        dense_expr: MatchDenseExpr | None,
        fusion_expr: FusionExpr | None,
        condition: dict | None,
        offset: int,
        limit: int,
    ) -> dict:
        """根据表达式构建 ES 查询体"""
        body: dict[str, Any] = {"size": limit}
        if offset > 0:
            body["from"] = offset

        condition_filter = self._build_condition_filter(condition) if condition else []

        if text_expr and dense_expr:
            # 混合检索：knn + bool/match
            knn_clause: dict[str, Any] = {
                "field": "embedding",
                "query_vector": dense_expr.embedding_data,
                "k": dense_expr.topn,
                "num_candidates": dense_expr.topn * 10,
            }
            msm = "70%"
            if text_expr.extra_options:
                msm = text_expr.extra_options.get("minimum_should_match", msm)
            body["knn"] = knn_clause
            body["query"] = {
                "bool": {
                    "must": [
                        {"match": {"text": {"query": text_expr.matching_text, "minimum_should_match": msm}}}
                    ],
                    "filter": condition_filter,
                }
            }
            # 融合权重
            if fusion_expr and fusion_expr.fusion_params:
                weights_str = fusion_expr.fusion_params.get("weights", "0.7,0.3")
                parts = [float(w.strip()) for w in weights_str.split(",")]
                if len(parts) == 2:
                    body["knn"]["boost"] = parts[1]  # vector weight
                    body["query"]["bool"]["must"][0]["match"]["text"]["boost"] = parts[0]  # text weight

        elif dense_expr:
            # 纯向量检索
            body["knn"] = {
                "field": "embedding",
                "query_vector": dense_expr.embedding_data,
                "k": dense_expr.topn,
                "num_candidates": dense_expr.topn * 10,
                "filter": {"bool": {"filter": condition_filter}} if condition_filter else None,
            }
            if condition_filter:
                body["query"] = {"bool": {"filter": condition_filter}}

        elif text_expr:
            # 纯全文检索
            msm = "70%"
            if text_expr.extra_options:
                msm = text_expr.extra_options.get("minimum_should_match", msm)
            body["query"] = {
                "bool": {
                    "must": [
                        {"match": {"text": {"query": text_expr.matching_text, "minimum_should_match": msm}}}
                    ],
                    "filter": condition_filter,
                }
            }
        else:
            # 无表达式 → match_all（带条件过滤）
            if condition_filter:
                body["query"] = {"bool": {"filter": condition_filter}}
            else:
                body["query"] = {"match_all": {}}

        return body

    def _parse_search_response(self, resp: dict, select_fields: list[str]) -> dict:
        """解析 ES 搜索响应为标准格式"""
        hits = resp.get("hits", {})
        total = hits.get("total", {})
        total_count = total.get("value", 0) if isinstance(total, dict) else total

        documents = []
        metadatas = []
        distances = []

        for hit in hits.get("hits", []):
            src = hit.get("_source", {})
            doc_id = hit.get("_id", "")

            # 返回查询到的原始文本（text_raw），而非分词后的 text
            text = src.get("text_raw", src.get("text", ""))

            meta = {"id": doc_id}
            for field in select_fields:
                if field == "id":
                    continue
                if field == "text":
                    meta["text"] = text
                elif field == "text_raw":
                    meta["text_raw"] = text
                else:
                    meta[field] = src.get(field)

            # score → distance（ES 返回的是相似度分数，转为距离）
            score = hit.get("_score", 0) or 0
            distance = max(0, 1 - score) if score > 0 else 1.0

            documents.append(text)
            metadatas.append(meta)
            distances.append(distance)

        return {
            "documents": documents,
            "metadatas": metadatas,
            "distances": distances,
            "total": total_count,
        }

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def insert(self, rows: list[dict]) -> list[str]:
        """批量插入文档。text 字段需已分词。"""
        errors: list[str] = []
        if not rows:
            return errors

        from elasticsearch.helpers import bulk, BulkIndexError

        actions = []
        for row in rows:
            doc_id = row.get("id", str(uuid.uuid4()))
            doc = {
                "_index": self._index_name,
                "_id": doc_id,
                "_source": {
                    "text": row.get("text", ""),
                    "text_raw": row.get("text_raw", ""),
                    "embedding": row.get("embedding", []),
                    "source": row.get("source", ""),
                    "kb_id": row.get("kb_id", ""),
                    "tenant_id": row.get("tenant_id", self._tenant_id),
                    "chunk_id": row.get("chunk_id", ""),
                    "metadata": row.get("metadata", {}),
                    "created_at": row.get("created_at", datetime.now(timezone.utc).isoformat()),
                },
            }
            actions.append(doc)

        try:
            success, failed = bulk(self._client, actions, raise_on_error=False)
            if failed:
                for item in failed:
                    for op_type, info in item.items():
                        errors.append(f"{op_type}: {info.get('error', 'unknown')}")
            logger.debug("Inserted %d/%d docs into %s", success, len(rows), self._index_name)
        except BulkIndexError as e:
            for err in e.errors:
                errors.append(str(err))
        except Exception as e:
            logger.exception("Bulk insert failed")
            errors.append(str(e))

        return errors

    def get(self, doc_id: str) -> dict | None:
        try:
            resp = self._client.get(index=self._index_name, id=doc_id, ignore=[404])
            if not resp.get("found"):
                return None
            src = resp["_source"]
            return {"id": resp["_id"], **src}
        except Exception:
            return None

    def delete(self, condition: dict) -> int:
        query = {"bool": {"filter": self._build_condition_filter(condition)}}
        try:
            resp = self._client.delete_by_query(
                index=self._index_name, body={"query": query}, refresh=True,
            )
            deleted = resp.get("deleted", 0)
            logger.debug("Deleted %d docs from %s with condition %s", deleted, self._index_name, condition)
            return deleted
        except Exception as e:
            logger.exception("Delete failed")
            return 0

    def update(self, condition: dict, new_value: dict) -> bool:
        query = {"bool": {"filter": self._build_condition_filter(condition)}}
        script = {
            "source": "; ".join(f"ctx._source.{k} = params.{k}" for k in new_value),
            "lang": "painless",
            "params": new_value,
        }
        try:
            resp = self._client.update_by_query(
                index=self._index_name,
                body={"query": query, "script": script},
                refresh=True,
            )
            updated = resp.get("updated", 0)
            logger.debug("Updated %d docs in %s", updated, self._index_name)
            return updated > 0
        except Exception as e:
            logger.exception("Update failed")
            return False

    # ------------------------------------------------------------------
    # 聚合（覆盖基类实现，避免 ES result_window 上限问题）
    # ------------------------------------------------------------------

    def get_all_sources(self) -> list[str]:
        """使用 ES terms 聚合获取所有来源名称。"""
        body = {
            "size": 0,
            "aggs": {
                "by_source": {
                    "terms": {"field": "source", "size": 10000},
                }
            },
        }
        try:
            resp = self._client.search(index=self._index_name, body=body)
            buckets = resp["aggregations"]["by_source"]["buckets"]
            return [b["key"] for b in buckets if b["key"]]
        except Exception as e:
            logger.warning("ES aggregation failed, falling back to base: %s", e)
            return super().get_all_sources()

    def get_source_details(self) -> list[dict]:
        """使用 ES terms 聚合按 source 统计 chunk 数量，无需拉取全量数据。"""
        body = {
            "size": 0,
            "aggs": {
                "by_source": {
                    "terms": {"field": "source", "size": 10000},
                }
            },
        }
        try:
            resp = self._client.search(index=self._index_name, body=body)
            buckets = resp["aggregations"]["by_source"]["buckets"]
            return [
                {"source": b["key"], "chunks": b["doc_count"]}
                for b in buckets
                if b["key"]
            ]
        except Exception as e:
            logger.warning("ES aggregation failed, falling back to base: %s", e)
            return super().get_source_details()

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------

    def close(self):
        try:
            self._client.close()
        except Exception:
            pass
