"""共享测试 fixtures

提供 mock 引擎、测试客户端和认证 headers，
供所有 API 集成测试使用。
"""
import sys
import os
from pathlib import Path
from unittest.mock import MagicMock

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

    同时 mock 用户存储，确保 testuser 可通过 JWT 认证。
    """
    mock_engine = MagicMock()
    mock_engine.ingest_document = MagicMock(return_value=5)
    mock_engine.delete_by_source = MagicMock()
    mock_engine.delete_all = MagicMock()
    mock_engine.vector_store = MagicMock()
    mock_engine.vector_store.get_all_sources = MagicMock(return_value=[])
    mock_engine.vector_store.get_document_count = MagicMock(return_value=0)
    mock_engine.get_index_stats = MagicMock(return_value={
        "indexed_documents": 0,
        "vector_count": 0,
        "bm25_ready": False,
    })

    mock_config = MagicMock()
    mock_config.DATA_DIR = "/tmp/test_data_dir"

    # 导入 main 并注入 mock
    import main
    monkeypatch.setattr(main, "rag_engine", mock_engine)
    from api import documents as docs_module
    docs_module.set_engine(mock_engine, mock_config)

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
