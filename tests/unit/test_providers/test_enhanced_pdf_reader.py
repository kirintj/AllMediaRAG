"""EnhancedPDFReader 单元测试

覆盖：supported_extensions、_table_to_markdown、init 无 provider、
read 不存在文件返回空字符串。
"""

import os
import sys
import importlib
import pytest


# ---------------------------------------------------------------------------
# 导入辅助：确保 backend 目录在 sys.path 中
# ---------------------------------------------------------------------------

_BACKEND_DIR = os.path.normpath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "backend",
))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

if "core" not in sys.modules:
    _core_spec = importlib.util.spec_from_file_location(
        "core", os.path.join(_BACKEND_DIR, "core", "__init__.py"),
        submodule_search_locations=[os.path.join(_BACKEND_DIR, "core")],
    )
    _core_mod = importlib.util.module_from_spec(_core_spec)
    sys.modules["core"] = _core_mod
    _core_spec.loader.exec_module(_core_mod)

if "core.providers" not in sys.modules:
    _providers_spec = importlib.util.spec_from_file_location(
        "core.providers",
        os.path.join(_BACKEND_DIR, "core", "providers", "__init__.py"),
        submodule_search_locations=[os.path.join(_BACKEND_DIR, "core", "providers")],
    )
    _providers_mod = importlib.util.module_from_spec(_providers_spec)
    sys.modules["core.providers"] = _providers_mod

    _base_path = os.path.join(_BACKEND_DIR, "core", "providers", "base.py")
    _base_spec = importlib.util.spec_from_file_location("core.providers.base", _base_path)
    _base_mod = importlib.util.module_from_spec(_base_spec)
    sys.modules["core.providers.base"] = _base_mod
    _base_spec.loader.exec_module(_base_mod)
    _providers_mod.base = _base_mod

if "core.providers.readers" not in sys.modules:
    _readers_spec = importlib.util.spec_from_file_location(
        "core.providers.readers",
        os.path.join(_BACKEND_DIR, "core", "providers", "readers", "__init__.py"),
        submodule_search_locations=[os.path.join(_BACKEND_DIR, "core", "providers", "readers")],
    )
    _readers_mod = importlib.util.module_from_spec(_readers_spec)
    sys.modules["core.providers.readers"] = _readers_mod


def _load_enhanced_pdf_reader():
    """加载 enhanced_pdf_reader 模块"""
    full_name = "core.providers.readers.enhanced_pdf_reader"
    if full_name in sys.modules:
        return sys.modules[full_name]
    module_path = os.path.join(
        _BACKEND_DIR, "core", "providers", "readers", "enhanced_pdf_reader.py",
    )
    spec = importlib.util.spec_from_file_location(full_name, module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = module
    spec.loader.exec_module(module)
    return module


def _get_enhanced_pdf_reader_class():
    mod = _load_enhanced_pdf_reader()
    return mod.EnhancedPDFReader


# ---------------------------------------------------------------------------
# EnhancedPDFReader 测试
# ---------------------------------------------------------------------------

class TestEnhancedPDFReader:
    """EnhancedPDFReader 基本功能测试"""

    def test_supported_extensions(self):
        """supported_extensions 应返回 [".pdf"]"""
        EnhancedPDFReader = _get_enhanced_pdf_reader_class()
        reader = EnhancedPDFReader()
        assert reader.supported_extensions() == [".pdf"]

    def test_init_without_providers(self):
        """无 provider 初始化不应报错"""
        EnhancedPDFReader = _get_enhanced_pdf_reader_class()
        reader = EnhancedPDFReader()
        assert reader.ocr is None
        assert reader.vlm is None

    def test_init_with_providers(self):
        """传入 provider 应正确绑定"""
        EnhancedPDFReader = _get_enhanced_pdf_reader_class()

        class MockOCR:
            pass

        class MockVLM:
            pass

        ocr = MockOCR()
        vlm = MockVLM()
        reader = EnhancedPDFReader(ocr_provider=ocr, vlm_provider=vlm)
        assert reader.ocr is ocr
        assert reader.vlm is vlm

    def test_read_nonexistent_file_returns_empty(self):
        """read 对不存在的文件应返回空字符串"""
        EnhancedPDFReader = _get_enhanced_pdf_reader_class()
        reader = EnhancedPDFReader()
        result = reader.read("/nonexistent/path/to/file.pdf")
        assert result == ""

    def test_can_handle(self):
        """can_handle 应正确识别 .pdf 扩展名"""
        EnhancedPDFReader = _get_enhanced_pdf_reader_class()
        reader = EnhancedPDFReader()
        assert reader.can_handle("report.pdf") is True
        assert reader.can_handle("report.PDF") is True
        assert reader.can_handle("report.txt") is False
        assert reader.can_handle("report.docx") is False

    def test_is_file_reader_subclass(self):
        """应是 FileReader 子类"""
        EnhancedPDFReader = _get_enhanced_pdf_reader_class()
        FileReader = sys.modules["core.providers.base"].FileReader
        assert issubclass(EnhancedPDFReader, FileReader)


# ---------------------------------------------------------------------------
# _table_to_markdown 测试
# ---------------------------------------------------------------------------

class TestTableToMarkdown:
    """_table_to_markdown 静态方法测试"""

    def test_basic_table(self):
        """正常表格应转换为 Markdown 格式"""
        EnhancedPDFReader = _get_enhanced_pdf_reader_class()
        table = [
            ["Name", "Age", "City"],
            ["Alice", "30", "Beijing"],
            ["Bob", "25", "Shanghai"],
        ]
        result = EnhancedPDFReader._table_to_markdown(table)

        assert "| Name | Age | City |" in result
        assert "| --- | --- | --- |" in result
        assert "| Alice | 30 | Beijing |" in result
        assert "| Bob | 25 | Shanghai |" in result

    def test_empty_table_returns_empty(self):
        """空表格应返回空字符串"""
        EnhancedPDFReader = _get_enhanced_pdf_reader_class()
        assert EnhancedPDFReader._table_to_markdown([]) == ""

    def test_empty_first_row_returns_empty(self):
        """第一行为空的表格应返回空字符串"""
        EnhancedPDFReader = _get_enhanced_pdf_reader_class()
        assert EnhancedPDFReader._table_to_markdown([[]]) == ""

    def test_none_cells_handled(self):
        """单元格为 None 时应转为空字符串"""
        EnhancedPDFReader = _get_enhanced_pdf_reader_class()
        table = [
            ["Col1", "Col2"],
            ["value", None],
            [None, "value2"],
        ]
        result = EnhancedPDFReader._table_to_markdown(table)

        assert "| value |  |" in result
        assert "|  | value2 |" in result

    def test_newlines_in_cells(self):
        """单元格内换行符应替换为空格"""
        EnhancedPDFReader = _get_enhanced_pdf_reader_class()
        table = [
            ["Header"],
            ["line1\nline2"],
        ]
        result = EnhancedPDFReader._table_to_markdown(table)
        assert "line1 line2" in result
        # 确认单元格内容中不包含原始换行（line1\nline2 变为 line1 line2）
        assert "line1\nline2" not in result

    def test_row_padding(self):
        """数据行列数少于表头时应补齐"""
        EnhancedPDFReader = _get_enhanced_pdf_reader_class()
        table = [
            ["A", "B", "C"],
            ["1", "2"],       # 只有两列
        ]
        result = EnhancedPDFReader._table_to_markdown(table)
        assert "| 1 | 2 |  |" in result

    def test_row_truncation(self):
        """数据行列数多于表头时应截断"""
        EnhancedPDFReader = _get_enhanced_pdf_reader_class()
        table = [
            ["A", "B"],
            ["1", "2", "extra"],
        ]
        result = EnhancedPDFReader._table_to_markdown(table)
        # extra 不应出现
        assert "extra" not in result
        assert "| 1 | 2 |" in result

    def test_single_row_table(self):
        """只有表头没有数据行应有效"""
        EnhancedPDFReader = _get_enhanced_pdf_reader_class()
        table = [["Col1", "Col2"]]
        result = EnhancedPDFReader._table_to_markdown(table)
        assert "| Col1 | Col2 |" in result
        assert "| --- | --- |" in result
        lines = result.strip().split("\n")
        assert len(lines) == 2  # 只有 header + separator

    def test_whitespace_trimmed(self):
        """单元格首尾空白应被去除"""
        EnhancedPDFReader = _get_enhanced_pdf_reader_class()
        table = [
            [" Name ", "  Age  "],
            ["  Alice  ", " 30 "],
        ]
        result = EnhancedPDFReader._table_to_markdown(table)
        assert "| Name | Age |" in result
        assert "| Alice | 30 |" in result


# ---------------------------------------------------------------------------
# 类常量测试
# ---------------------------------------------------------------------------

class TestConstants:
    """验证类常量正确设置"""

    def test_min_image_size(self):
        EnhancedPDFReader = _get_enhanced_pdf_reader_class()
        assert EnhancedPDFReader.MIN_IMAGE_SIZE == 100

    def test_scanned_threshold(self):
        EnhancedPDFReader = _get_enhanced_pdf_reader_class()
        assert EnhancedPDFReader.SCANNED_THRESHOLD == 50
