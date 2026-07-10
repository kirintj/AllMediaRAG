"""RAG Engine: Service 层门面。

职责：组合 InfraBundle + 三大 Service（Retrieval / Ingestion / Generation），
提供统一的业务 API（retrieve / ingest / generate / query_stream）。

为什么不直接暴露 Service：RAGEngine 提供单一入口和生命周期管理（close），
调用方（main.py、API 路由）只需持有一个 engine 引用。
"""
import logging
from typing import Generator

from core.services import create_infra, InfraBundle
from core.services.bundle_factory import BundleFactory
from core.services.retrieval_pipeline import RetrievalPipeline
from core.services.ingestion_service import IngestionService
from core.services.generation_service import GenerationService

logger = logging.getLogger(__name__)


class RAGEngine:
    """RAG 引擎门面，委托所有业务操作给 Service 层。"""

    def __init__(self, config, use_factory: bool = False):
        self._config = config
        self._use_factory = use_factory
        self._infra = create_infra(config)

        # Bundle 层（供测试使用，API 路由已迁移到 Service 层）
        self._bundle_factory = BundleFactory(self._infra)
        self.retrieval_bundle = self._bundle_factory.create_retrieval_bundle()
        self.processing_bundle = self._bundle_factory.create_processing_bundle()
        self.generation_bundle = self._bundle_factory.create_generation_bundle()

        # Service 层（API 路由实际使用的三个服务）
        self.retrieval = RetrievalPipeline(self._infra)
        self.ingestion = IngestionService(self._infra)
        self.generation = GenerationService(self._infra, self.retrieval)

        # 高频访问属性快捷方式（scripts/rebuild_index.py 等使用）
        self.embedding_service = self._infra.embedding_service
        self.vector_store = self._infra.vector_store
        self.bm25_retriever = self._infra.bm25_retriever

        logger.info("RAGEngine initialized (infra + 3 services)")

    @classmethod
    def from_services(cls, config, infra: InfraBundle, retrieval, ingestion, generation):
        """从已有的 infra 和 Service 构建门面。

        用途：main.py 在 lifespan 中先创建 infra 和 Service，
        再通过此方法构建 engine，避免重复 create_infra。
        """
        instance = cls.__new__(cls)
        instance._config = config
        instance._use_factory = False
        instance._infra = infra

        instance._bundle_factory = BundleFactory(infra)
        instance.retrieval_bundle = instance._bundle_factory.create_retrieval_bundle()
        instance.processing_bundle = instance._bundle_factory.create_processing_bundle()
        instance.generation_bundle = instance._bundle_factory.create_generation_bundle()

        instance.retrieval = retrieval
        instance.ingestion = ingestion
        instance.generation = generation

        instance.embedding_service = infra.embedding_service
        instance.vector_store = infra.vector_store
        instance.bm25_retriever = infra.bm25_retriever

        logger.info("RAGEngine initialized (from pre-existing services)")
        return instance

    # ------------------------------------------------------------------
    # Business methods — 委托给 Service 层
    # ------------------------------------------------------------------

    # -- Retrieval -------------------------------------------------------

    def retrieve(self, query: str, top_k: int = None) -> dict:
        """完整检索管线（含 query understanding / rerank / cache）。"""
        return self.retrieval.full_retrieve(query)

    def full_retrieve(self, query: str) -> dict:
        return self.retrieval.full_retrieve(query)

    async def full_retrieve_async(self, query: str) -> dict:
        return await self.retrieval.full_retrieve_async(query)

    # -- Ingestion -------------------------------------------------------

    def ingest_document(self, file_path: str) -> int:
        return self.ingestion.ingest_document(file_path)

    def delete_by_source(self, source: str):
        self.ingestion.delete_by_source(source)

    def delete_all(self):
        self.ingestion.delete_all()

    def sync_index(self, data_dir: str) -> dict:
        return self.ingestion.sync_index(data_dir)

    def get_index_stats(self) -> dict:
        return self.ingestion.get_index_stats()

    # -- Generation ------------------------------------------------------

    def build_prompt(self, query: str, contexts: list[dict], history: list[dict] = None) -> str:
        return self.generation.build_prompt(query, contexts, history=history)

    def query_stream(self, question: str, history: list[dict] = None) -> Generator[dict, None, None]:
        yield from self.generation.query_stream(question, history=history)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self):
        """释放所有资源。"""
        try:
            if self.embedding_service:
                self.embedding_service._model = None

            rerank_mgr = self._infra.rerank_manager
            if rerank_mgr and hasattr(rerank_mgr, '_model'):
                rerank_mgr._model = None

            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except ImportError:
                pass

            self.retrieval.close()
            self.ingestion.close()
            self.generation.close()

            if hasattr(self.vector_store, 'close'):
                self.vector_store.close()
            if hasattr(self._infra.index_manager, 'close'):
                self._infra.index_manager.close()

            logger.info("RAGEngine closed")
        except Exception as e:
            logger.warning("Error closing RAGEngine: %s", e)
