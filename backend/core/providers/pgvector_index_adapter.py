"""PostgreSQL 索引管理适配器

替代 IndexManager（读写 index_state.json），直接读写 documents 表。
对齐 IndexManager 的公共接口签名。
"""

import os
import hashlib
import logging
from typing import Optional
from datetime import datetime, timezone

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

from core.db.models import DocumentModel

logger = logging.getLogger(__name__)


class PgIndexManager:
    """PostgreSQL 索引管理器

    实现与 IndexManager 相同的公共方法，但底层读写 documents 表。
    """

    # 支持的文件格式（与 IndexManager 保持一致）
    SUPPORTED_EXTENSIONS = {'.html', '.htm', '.txt', '.md', '.pdf', '.docx',
                            '.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif'}

    def __init__(self, database_url: str = "", **kwargs):
        """初始化

        Args:
            database_url: PostgreSQL 连接 URL
        """
        if not database_url:
            raise ValueError("database_url is required for PgIndexManager")

        self._engine = create_engine(
            database_url,
            pool_size=2,
            max_overflow=5,
            pool_timeout=30,
            pool_recycle=1800,
            echo=False,
        )
        self._session_factory = sessionmaker(bind=self._engine, expire_on_commit=False)
        logger.info("PgIndexManager initialized")

    def _get_session(self):
        return self._session_factory()

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
        session = self._get_session()
        try:
            doc = session.query(DocumentModel.file_hash).filter_by(source=filename).first()
            return doc.file_hash if doc else None
        finally:
            session.close()

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
        session = self._get_session()
        try:
            doc = session.query(DocumentModel).filter_by(source=filename).first()
            if doc:
                doc.file_hash = file_hash
                doc.chunk_count = chunk_count
                doc.indexed_at = datetime.now(timezone.utc)
                doc.updated_at = datetime.now(timezone.utc)
            else:
                doc = DocumentModel(
                    source=filename,
                    file_hash=file_hash,
                    chunk_count=chunk_count,
                )
                session.add(doc)
            session.commit()
            logger.debug("Recorded index state: %s (hash=%s, chunks=%d)", filename, file_hash[:8], chunk_count)
        except Exception as e:
            session.rollback()
            logger.exception("Failed to record indexed: %s", filename)
            raise
        finally:
            session.close()

    def remove_record(self, filename: str):
        """删除记录

        Args:
            filename: 文件名
        """
        session = self._get_session()
        try:
            deleted = session.query(DocumentModel).filter_by(source=filename).delete()
            session.commit()
            if deleted:
                logger.info("Removed index record: %s", filename)
        except Exception as e:
            session.rollback()
            logger.exception("Failed to remove record: %s", filename)
            raise
        finally:
            session.close()

    def get_all_records(self) -> dict:
        """获取所有记录

        Returns:
            {filename: {"hash": str, "chunk_count": int, "indexed_at": str}}
        """
        session = self._get_session()
        try:
            docs = session.query(DocumentModel).all()
            state = {}
            for doc in docs:
                state[doc.source] = {
                    "hash": doc.file_hash,
                    "chunk_count": doc.chunk_count,
                    "indexed_at": doc.indexed_at.isoformat() if doc.indexed_at else "",
                }
            return state
        finally:
            session.close()

    def get_record_count(self) -> int:
        """获取记录数量"""
        session = self._get_session()
        try:
            return session.query(func.count(DocumentModel.id)).scalar()
        finally:
            session.close()

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
            "unchanged": [],
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

        # 2. 从数据库获取已索引文件
        indexed_state = self.get_all_records()
        indexed_files = set(indexed_state.keys())
        current_file_set = set(current_files.keys())

        # 新增
        for filename in current_file_set - indexed_files:
            result["added"].append(filename)

        # 删除
        for filename in indexed_files - current_file_set:
            result["deleted"].append(filename)

        # 修改/未变
        for filename in indexed_files & current_file_set:
            if current_files[filename] != indexed_state[filename]["hash"]:
                result["modified"].append(filename)
            else:
                result["unchanged"].append(filename)

        logger.info("Change detection: added=%d, modified=%d, deleted=%d, unchanged=%d",
                     len(result["added"]), len(result["modified"]),
                     len(result["deleted"]), len(result["unchanged"]))

        return result

    def close(self):
        """关闭数据库连接池"""
        if self._engine:
            self._engine.dispose()
            logger.info("PgIndexManager closed")
