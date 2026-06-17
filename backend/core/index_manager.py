import os
import json
import hashlib
import logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class IndexManager:
    """增量索引管理器：通过文件 Hash 追踪文档状态

    支持功能：
    - 计算文件 SHA-256 Hash
    - 对比已索引文档的 Hash
    - 检测新增/修改/删除的文档
    - 状态持久化到磁盘
    """

    # 支持的文件格式
    SUPPORTED_EXTENSIONS = {'.html', '.htm', '.txt', '.md', '.pdf', '.docx',
                            '.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif'}

    def __init__(self, state_file: str):
        """
        Args:
            state_file: 状态文件路径，如 ./chroma_db/index_state.json
        """
        self.state_file = state_file
        self._state: dict[str, dict] = {}  # {filename: {"hash": str, "chunk_count": int, "indexed_at": str}}
        self._load_state()

    def _load_state(self):
        """从磁盘加载索引状态"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    self._state = json.load(f)
                logger.info("Loaded index state: %d records from %s", len(self._state), self.state_file)
            else:
                self._state = {}
                logger.info("No existing index state found")
        except Exception as e:
            logger.warning("Failed to load index state: %s", e)
            self._state = {}

    def _save_state(self):
        """持久化索引状态"""
        try:
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self._state, f, ensure_ascii=False, indent=2)
            logger.debug("Saved index state: %d records", len(self._state))
        except Exception as e:
            logger.warning("Failed to save index state: %s", e)

    @staticmethod
    def compute_file_hash(file_path: str) -> str:
        """计算文件 SHA-256 Hash

        Args:
            file_path: 文件路径

        Returns:
            SHA-256 哈希值（十六进制字符串）
        """
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def get_indexed_hash(self, filename: str) -> Optional[str]:
        """获取已索引文件的 Hash

        Args:
            filename: 文件名

        Returns:
            已索引的 Hash，若不存在返回 None
        """
        entry = self._state.get(filename)
        return entry["hash"] if entry else None

    def needs_update(self, file_path: str) -> bool:
        """判断文件是否需要更新索引

        Args:
            file_path: 文件路径

        Returns:
            True 表示需要更新（新增或修改）
        """
        filename = os.path.basename(file_path)
        current_hash = self.compute_file_hash(file_path)
        indexed_hash = self.get_indexed_hash(filename)
        return current_hash != indexed_hash

    def record_indexed(self, filename: str, file_hash: str, chunk_count: int):
        """记录已索引文件的状态

        Args:
            filename: 文件名
            file_hash: 文件 Hash
            chunk_count: 分块数量
        """
        self._state[filename] = {
            "hash": file_hash,
            "chunk_count": chunk_count,
            "indexed_at": datetime.now().isoformat(),
        }
        self._save_state()

    def remove_record(self, filename: str):
        """删除记录

        Args:
            filename: 文件名
        """
        if filename in self._state:
            del self._state[filename]
            self._save_state()
            logger.info("Removed index record: %s", filename)

    def get_all_records(self) -> dict:
        """获取所有记录"""
        return dict(self._state)

    def get_record_count(self) -> int:
        """获取记录数量"""
        return len(self._state)

    def detect_changes(self, data_dir: str) -> dict:
        """扫描目录，检测变更

        Args:
            data_dir: 数据目录路径

        Returns:
            {"added": [str], "modified": [str], "deleted": [str], "unchanged": [str]}
        """
        result = {
            "added": [],
            "modified": [],
            "deleted": [],
            "unchanged": []
        }

        # 1. 扫描 data_dir 下所有支持的文件
        current_files = {}
        if os.path.exists(data_dir):
            for filename in os.listdir(data_dir):
                ext = os.path.splitext(filename)[1].lower()
                if ext in self.SUPPORTED_EXTENSIONS:
                    file_path = os.path.join(data_dir, filename)
                    if os.path.isfile(file_path):
                        try:
                            current_files[filename] = self.compute_file_hash(file_path)
                        except Exception as e:
                            logger.warning("Failed to compute hash for %s: %s", filename, e)

        # 2. 对比 _state 中的记录
        indexed_files = set(self._state.keys())
        current_file_set = set(current_files.keys())

        # 新增：当前存在但未索引
        for filename in current_file_set - indexed_files:
            result["added"].append(filename)

        # 删除：已索引但当前不存在
        for filename in indexed_files - current_file_set:
            result["deleted"].append(filename)

        # 修改/未变：两边都存在，对比 Hash
        for filename in indexed_files & current_file_set:
            if current_files[filename] != self._state[filename]["hash"]:
                result["modified"].append(filename)
            else:
                result["unchanged"].append(filename)

        logger.info("Change detection: added=%d, modified=%d, deleted=%d, unchanged=%d",
                    len(result["added"]), len(result["modified"]),
                    len(result["deleted"]), len(result["unchanged"]))

        return result
