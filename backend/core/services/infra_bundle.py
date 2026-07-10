"""基础设施数据包。

InfraBundle 是所有 RAG 服务共享依赖的容器，由 infra_factory.create_infra 构建。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class InfraBundle:
    """所有 RAG 服务共享依赖的容器。

    为什么用 dataclass 而非 dict：提供类型提示和属性访问，
    IDE 可以自动补全，避免键名拼写错误。
    """

    settings: Any  # AppSettings
    embedding_service: Any
    vector_store: Any
    llm_client: Any
    bm25_retriever: Any
    document_processor: Any
    rerank_manager: Any
    cache_manager: Any
    index_manager: Any
    classifier: Any
    router: Any
    rewriters: dict = field(default_factory=dict)
    confidence_evaluator: Any = None
    citation_verifier: Any = None
    self_rag_reflector: Any = None
    metrics_collector: Any = None
    executor: Any = None  # ThreadPoolExecutor
    image_store: Any = None
    bm25_ready: bool = False
    graph_store: Any = None
    graph_retriever: Any = None
    kg_extractor: Any = None
