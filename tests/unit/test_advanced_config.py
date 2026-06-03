import pytest
import os
import sys
import importlib
from unittest.mock import patch


@pytest.fixture(autouse=True)
def _restore_advanced_config_module():
    """每个测试后恢复 advanced_config 模块的原始状态，避免 reload 污染后续测试。"""
    # 记录模块在测试前的状态
    module_key = "core.advanced_config"
    original_module = sys.modules.get(module_key)
    yield
    # 恢复：删除被 reload 污染的模块，重新加载原始版本
    if module_key in sys.modules:
        del sys.modules[module_key]
    if original_module is not None:
        sys.modules[module_key] = original_module


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


def test_advanced_config_invalid_int_env_falls_back_to_default():
    """非法整数环境变量应回退到默认值"""
    with patch.dict(os.environ, {
        'MULTI_QUERY_COUNT': 'not_a_number',
        'RERANK_TOP_K': 'abc',
        'BATCH_SIZE': '',
    }):
        import core.advanced_config
        importlib.reload(core.advanced_config)
        from core.advanced_config import AdvancedRAGConfig
        config = AdvancedRAGConfig()

        assert config.MULTI_QUERY_COUNT == 3
        assert config.RERANK_TOP_K == 20
        assert config.BATCH_SIZE == 32


def test_advanced_config_invalid_float_env_falls_back_to_default():
    """非法浮点数环境变量应回退到默认值"""
    with patch.dict(os.environ, {
        'SEMANTIC_CACHE_THRESHOLD': 'high',
        'ALERT_ERROR_RATE_THRESHOLD': 'NaN',
    }):
        import core.advanced_config
        importlib.reload(core.advanced_config)
        from core.advanced_config import AdvancedRAGConfig
        config = AdvancedRAGConfig()

        assert config.SEMANTIC_CACHE_THRESHOLD == 0.95
        assert config.ALERT_ERROR_RATE_THRESHOLD == 0.05


def test_advanced_config_hyde_enabled_intents_is_tuple():
    """HYDE_ENABLED_INTENTS 应为 tuple 类型"""
    from core.advanced_config import AdvancedRAGConfig

    config = AdvancedRAGConfig()

    assert isinstance(config.HYDE_ENABLED_INTENTS, tuple)
    assert config.HYDE_ENABLED_INTENTS == ("analytical", "exploratory")
