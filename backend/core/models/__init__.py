# 为什么将 DocumentRegion 作为包的唯一公开导出：
# 消费方（VLMExtractor、RegionChunker）只需要这一个类型，
# 通过 __all__ 限制导出可以避免内部实现细节泄漏到外部导入路径。
from .document_region import DocumentRegion

__all__ = ["DocumentRegion"]
