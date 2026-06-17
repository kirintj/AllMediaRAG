import re
from .base import ChunkingStrategy, ChunkData


class ParentChildChunking(ChunkingStrategy):
    """Parent-Child 分层分块策略

    解决检索精度 vs 生成上下文完整性的矛盾：
    - Child chunks（小块）：用于向量检索和 BM25，提高匹配精度
    - Parent chunks（大块）：包含完整上下文，送给 LLM 生成

    工作原理：
    1. 先按句子切分文本
    2. 将句子分组为 child chunks（child_size 个句子）
    3. 每 3-5 个连续 child 合并为一个 parent
    4. 每个 child 的 metadata 中存储 parent_text，检索后替换
    """

    def __init__(
        self,
        child_sentences: int = 3,
        parent_groups: int = 4,
        overlap_sentences: int = 1,
    ):
        """
        Args:
            child_sentences: 每个 child chunk 包含的句子数（默认 3）
            parent_groups: 每个 parent 由多少个 child 合并（默认 4）
            overlap_sentences: child 之间的重叠句子数（默认 1）
        """
        self.child_sentences = child_sentences
        self.parent_groups = parent_groups
        self.overlap_sentences = overlap_sentences

    @property
    def name(self) -> str:
        return "parent_child"

    def split(self, text: str, metadata: dict = None) -> list[ChunkData]:
        """Parent-Child 分层切分

        返回的 ChunkData 列表中，每个元素代表一个 child chunk。
        metadata 中额外包含：
        - parent_id: 所属 parent 的唯一标识
        - parent_text: parent 的完整文本（用于替换）
        - chunk_type: "child"
        """
        base_metadata = metadata or {}
        sentences = self._split_sentences(text)

        if not sentences:
            return []

        # 句子太少，直接作为一个整体
        if len(sentences) <= self.child_sentences:
            return [ChunkData(
                content="\n".join(sentences),
                metadata={
                    **base_metadata,
                    "chunk_index": 0,
                    "chunk_type": "child",
                    "parent_id": f"{base_metadata.get('source', 'doc')}_p0",
                    "parent_text": "\n".join(sentences),
                },
            )]

        # Step 1: 创建 child chunks（带重叠）
        child_chunks = self._create_children(sentences, base_metadata)

        # Step 2: 将连续 child 分组为 parent
        self._assign_parents(child_chunks, base_metadata)

        return child_chunks

    def _split_sentences(self, text: str) -> list[str]:
        """按句子切分文本"""
        paragraphs = re.split(r"\n\n+", text)
        sentences = []
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            # 按中文句末标点和换行符切分，保留标点
            parts = re.split(r"(?<=[。？！\n])", para)
            for part in parts:
                part = part.strip()
                if part:
                    sentences.append(part)
        return sentences

    def _create_children(
        self, sentences: list[str], base_metadata: dict
    ) -> list[ChunkData]:
        """创建 child chunks（带重叠）"""
        children = []
        stride = max(1, self.child_sentences - self.overlap_sentences)
        source = base_metadata.get("source", "doc")

        for i in range(0, len(sentences), stride):
            end = min(i + self.child_sentences, len(sentences))
            chunk_sents = sentences[i:end]

            if not chunk_sents:
                break

            children.append(ChunkData(
                content="\n".join(chunk_sents),
                metadata={
                    **base_metadata,
                    "chunk_index": len(children),
                    "chunk_type": "child",
                    "_sent_start": i,  # 内部标记，用于 parent 分组
                    "_sent_end": end,
                },
            ))

            # 如果已经到达文本末尾，停止
            if end >= len(sentences):
                break

        return children

    def _assign_parents(
        self, children: list[ChunkData], base_metadata: dict
    ):
        """将连续 child 分组为 parent，将 parent_text 写入 child metadata"""
        source = base_metadata.get("source", "doc")
        parent_count = 0

        for i in range(0, len(children), self.parent_groups):
            group = children[i: i + self.parent_groups]
            if not group:
                break

            # 合并 group 中所有 child 的文本为 parent 文本
            # 去重重叠部分：只取每个 child 的独有部分
            parent_parts = []
            prev_end = -1
            for child in group:
                sent_start = child["metadata"]["_sent_start"]
                sent_end = child["metadata"]["_sent_end"]

                child_text = child["content"]

                # 如果有重叠且是同一个 parent 内的，去重
                if sent_start <= prev_end:
                    # 简单去重：按行去重
                    lines = child_text.split("\n")
                    new_lines = []
                    for line in lines:
                        if line not in parent_parts[-1] if parent_parts else True:
                            new_lines.append(line)
                    if new_lines:
                        parent_parts.append("\n".join(new_lines))
                else:
                    parent_parts.append(child_text)

                prev_end = sent_end

            parent_text = "\n".join(parent_parts)
            parent_id = f"{source}_p{parent_count}"

            # 将 parent 信息写入每个 child 的 metadata
            for child in group:
                child["metadata"]["parent_id"] = parent_id
                child["metadata"]["parent_text"] = parent_text

                # 清理内部标记
                child["metadata"].pop("_sent_start", None)
                child["metadata"].pop("_sent_end", None)

            parent_count += 1
