import time
import threading
from typing import Any, Optional
from collections import OrderedDict


class L1Cache:
    """L1内存缓存（线程安全）"""

    def __init__(self, max_size: int = 1000, ttl: int = 300):
        """
        Args:
            max_size: 最大缓存条目数
            ttl: 默认生存时间（秒）
        """
        self.max_size = max_size
        self.ttl = ttl
        self.cache: OrderedDict = OrderedDict()
        self.timestamps: dict = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值

        Args:
            key: 缓存键

        Returns:
            缓存值，如果不存在或过期则返回None
        """
        with self._lock:
            if key not in self.cache:
                return None

            # 检查是否过期
            if self._is_expired(key):
                self._remove(key)
                return None

            # 移到最前面（LRU）
            self.cache.move_to_end(key)

            return self.cache[key]

    def set(self, key: str, value: Any, ttl: int = None) -> None:
        """
        设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 可选的 per-key 生存时间（秒），为 None 时使用默认 ttl
        """
        with self._lock:
            # 如果已存在，先删除
            if key in self.cache:
                self._remove(key)

            # 检查是否需要淘汰
            while len(self.cache) >= self.max_size:
                self._evict()

            # 添加新条目
            self.cache[key] = value
            self.timestamps[key] = (time.time(), ttl)

    def delete(self, key: str) -> bool:
        """
        删除缓存条目

        Args:
            key: 缓存键

        Returns:
            是否成功删除
        """
        with self._lock:
            if key in self.cache:
                self._remove(key)
                return True
            return False

    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self.cache.clear()
            self.timestamps.clear()

    def _is_expired(self, key: str) -> bool:
        """检查是否过期（内部方法，调用方需已持锁）"""
        if key not in self.timestamps:
            return True

        created_at, key_ttl = self.timestamps[key]
        effective_ttl = key_ttl if key_ttl is not None else self.ttl
        elapsed = time.time() - created_at
        return elapsed > effective_ttl

    def _remove(self, key: str) -> None:
        """删除条目"""
        if key in self.cache:
            del self.cache[key]
        if key in self.timestamps:
            del self.timestamps[key]

    def size(self) -> int:
        """返回当前缓存条目数"""
        return len(self.cache)

    def _evict(self) -> None:
        """淘汰最久未使用的条目"""
        if self.cache:
            # 获取要淘汰的key
            key, _ = self.cache.popitem(last=False)
            # 删除对应的时间戳
            if key in self.timestamps:
                del self.timestamps[key]
