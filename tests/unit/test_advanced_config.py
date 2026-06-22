import pytest
import os
from unittest.mock import patch


def test_unified_config_default_values():
    """Test that the unified config has correct defaults (merged from both configs)."""
    from core.config import AppSettings

    # Skip loading .env file to test pure code defaults
    settings = AppSettings(_env_file=None)

    # Query expansion
    assert settings.USE_HYDE is True
    assert settings.MULTI_QUERY_ENABLED is True
    assert settings.MULTI_QUERY_COUNT == 3

    # Reranking
    assert settings.RERANK_STRATEGY == "cohere"
    assert settings.RERANK_TOP_K == 40      # primary config value wins
    assert settings.RERANK_TIMEOUT_MS == 250

    # Cache
    assert settings.USE_CACHE is True
    assert settings.CACHE_L1_MAX_SIZE == 1000
    assert settings.SEMANTIC_CACHE_THRESHOLD == 0.95


def test_unified_config_from_env():
    """Test loading config values from environment variables."""
    with patch.dict(os.environ, {
        'COHERE_API_KEY': 'test-key-123',
        'RERANK_STRATEGY': 'bge',
        'USE_REDIS': 'true'
    }):
        from core.config import AppSettings
        settings = AppSettings()

        assert settings.COHERE_API_KEY == 'test-key-123'
        assert settings.RERANK_STRATEGY == 'bge'
        assert settings.USE_REDIS is True


def test_unified_config_invalid_int_env_falls_back_to_default():
    """Invalid integer env vars should fall back to Pydantic defaults."""
    with patch.dict(os.environ, {
        'MULTI_QUERY_COUNT': 'not_a_number',
        'RERANK_TOP_K': 'abc',
        'BATCH_SIZE': '',
    }):
        from core.config import AppSettings
        # Pydantic raises ValidationError for invalid int values
        with pytest.raises(Exception):
            AppSettings()


def test_unified_config_invalid_float_env_falls_back_to_default():
    """Invalid float env vars should raise a validation error."""
    with patch.dict(os.environ, {
        'SEMANTIC_CACHE_THRESHOLD': 'high',
        'ALERT_ERROR_RATE_THRESHOLD': 'NaN',
    }):
        from core.config import AppSettings
        with pytest.raises(Exception):
            AppSettings()


def test_unified_config_hyde_enabled_intents_is_tuple():
    """HYDE_ENABLED_INTENTS should be a tuple type."""
    from core.config import AppSettings

    settings = AppSettings()

    assert isinstance(settings.HYDE_ENABLED_INTENTS, tuple)
    assert settings.HYDE_ENABLED_INTENTS == ("analytical", "exploratory")


def test_advanced_config_alias():
    """The advanced_config alias should point to the same object as config."""
    from core.config import config, advanced_config

    assert config is advanced_config


def test_database_url_property_from_env():
    """database_url should prefer DATABASE_URL env var."""
    with patch.dict(os.environ, {
        'DATABASE_URL': 'postgresql://user:pass@host:5432/db',
    }):
        from core.config import AppSettings
        settings = AppSettings()
        assert settings.database_url == 'postgresql://user:pass@host:5432/db'


def test_database_url_property_assembled():
    """database_url should fall back to assembling from PG_* values."""
    env = {
        'DATABASE_URL': '',
        'PG_HOST': 'dbhost',
        'PG_PORT': '5433',
        'PG_USER': 'myuser',
        'PG_PASSWORD': 'mypass',
        'PG_DATABASE': 'mydb',
    }
    with patch.dict(os.environ, env, clear=False):
        from core.config import AppSettings
        settings = AppSettings()
        assert settings.database_url == 'postgresql://myuser:mypass@dbhost:5433/mydb'
