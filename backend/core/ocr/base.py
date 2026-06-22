from abc import ABC, abstractmethod


class OCRProvider(ABC):
    """OCR 提供者抽象基类

    遵循 backend/core/reranking/base.py 的抽象模式，
    所有 OCR 实现必须继承此类。
    """

    @abstractmethod
    def extract_text(self, image_or_pdf_path: str) -> str:
        """从图片或扫描件 PDF 提取文字

        Args:
            image_or_pdf_path: 图片文件路径或 PDF 文件路径

        Returns:
            提取的文字内容
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """检查 OCR 提供者是否可用"""
        pass

    def _validate_path(self, path: str) -> bool:
        """验证文件路径是否存在"""
        import os
        return os.path.exists(path)
