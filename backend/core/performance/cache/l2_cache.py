import logging
import pickle
from typing import Any, Optional

logger = logging.getLogger(__name__)


class L2Cache:
    """L2 Redis 缓存

    延迟初始化 Redis 连接，支持：
    - 二进制序列化（pickle）
    - TTL 过期
    - 按模式批量失效
    - 连接失败自动降级
    """

    def __init__(self, host: str = "localhost", port: int = 6379,
                 db: int = 0, ttl: int = 600, prefix: str = "rag:cache:"):
        """
        Args:
            host: Redis 主机
            port: Redis 端口
            db: Redis 数据库编号
            ttl: 默认过期时间（秒）
            prefix: 缓存键前缀
        """
        self.ttl = ttl
        self.prefix = prefix
        self._client = None
        self._init_failed = False
        self._host = host
        self._port = port
        self._db = db

    @property
    def client(self):
        """延迟初始化 Redis 连接"""
        if self._client is None and not self._init_failed:
            try:
                import redis
                self._client = redis.Redis(
                    host=self._host,
                    port=self._port,
                    db=self._db,
                    decode_responses=False,  # 二进制模式，用于 pickle
                    socket_connect_timeout=3,
                    socket_timeout=3,
                    retry_on_timeout=True,
                )
                # 测试连接
                self._client.ping()
                logger.info("Redis L2 cache connected: %s:%d", self._host, self._port)
            except Exception as e:
                logger.warning("Redis connection failed, L2 cache disabled: %s", e)
                self._init_failed = True
        return self._client

    def _make_key(self, key: str) -> str:
        """生成完整的缓存键"""
        return f"{self.prefix}{key}"

    def get(self, key: str) -> Optional[Any]:
        """从缓存获取值

        Args:
            key: 缓存键

        Returns:
            缓存的值，不存在或失败返回 None
        """
        if not self.client:
            return None

        try:
            data = self.client.get(self._make_key(key))
            if data is None:
                return None
            return pickle.loads(data)
        except Exception as e:
            logger.warning("Redis L2 get failed for key '%s': %s", key, e)
            return None

    def set(self, key: str, value: Any, ttl: int = None) -> None:
        """设置缓存值

        Args:
            key: 缓存键
            value: 要缓存的值
            ttl: 过期时间（秒），None 使用默认 TTL
        """
        if not self.client:
            return

        try:
            serialized = pickle.dumps(value)
            effective_ttl = ttl if ttl is not None else self.ttl
            self.client.setex(self._make_key(key), effective_ttl, serialized)
        except Exception as e:
            logger.warning("Redis L2 set failed for key '%s': %s", key, e)

    def delete(self, key: str) -> bool:
        """删除缓存

        Args:
            key: 缓存键

        Returns:
            是否删除成功
        """
        if not self.client:
            return False

        try:
            return bool(self.client.delete(self._make_key(key)))
        except Exception as e:
            logger.warning("Redis L2 delete failed for key '%s': %s", key, e)
            return False

    def clear(self) -> None:
        """清空所有缓存（带前缀的）"""
        if not self.client:
            return

        try:
            cursor = 0
            deleted = 0
            while True:
                cursor, keys = self.client.scan(cursor=cursor, match=f"{self.prefix}*", count=100)
                if keys:
                    deleted += self.client.delete(*keys)
                if cursor == 0:
                    break
            logger.info("Redis L2 cache cleared: %d keys", deleted)
        except Exception as e:
            logger.warning("Redis L2 clear failed: %s", e)

    def invalidate_by_pattern(self, pattern: str) -> int:
        """按模式批量失效缓存（用于文档变更时）

        Args:
            pattern: 匹配模式，如 "*document_name*"

        Returns:
            删除的键数量
        """
        if not self.client:
            return 0

        try:
            cursor = 0
            deleted = 0
            while True:
                cursor, keys = self.client.scan(cursor=cursor, match=f"{self.prefix}{pattern}", count=100)
                if keys:
                    deleted += self.client.delete(*keys)
                if cursor == 0:
                    break
            return deleted
        except Exception as e:
            logger.warning("Redis L2 invalidate failed: %s", e)
            return 0

    def invalidate_by_source(self, source: str) -> int:
        """按文档来源失效缓存

        Args:
            source: 文档来源名称

        Returns:
            删除的键数量
        """
        return self.invalidate_by_pattern(f"*{source}*")

    def get_stats(self) -> dict:
        """获取缓存统计信息"""
        if not self.client:
            return {"connected": False}

        try:
            info = self.client.info("keyspace")
            db_key = f"db{self._db}"
            db_info = info.get(db_key, {})
            return {
                "connected": True,
                "keys": db_info.get("keys", 0),
                "expires": db_info.get("expires", 0),
            }
        except Exception as e:
            logger.warning("Redis stats failed: %s", e)
            return {"connected": False, "error": str(e)}
