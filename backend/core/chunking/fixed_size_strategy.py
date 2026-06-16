import re
from .base import ChunkingStrategy, ChunkData


class FixedSizeChunking(ChunkingStrategy):
    """按固定大小切分策略

    以 chunk_size 为窗口遍历文本，优先在句子边界处切分，
    并在相邻 chunk 之间保留 chunk_overlap 个字符的重叠。
    """

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50):
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    @property
    def name(self) -> str:
        return "fixed_size"

    def split(self, text: str, metadata: dict = None) -> list[ChunkData]:
        """按固定大小切分文本"""
        base_metadata = metadata or {}
        if not text or not text.strip():
            return []

        chunks = []
        start = 0
        text_len = len(text)

        while start < text_len:
            end = start + self.chunk_size

            if end < text_len:
                # 在 chunk_size 范围内找最后一个句子边界
                boundary = self._find_sentence_boundary(text, start, end)
                if boundary > start:
                    end = boundary

            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append(ChunkData(
                    content=chunk_text,
                    metadata={**base_metadata, "chunk_index": len(chunks)},
                ))

            # 下一个 chunk 的起始位置（带重叠）
            start = end - self.chunk_overlap if end < text_len else text_len

        return chunks

    def _find_sentence_boundary(self, text: str, start: int, end: int) -> int:
        """在 [start, end) 范围内从后向前查找句子边界"""
        search_text = text[start:end]
        # 查找最后一个句子终止符
        for pattern in ["。", "！", "？", "\n"]:
            idx = search_text.rfind(pattern)
            if idx > 0:
                return start + idx + len(pattern)
        return end
