import logging
from typing import Any, Optional
from .l1_cache import L1Cache

logger = logging.getLogger(__name__)


class CacheManager:
    """多级缓存管理器

    支持 L1 内存缓存（必须）和 L2 Redis 缓存（可选）。
    L2 缓存命中时自动回填 L1。
    """

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
                - l2_ttl: int (optional)
        """
        self.enabled = config.get("use_cache", True)

        # L1缓存（必选）
        self.l1_cache = L1Cache(
            max_size=config.get("l1_max_size", 1000),
            ttl=config.get("l1_ttl", 300)
        )

        # L2缓存（可选，Redis）
        self.l2_cache = None
        if config.get("use_redis", False):
            try:
                from .l2_cache import L2Cache
                self.l2_cache = L2Cache(
                    host=config.get("redis_host", "localhost"),
                    port=config.get("redis_port", 6379),
                    ttl=config.get("l2_ttl", 600),
                )
                logger.info("L2 Redis cache initialized")
            except Exception as e:
                logger.warning("L2 Redis cache initialization failed: %s", e)

        logger.info("CacheManager initialized (enabled=%s, l2=%s)",
                   self.enabled, self.l2_cache is not None)

    def get(self, key: str) -> Optional[Any]:
        """从缓存获取值

        优先 L1，L1 未命中则查 L2，L2 命中回填 L1。

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
        """设置缓存值

        同时写入 L1 和 L2（如果启用）。

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
        """删除缓存条目

        同时删除 L1 和 L2。

        Args:
            key: 缓存键

        Returns:
            是否成功
        """
        if not self.enabled:
            return False

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

    def invalidate_by_source(self, source: str) -> None:
        """按文档来源失效缓存

        文档变更时调用，清除与该文档相关的缓存。

        Args:
            source: 文档来源名称
        """
        if self.l2_cache:
            deleted = self.l2_cache.invalidate_by_source(source)
            if deleted > 0:
                logger.info("Invalidated %d cache entries for source: %s", deleted, source)

    def get_stats(self) -> dict:
        """获取缓存统计信息"""
        stats = {
            "enabled": self.enabled,
            "l1_size": self.l1_cache.size(),
        }

        if self.l2_cache:
            stats["l2"] = self.l2_cache.get_stats()

        return stats
