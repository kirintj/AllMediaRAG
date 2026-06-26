"""共享测试 fixtures

提供 mock 引擎、测试客户端和认证 headers，
供所有 API 集成测试使用。
"""
import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# 确保 backend 目录在 Python 路径中
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """重置速率限制器，避免测试间互相影响。"""
    from core.rate_limit import limiter
    limiter._storage.reset()
    yield
    limiter._storage.reset()


@pytest.fixture(autouse=True)
def _mock_engine(monkeypatch):
    """Mock 掉 RAG 引擎初始化，避免加载真实模型。

    Patches ``create_infra`` so the lifespan initialisation path
    (InfraBundle + 3 services + RAGEngine facade) receives mock objects.
    Also mocks the user store so testuser can authenticate via JWT.
    """
    # -- Build a mock InfraBundle with all attributes the services need ----
    mock_infra = MagicMock()
    mock_infra.embedding_service = MagicMock()
    mock_infra.vector_store = MagicMock()
    mock_infra.vector_store.get_all_sources = MagicMock(return_value=[])
    mock_infra.vector_store.get_document_count = MagicMock(return_value=0)
    mock_infra.vector_store.close = MagicMock()
    mock_infra.llm_client = MagicMock()
    mock_infra.document_processor = MagicMock()
    mock_infra.bm25_retriever = MagicMock()
    mock_infra.rerank_manager = MagicMock()
    mock_infra.cache_manager = MagicMock()
    mock_infra.index_manager = MagicMock()
    mock_infra.index_manager.close = MagicMock()
    mock_infra.classifier = MagicMock()
    mock_infra.router = MagicMock()
    mock_infra.rewriters = {}
    mock_infra.confidence_evaluator = MagicMock()
    mock_infra.citation_verifier = MagicMock()
    mock_infra.self_rag_reflector = MagicMock()
    mock_infra.executor = MagicMock()
    mock_infra.bm25_ready = True
    # 新增字段：VLM Extractor 和 ImageStore（默认禁用，不影响旧测试）
    mock_infra.image_store = None
    mock_infra.settings.USE_VLM_EXTRACTOR = False
    mock_infra.settings.MULTIMODAL_GENERATION = False
    mock_infra.settings.MULTIMODAL_MAX_IMAGES = 3
    # settings attributes accessed by RAGEngine and services
    mock_infra.settings.TOP_K = 5
    mock_infra.settings.BM25_TOP_K = 6
    mock_infra.settings.RRF_K = 60
    mock_infra.settings.RRF_WEIGHT_VECTOR = 0.7
    mock_infra.settings.RRF_WEIGHT_BM25 = 0.3
    mock_infra.settings.SIMILARITY_THRESHOLD = 0.5
    mock_infra.settings.USE_HYDE = False
    mock_infra.settings.MULTI_QUERY_ENABLED = False
    mock_infra.settings.MULTI_QUERY_COUNT = 3
    mock_infra.settings.RERANK_TOP_K = 40
    mock_infra.settings.RERANK_GATE_THRESHOLD = 0.3
    mock_infra.settings.RETRIEVAL_REFETCH_ENABLED = False
    mock_infra.settings.CITATION_VERIFY_ENABLED = False
    mock_infra.settings.SELF_RAG_ENABLED = False

    # Patch create_infra in the main module so lifespan gets the mock
    import main
    monkeypatch.setattr(main, "create_infra", lambda config: mock_infra)

    # Mock 用户存储，使 testuser 通过认证
    from core import auth
    monkeypatch.setattr(auth, "_load_users", lambda: {
        "testuser": {"username": "testuser", "password_hash": "x"}
    })


@pytest.fixture
def client():
    """提供 FastAPI 测试客户端"""
    import main
    return TestClient(main.app, raise_server_exceptions=False)


@pytest.fixture
def auth_headers():
    """提供有效 JWT 认证 headers"""
    from core.auth import create_access_token
    token = create_access_token({"sub": "testuser"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_files_10():
    """生成 10 个测试文件"""
    return [
        ("files", (f"test_{i}.txt", b"test content", "text/plain"))
        for i in range(10)
    ]


@pytest.fixture
def sample_files_25():
    """生成 25 个测试文件"""
    return [
        ("files", (f"test_{i}.txt", b"test content", "text/plain"))
        for i in range(25)
    ]


@pytest.fixture
def sample_files_101():
    """生成 101 个测试文件"""
    return [
        ("files", (f"test_{i}.txt", b"test content", "text/plain"))
        for i in range(101)
    ]
