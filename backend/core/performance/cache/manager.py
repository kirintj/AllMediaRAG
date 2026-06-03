import logging
from typing import Any, Optional
from .l1_cache import L1Cache

logger = logging.getLogger(__name__)


class CacheManager:
    """多级缓存管理器"""

    def __init__(self, config: dict):
        """
        Args:
            config: 缓存配置
                - use_cache: bool
                - l1_max_size: int
                - l1_ttl: int
                - use_redis: bool
                - redis_host: str (optional)
                - redis_port: int (optional)
        """
        self.enabled = config.get("use_cache", True)

        # L1缓存（必选）
        self.l1_cache = L1Cache(
            max_size=config.get("l1_max_size", 1000),
            ttl=config.get("l1_ttl", 300)
        )

        # L2缓存（可选，如Redis）
        self.l2_cache = None
        if config.get("use_redis", False):
            # TODO: 实现Redis缓存
            logger.info("Redis cache requested but not implemented yet")

        logger.info("CacheManager initialized (enabled=%s)", self.enabled)

    def get(self, key: str) -> Optional[Any]:
        """
        从缓存获取值

        Args:
            key: 缓存键

        Returns:
            缓存值
        """
        if not self.enabled:
            return None

        # L1缓存
        result = self.l1_cache.get(key)
        if result is not None:
            return result

        # L2缓存（如果启用）
        if self.l2_cache:
            result = self.l2_cache.get(key)
            if result is not None:
                # 回填L1
                self.l1_cache.set(key, result)
                return result

        return None

    def set(self, key: str, value: Any) -> None:
        """
        设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
        """
        if not self.enabled:
            return

        # L1缓存
        self.l1_cache.set(key, value)

        # L2缓存（如果启用）
        if self.l2_cache:
            self.l2_cache.set(key, value)

    def delete(self, key: str) -> bool:
        """
        删除缓存条目

        Args:
            key: 缓存键

        Returns:
            是否成功
        """
        result = self.l1_cache.delete(key)

        if self.l2_cache:
            self.l2_cache.delete(key)

        return result

    def clear(self) -> None:
        """清空所有缓存"""
        self.l1_cache.clear()

        if self.l2_cache:
            self.l2_cache.clear()

        logger.info("Cache cleared")
