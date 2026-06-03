import pytest
import os
import importlib
from unittest.mock import patch

def test_advanced_config_default_values():
    """测试高级配置的默认值"""
    from core.advanced_config import AdvancedRAGConfig

    config = AdvancedRAGConfig()

    # 查询扩展配置
    assert config.USE_HYDE is True
    assert config.MULTI_QUERY_ENABLED is True
    assert config.MULTI_QUERY_COUNT == 3

    # 重排序配置
    assert config.RERANK_STRATEGY == "cohere"
    assert config.RERANK_TOP_K == 20
    assert config.RERANK_TIMEOUT_MS == 250

    # 缓存配置
    assert config.USE_CACHE is True
    assert config.CACHE_L1_MAX_SIZE == 1000
    assert config.SEMANTIC_CACHE_THRESHOLD == 0.95

def test_advanced_config_from_env():
    """测试从环境变量加载配置"""
    with patch.dict(os.environ, {
        'COHERE_API_KEY': 'test-key-123',
        'RERANK_STRATEGY': 'bge',
        'USE_REDIS': 'true'
    }):
        import core.advanced_config
        importlib.reload(core.advanced_config)
        from core.advanced_config import AdvancedRAGConfig
        config = AdvancedRAGConfig()

        assert config.COHERE_API_KEY == 'test-key-123'
        assert config.RERANK_STRATEGY == 'bge'
        assert config.USE_REDIS is True
