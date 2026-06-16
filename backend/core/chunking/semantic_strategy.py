import re
import numpy as np
from .base import ChunkingStrategy, ChunkData


class SemanticChunking(ChunkingStrategy):
    """基于语义相似度的切分策略

    通过计算相邻句子的 embedding 余弦相似度，
    在相似度低于动态阈值处进行切分。
    """

    def __init__(
        self,
        embedding_service=None,
        percentile: int = 25,
        min_sentences: int = 2,
        max_sentences: int = 20,
    ):
        self.embedding_service = embedding_service
        self.percentile = percentile
        self.min_sentences = min_sentences
        self.max_sentences = max_sentences

    def set_embedding_service(self, embedding_service):
        """延迟注入 embedding 服务（避免循环依赖）"""
        self.embedding_service = embedding_service

    @property
    def name(self) -> str:
        return "semantic"

    def split(self, text: str, metadata: dict = None) -> list[ChunkData]:
        """语义切分主流程

        句子切分 -> embedding -> 语义聚类 -> 返回 ChunkData 列表
        """
        base_metadata = metadata or {}
        sentences = self.split_into_sentences(text)
        if not sentences:
            return []

        # 句子太少，直接作为一个 chunk
        if len(sentences) <= self.min_sentences:
            return [ChunkData(
                content="\n".join(sentences),
                metadata={**base_metadata, "chunk_index": 0},
            )]

        # 尝试语义切分
        if self.embedding_service:
            sentence_embeddings = self.embedding_service.encode(sentences)
            sentence_groups = self.semantic_chunk(sentences, sentence_embeddings)
        else:
            # 无 embedding 服务时退化为固定分组
            sentence_groups = [
                list(range(i, min(i + self.min_sentences, len(sentences))))
                for i in range(0, len(sentences), self.min_sentences)
            ]

        chunks = []
        for group_indices in sentence_groups:
            chunk_text = "\n".join(sentences[i] for i in group_indices)
            if chunk_text.strip():
                chunks.append(ChunkData(
                    content=chunk_text,
                    metadata={**base_metadata, "chunk_index": len(chunks)},
                ))

        return chunks

    def split_into_sentences(self, text: str) -> list[str]:
        """将文本切分为句子

        按段落（双换行）拆分，再按中文句末标点和换行符切分。
        """
        paragraphs = re.split(r"\n\n+", text)
        sentences = []
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            parts = re.split(r"(?<=[。？！\n])", para)
            for part in parts:
                part = part.strip()
                if part:
                    sentences.append(part)
        return sentences

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """计算余弦相似度"""
        a_arr = np.array(a)
        b_arr = np.array(b)
        dot = np.dot(a_arr, b_arr)
        norm = np.linalg.norm(a_arr) * np.linalg.norm(b_arr)
        if norm == 0:
            return 0.0
        return float(dot / norm)

    def semantic_chunk(
        self, sentences: list[str], embeddings: list[list[float]]
    ) -> list[list[int]]:
        """基于语义相似度切分句子

        Args:
            sentences: 句子列表
            embeddings: 句子级 embedding 列表

        Returns:
            chunk 列表，每个 chunk 是句子索引的列表
        """
        if len(sentences) <= self.min_sentences:
            return [list(range(len(sentences)))]

        # 计算相邻句子的余弦相似度
        similarities = []
        for i in range(len(embeddings) - 1):
            sim = self._cosine_similarity(embeddings[i], embeddings[i + 1])
            similarities.append(sim)

        # 动态阈值：取百分位数
        threshold = float(np.percentile(similarities, self.percentile))

        # 低于阈值处切分
        chunks = []
        current_chunk = [0]
        for i, sim in enumerate(similarities):
            if sim < threshold:
                if len(current_chunk) >= self.min_sentences:
                    chunks.append(current_chunk)
                    current_chunk = [i + 1]
                else:
                    current_chunk.append(i + 1)
            else:
                current_chunk.append(i + 1)

            if len(current_chunk) >= self.max_sentences:
                chunks.append(current_chunk)
                current_chunk = []

        if current_chunk:
            chunks.append(current_chunk)

        return chunks
