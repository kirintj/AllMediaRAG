"""适配器：将现有实现包装为 Provider 接口

这些适配器允许现有的 VectorStore、EmbeddingService、LLMClient
无缝集成到 ProviderFactory 工厂模式中，无需修改原始代码。
"""

from typing import Generator
from .base import VectorStoreProvider, EmbeddingProvider, LLMProvider


class ChromaVectorStoreAdapter(VectorStoreProvider):
    """将现有 VectorStore 适配为 VectorStoreProvider 接口"""

    def __init__(self, persist_dir: str):
        from core.vector_store import VectorStore
        self._store = VectorStore(persist_dir)

    def add_documents(self, texts: list[str], embeddings: list, metadatas: list) -> None:
        self._store.add_documents(texts, embeddings, metadatas)

    def query(self, embedding: list[float], top_k: int) -> dict:
        return self._store.query(embedding, top_k)

    def delete_by_source(self, source: str) -> None:
        self._store.delete_by_source(source)

    def get_all_sources(self) -> list[str]:
        return self._store.get_all_sources()

    def get_document_count(self) -> int:
        return self._store.get_document_count()

    def delete_all(self) -> None:
        self._store.delete_all()

    def get_all_documents(self) -> list[dict]:
        return self._store.get_all_documents()


class SentenceTransformerAdapter(EmbeddingProvider):
    """将现有 EmbeddingService 适配为 EmbeddingProvider 接口"""

    def __init__(self, model_path: str):
        from core.embedding_service import EmbeddingService
        self._service = EmbeddingService(model_path)

    def encode(self, texts: list[str]) -> list[list[float]]:
        return self._service.encode(texts)

    def encode_single(self, text: str) -> list[float]:
        return self._service.encode_single(text)


class OpenAICompatibleLLMAdapter(LLMProvider):
    """将现有 LLMClient 适配为 LLMProvider 接口"""

    def __init__(self, api_key: str, api_base: str, model: str):
        from core.llm_client import LLMClient
        self._client = LLMClient(api_key, api_base, model)

    def generate(self, prompt: str) -> str:
        return self._client.generate(prompt)

    def stream_generate(self, prompt: str) -> Generator[str, None, None]:
        return self._client.stream_generate(prompt)
