from .base import ChunkingStrategy, ChunkData


class RecursiveChunking(ChunkingStrategy):
    """递归切分策略

    按分隔符优先级逐级切分：先用最高优先级分隔符切分，
    若切片仍超过 chunk_size，则用下一级分隔符递归切分，
    直至满足大小要求。相邻 chunk 之间保留 chunk_overlap 字符重叠。
    """

    DEFAULT_SEPARATORS = ["\n\n", "\n", "。", "！", "？", ".", "!", "?", "；", ";", " "]

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        separators: list[str] = None,
    ):
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators if separators is not None else self.DEFAULT_SEPARATORS

    @property
    def name(self) -> str:
        return "recursive"

    def split(self, text: str, metadata: dict = None) -> list[ChunkData]:
        """递归切分文本"""
        base_metadata = metadata or {}
        if not text or not text.strip():
            return []

        raw_chunks = self._recursive_split(text, self.separators)
        chunks = []
        for i, chunk_text in enumerate(raw_chunks):
            chunk_text = chunk_text.strip()
            if chunk_text:
                chunks.append(ChunkData(
                    content=chunk_text,
                    metadata={**base_metadata, "chunk_index": len(chunks)},
                ))
        return chunks

    def _recursive_split(self, text: str, separators: list[str]) -> list[str]:
        """递归切分核心逻辑

        Args:
            text: 待切分文本
            separators: 当前可用的分隔符列表（按优先级排序）

        Returns:
            切分后的文本片段列表
        """
        if len(text) <= self.chunk_size:
            return [text]

        # 找到第一个出现在文本中的分隔符
        separator = ""
        remaining_separators = []
        for i, sep in enumerate(separators):
            if sep in text:
                separator = sep
                remaining_separators = separators[i + 1:]
                break

        # 没有可用分隔符，硬切
        if not separator:
            return self._hard_split(text)

        # 按分隔符切分
        parts = text.split(separator)
        merged = self._merge_parts(parts, separator)

        # 对仍然过长的片段递归处理
        result = []
        for part in merged:
            if len(part) > self.chunk_size and remaining_separators:
                sub_chunks = self._recursive_split(part, remaining_separators)
                result.extend(sub_chunks)
            else:
                result.append(part)
        return result

    def _merge_parts(self, parts: list[str], separator: str) -> list[str]:
        """将切分后的片段合并到 chunk_size 以内

        相邻片段之间用 separator 连接。当合并后长度接近 chunk_size 时
        开启新 chunk，并在新 chunk 开头保留 overlap 内容。
        """
        merged = []
        current = ""

        for part in parts:
            candidate = (current + separator + part) if current else part
            if len(candidate) <= self.chunk_size:
                current = candidate
            else:
                if current:
                    merged.append(current)
                # 如果单个 part 也超长，原样返回（交由上层递归处理）
                if len(part) > self.chunk_size:
                    merged.append(part)
                    current = ""
                else:
                    # 从上一个 chunk 尾部取 overlap 作为新 chunk 开头
                    if self.chunk_overlap > 0 and merged:
                        tail = merged[-1][-self.chunk_overlap:]
                        current = tail + separator + part
                        if len(current) > self.chunk_size:
                            # overlap 加上 part 还是太长，放弃 overlap
                            current = part
                    else:
                        current = part

        if current:
            merged.append(current)

        return merged

    def _hard_split(self, text: str) -> list[str]:
        """无分隔符时按 chunk_size 硬切"""
        result = []
        start = 0
        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            result.append(text[start:end])
            start = end - self.chunk_overlap if end < len(text) else end
        return result
