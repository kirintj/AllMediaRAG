"""ImageStore — 原图本地存储与去重

VLM 提取的 figure 区域原图通过本模块落盘，
返回的相对路径写入 Chroma 元数据，供溯源时按需加载。
"""
import base64
import hashlib
from collections import defaultdict
from pathlib import Path
from typing import Dict


class ImageStore:
    """基于文件系统的原图存储，按内容哈希去重。"""

    def __init__(self, base_dir: str) -> None:
        # images 子目录单独隔离，便于整体迁移或清理
        self._base_dir = Path(base_dir)
        self._images_dir = self._base_dir / "images"
        self._images_dir.mkdir(parents=True, exist_ok=True)
        # 为什么用 set 而非 list：save() 需要检查路径是否已注册，
        # set 的 O(1) 查找避免了 list 在大量图片时的 O(n) 线性扫描。
        self._source_images: Dict[str, set] = defaultdict(set)

    def save(self, image_base64: str, source: str = "") -> str:
        """保存 base64 编码的图片，返回相对于 base_dir 的路径。

        相同内容只写盘一次（MD5 去重），重复调用直接返回已有路径。
        """
        raw = base64.b64decode(image_base64)
        content_hash = hashlib.md5(raw).hexdigest()[:12]
        ext = self._detect_ext(raw)
        filename = f"{content_hash}{ext}"
        rel_path = f"images/{filename}"
        abs_path = self._images_dir / filename

        # 去重：文件已存在则跳过写入，仅确保映射存在
        if not abs_path.exists():
            abs_path.write_bytes(raw)

        if source:
            # 为什么用 set.add：O(1) 插入，自动去重，无需手动检查
            self._source_images[source].add(rel_path)

        return rel_path

    def load_base64(self, relative_path: str) -> str:
        """按相对路径读取图片并返回 base64，文件不存在返回空字符串。

        调用方（如 API 层）无需处理 FileNotFoundError。
        """
        # 为什么做路径穿越检查：防止恶意输入如 "../../etc/passwd"
        # 读取 _base_dir 之外的文件。resolve() 将 .. 解析为绝对路径，
        # 再检查是否仍在 _base_dir 下。
        abs_path = (self._base_dir / relative_path).resolve()
        if not str(abs_path).startswith(str(self._base_dir.resolve())):
            return ""
        if not abs_path.is_file():
            return ""
        return base64.b64encode(abs_path.read_bytes()).decode("utf-8")

    def register_source_image(self, source: str, relative_path: str) -> None:
        """将已有图片路径关联到来源，供 cleanup_by_source 使用。

        典型场景：从已有向量库元数据恢复映射关系时调用。
        """
        self._source_images[source].add(relative_path)

    def cleanup_by_source(self, source: str) -> None:
        """删除指定来源的所有图片文件并清除映射。

        由 IngestionService 在删除向量数据前调用，
        确保原图不会成为孤立文件占用磁盘。
        """
        paths = self._source_images.pop(source, [])
        # 收集所有剩余来源仍在引用的路径，避免误删被其他来源共享的文件
        still_referenced: set = set()
        for remaining_paths in self._source_images.values():
            still_referenced.update(remaining_paths)
        for rel_path in paths:
            if rel_path in still_referenced:
                continue
            abs_path = self._base_dir / rel_path
            if abs_path.is_file():
                abs_path.unlink()

    @staticmethod
    def _detect_ext(image_bytes: bytes) -> str:
        """通过魔数检测图片格式，无法识别时回退到 .png。

        仅需前 4 字节即可区分常见格式，避免依赖文件扩展名。
        """
        if image_bytes[:4] == b"\x89PNG":
            return ".png"
        if image_bytes[:3] == b"\xff\xd8\xff":
            return ".jpg"
        if image_bytes[:3] == b"GIF":
            return ".gif"
        if image_bytes[:2] == b"BM":
            return ".bmp"
        return ".png"
