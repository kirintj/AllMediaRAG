import sys
import os
import pytest

# Ensure backend is on the path
_backend_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "backend")
sys.path.insert(0, os.path.abspath(_backend_dir))

from core.chunking import (
    ChunkingStrategy,
    ChunkData,
    SemanticChunking,
    FixedSizeChunking,
    RecursiveChunking,
)


# ---- Helpers ----

def _make_long_text(sentences: int = 30) -> str:
    """生成包含多个句子的测试文本"""
    base = "这是第{}句话。"
    return "".join(base.format(i) for i in range(sentences))


# ---- SemanticChunking ----

class TestSemanticChunking:

    def test_empty_text(self):
        strategy = SemanticChunking()
        result = strategy.split("")
        assert result == []

    def test_name(self):
        strategy = SemanticChunking()
        assert strategy.name == "semantic"

    def test_split_basic(self):
        text = _make_long_text(10)
        strategy = SemanticChunking(min_sentences=2)
        result = strategy.split(text)
        assert len(result) >= 1
        for chunk in result:
            assert isinstance(chunk, dict)
            assert "content" in chunk
            assert "metadata" in chunk
            assert chunk["content"].strip() != ""

    def test_short_text_single_chunk(self):
        """单句文本应返回一个 chunk"""
        text = "这是一句话。"
        strategy = SemanticChunking(min_sentences=2)
        result = strategy.split(text)
        assert len(result) == 1
        assert result[0]["content"] == text

    def test_metadata_passthrough(self):
        text = _make_long_text(5)
        strategy = SemanticChunking(min_sentences=2)
        result = strategy.split(text, metadata={"source": "test.txt"})
        for chunk in result:
            assert chunk["metadata"]["source"] == "test.txt"
            assert "chunk_index" in chunk["metadata"]


# ---- FixedSizeChunking ----

class TestFixedSizeChunking:

    def test_empty_text(self):
        strategy = FixedSizeChunking(chunk_size=512, chunk_overlap=50)
        result = strategy.split("")
        assert result == []

    def test_name(self):
        strategy = FixedSizeChunking()
        assert strategy.name == "fixed_size"

    def test_split_basic(self):
        text = _make_long_text(50)
        strategy = FixedSizeChunking(chunk_size=100, chunk_overlap=20)
        result = strategy.split(text)
        assert len(result) > 1
        for chunk in result:
            assert chunk["content"].strip() != ""

    def test_chunk_size_respected(self):
        text = _make_long_text(100)
        strategy = FixedSizeChunking(chunk_size=80, chunk_overlap=0)
        result = strategy.split(text)
        # All chunks except possibly the last should be <= chunk_size
        for chunk in result[:-1]:
            assert len(chunk["content"]) <= 80

    def test_overlap_greater_than_size_raises(self):
        with pytest.raises(ValueError, match="chunk_overlap"):
            FixedSizeChunking(chunk_size=10, chunk_overlap=10)


# ---- RecursiveChunking ----

class TestRecursiveChunking:

    def test_empty_text(self):
        strategy = RecursiveChunking(chunk_size=512, chunk_overlap=50)
        result = strategy.split("")
        assert result == []

    def test_name(self):
        strategy = RecursiveChunking()
        assert strategy.name == "recursive"

    def test_split_basic(self):
        text = _make_long_text(50)
        strategy = RecursiveChunking(chunk_size=100, chunk_overlap=20)
        result = strategy.split(text)
        assert len(result) >= 1
        for chunk in result:
            assert chunk["content"].strip() != ""

    def test_respects_separators(self):
        """含多种分隔符的文本应按分隔符切分"""
        text = "段落一。\n\n段落二。\n\n段落三。"
        strategy = RecursiveChunking(chunk_size=20, chunk_overlap=0)
        result = strategy.split(text)
        assert len(result) >= 1
        contents = [c["content"] for c in result]
        # 每个 chunk 的长度应 <= chunk_size（除了可能的最后一段）
        for c in contents[:-1]:
            assert len(c) <= 20

    def test_overlap_greater_than_size_raises(self):
        with pytest.raises(ValueError, match="chunk_overlap"):
            RecursiveChunking(chunk_size=10, chunk_overlap=10)

    def test_metadata_passthrough(self):
        text = _make_long_text(5)
        strategy = RecursiveChunking(chunk_size=512, chunk_overlap=50)
        result = strategy.split(text, metadata={"source": "demo.md"})
        for chunk in result:
            assert chunk["metadata"]["source"] == "demo.md"
