import pytest
import time

def test_l1_cache_set_and_get():
    """测试L1缓存的设置和获取"""
    from core.performance.cache.l1_cache import L1Cache

    cache = L1Cache(max_size=100, ttl=60)

    cache.set("key1", {"data": "value1"})
    result = cache.get("key1")

    assert result is not None
    assert result["data"] == "value1"

def test_l1_cache_expiration():
    """测试L1缓存过期"""
    from core.performance.cache.l1_cache import L1Cache

    cache = L1Cache(max_size=100, ttl=1)  # 1秒过期

    cache.set("key1", {"data": "value1"})
    time.sleep(1.1)
    result = cache.get("key1")

    assert result is None

def test_l1_cache_eviction():
    """测试L1缓存淘汰"""
    from core.performance.cache.l1_cache import L1Cache

    cache = L1Cache(max_size=2, ttl=60)

    cache.set("key1", "value1")
    cache.set("key2", "value2")
    cache.set("key3", "value3")  # 应该淘汰key1

    assert cache.get("key1") is None
    assert cache.get("key2") is not None
    assert cache.get("key3") is not None

def test_l1_cache_delete():
    """测试L1缓存删除"""
    from core.performance.cache.l1_cache import L1Cache

    cache = L1Cache(max_size=100, ttl=60)

    cache.set("key1", "value1")
    assert cache.delete("key1") is True
    assert cache.get("key1") is None
    assert cache.delete("nonexistent") is False

def test_cache_manager_set_and_get():
    """测试缓存管理器设置和获取"""
    from core.performance.cache.manager import CacheManager

    config = {
        "use_cache": True,
        "l1_max_size": 100,
        "l1_ttl": 60,
        "use_redis": False
    }

    cache = CacheManager(config)

    cache.set("query1", {"results": [1, 2, 3]})
    result = cache.get("query1")

    assert result is not None
    assert result["results"] == [1, 2, 3]

def test_cache_manager_disabled():
    """测试缓存禁用"""
    from core.performance.cache.manager import CacheManager

    config = {
        "use_cache": False,
        "l1_max_size": 100,
        "l1_ttl": 60,
        "use_redis": False
    }

    cache = CacheManager(config)

    cache.set("query1", {"results": [1, 2, 3]})
    result = cache.get("query1")

    assert result is None

def test_cache_manager_clear():
    """测试缓存清空"""
    from core.performance.cache.manager import CacheManager

    config = {
        "use_cache": True,
        "l1_max_size": 100,
        "l1_ttl": 60,
        "use_redis": False
    }

    cache = CacheManager(config)

    cache.set("key1", "value1")
    cache.set("key2", "value2")
    cache.clear()

    assert cache.get("key1") is None
    assert cache.get("key2") is None
