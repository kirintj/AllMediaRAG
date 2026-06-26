"""ImageStore 原图存储测试

验证 save / load / dedup / cleanup 等核心行为。
"""
import base64
import os
from pathlib import Path

import pytest

# 1×1 像素透明 PNG，体积最小，适合单元测试
TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVQI12NgAAIABQAB"
    "Nl7BcQAAAABJRU5ErkJggg=="
)
TINY_PNG_B64 = base64.b64encode(TINY_PNG).decode("utf-8")


@pytest.fixture
def store(tmp_path):
    """每次测试使用独立临时目录，避免测试间互相污染。"""
    from core.image_store import ImageStore
    return ImageStore(str(tmp_path))


class TestSaveAndLoad:
    """保存后再加载，内容必须完全一致。"""

    def test_save_returns_images_prefix(self, store):
        """返回路径必须以 images/ 开头，供 Chroma 元数据引用。"""
        rel = store.save(TINY_PNG_B64)
        assert rel.startswith("images/")

    def test_file_exists_after_save(self, store, tmp_path):
        """save 写盘后文件必须存在于 base_dir/images/ 下。"""
        rel = store.save(TINY_PNG_B64)
        assert (tmp_path / rel).is_file()

    def test_load_roundtrip(self, store):
        """base64 经过 save→load 后内容不变。"""
        rel = store.save(TINY_PNG_B64)
        loaded = store.load_base64(rel)
        assert loaded == TINY_PNG_B64


class TestDedup:
    """相同内容重复保存应返回同一路径，避免磁盘浪费。"""

    def test_same_content_same_path(self, store):
        rel1 = store.save(TINY_PNG_B64)
        rel2 = store.save(TINY_PNG_B64)
        assert rel1 == rel2

    def test_file_written_only_once(self, store, tmp_path):
        """重复保存不应产生额外文件。"""
        store.save(TINY_PNG_B64)
        store.save(TINY_PNG_B64)
        images_dir = tmp_path / "images"
        assert len(list(images_dir.iterdir())) == 1


class TestLoadNonexistent:
    """加载不存在的文件应返回空字符串，而非抛异常。"""

    def test_returns_empty_string(self, store):
        assert store.load_base64("images/not_exist.png") == ""


class TestCleanupBySource:
    """按来源清理：删除对应图片文件并清除映射。"""

    def test_cleanup_deletes_file(self, store, tmp_path):
        """cleanup 后文件必须从磁盘移除。"""
        rel = store.save(TINY_PNG_B64, source="doc_1")
        assert (tmp_path / rel).is_file()
        store.cleanup_by_source("doc_1")
        assert not (tmp_path / rel).exists()

    def test_cleanup_removes_mapping(self, store):
        """cleanup 后内部映射应为空。"""
        store.save(TINY_PNG_B64, source="doc_1")
        store.cleanup_by_source("doc_1")
        assert "doc_1" not in store._source_images

    def test_cleanup_only_affects_target_source(self, store):
        """cleanup 不应影响其他来源的图片。"""
        rel_a = store.save(TINY_PNG_B64, source="doc_a")
        rel_b = store.save(TINY_PNG_B64, source="doc_b")
        store.cleanup_by_source("doc_a")
        # doc_b 的映射和文件仍应存在
        assert store.load_base64(rel_b) == TINY_PNG_B64
