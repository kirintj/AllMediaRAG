import logging
from collections import OrderedDict

import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# BGE-M3 原生最大 token 长度
_MAX_TOKENS = 8192
# 粗估：中文平均 ~2 字符/token，留 10% 余量
_MAX_CHARS = int(_MAX_TOKENS * 2 * 0.9)  # ~14745


class EmbeddingService:
    """Embedding 服务：加载 BGE-M3 模型，提供向量编码接口

    特性：
    - 延迟加载模型，首次使用时才加载（避免启动阻塞）
    - 自动检测 GPU，有 CUDA 时使用 GPU + FP16 加速
    - LRU 缓存避免重复编码
    - 长文本自动截断到模型最大长度
    """

    def __init__(self, model_path: str, cache_size: int = 2048):
        """
        Args:
            model_path: 模型路径或 HuggingFace 模型 ID
            cache_size: embedding LRU 缓存大小，0 禁用
        """
        self._model_path = model_path
        self._model = None
        self._device = None
        self._loaded = False

        # LRU 缓存
        self._cache: OrderedDict[str, list[float]] = OrderedDict()
        self._cache_size = cache_size
        self._cache_hits = 0
        self._cache_misses = 0

    @property
    def model(self):
        """延迟加载模型（首次使用时才加载）"""
        if self._model is None:
            self._load_model()
        return self._model

    def _load_model(self):
        """实际加载模型（内部方法）"""
        import torch

        # GPU 自动检测
        if torch.cuda.is_available():
            self._device = "cuda"
            dtype = torch.float16
            logger.info("Embedding: loading GPU model (%s), FP16", torch.cuda.get_device_name(0))
        else:
            self._device = "cpu"
            dtype = torch.float32
            logger.info("Embedding: loading CPU model, FP32")

        logger.info("Loading embedding model from: %s ...", self._model_path)
        self._model = SentenceTransformer(self._model_path, device=self._device)
        self._model.to(dtype=dtype)
        self._loaded = True
        logger.info("Embedding model loaded successfully")

    def encode(self, texts: list[str], show_progress: bool = False) -> list[list[float]]:
        """批量编码文本为向量（带缓存）

        Args:
            texts: 文本列表
            show_progress: 是否显示进度条（大批量导入时使用）

        Returns:
            向量列表（与输入等长、等序）
        """
        if not texts:
            return []

        # 确保模型已加载
        _ = self.model

        results: list[list[float] | None] = [None] * len(texts)
        to_encode_idx: list[int] = []
        to_encode_text: list[str] = []

        # 查缓存
        for i, text in enumerate(texts):
            truncated = self._truncate(text)
            cached = self._cache_get(truncated)
            if cached is not None:
                results[i] = cached
            else:
                to_encode_idx.append(i)
                to_encode_text.append(truncated)

        # 批量编码未命中部分
        if to_encode_text:
            embeddings = self.model.encode(
                to_encode_text,
                normalize_embeddings=True,
                show_progress_bar=show_progress and len(to_encode_text) > 10,
                batch_size=64,
            )
            for idx, emb in zip(to_encode_idx, embeddings):
                vec = emb.tolist()
                self._cache_put(to_encode_text[to_encode_idx.index(idx)], vec)
                results[idx] = vec

        return results  # type: ignore

    def encode_single(self, text: str) -> list[float]:
        """编码单条文本（带缓存）

        Args:
            text: 单条文本

        Returns:
            向量
        """
        # 确保模型已加载
        _ = self.model

        truncated = self._truncate(text)
        cached = self._cache_get(truncated)
        if cached is not None:
            return cached

        embedding = self.model.encode(truncated, normalize_embeddings=True)
        vec = embedding.tolist()
        self._cache_put(truncated, vec)
        return vec

    @staticmethod
    def _truncate(text: str) -> str:
        """截断超长文本到模型最大长度（粗估 token 数）"""
        if len(text) > _MAX_CHARS:
            return text[:_MAX_CHARS]
        return text

    def _cache_get(self, key: str) -> list[float] | None:
        """从 LRU 缓存获取"""
        if self._cache_size <= 0:
            return None
        if key in self._cache:
            self._cache.move_to_end(key)
            self._cache_hits += 1
            return self._cache[key]
        self._cache_misses += 1
        return None

    def _cache_put(self, key: str, value: list[float]) -> None:
        """写入 LRU 缓存"""
        if self._cache_size <= 0:
            return
        if key in self._cache:
            self._cache.move_to_end(key)
            return
        while len(self._cache) >= self._cache_size:
            self._cache.popitem(last=False)
        self._cache[key] = value

    def cache_stats(self) -> dict:
        """返回缓存统计信息"""
        total = self._cache_hits + self._cache_misses
        return {
            "size": len(self._cache),
            "max_size": self._cache_size,
            "hits": self._cache_hits,
            "misses": self._cache_misses,
            "hit_rate": self._cache_hits / total if total > 0 else 0.0,
        }
