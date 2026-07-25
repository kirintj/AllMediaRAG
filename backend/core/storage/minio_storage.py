"""MinIO/S3 文件存储抽象"""
from __future__ import annotations

import io
import logging
from typing import BinaryIO

logger = logging.getLogger(__name__)


class MinIOStorage:
    """MinIO/S3 文件存储"""

    def __init__(self, endpoint: str, access_key: str, secret_key: str,
                 bucket: str, secure: bool = False):
        from minio import Minio
        self._client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
        )
        self._bucket = bucket
        self._ensure_bucket()

    def _ensure_bucket(self):
        if not self._client.bucket_exists(self._bucket):
            self._client.make_bucket(self._bucket)
            logger.info("Created MinIO bucket: %s", self._bucket)

    def upload(self, data: bytes | BinaryIO, object_key: str, content_type: str = "application/octet-stream") -> str:
        """上传文件到 MinIO

        Args:
            data: 文件内容（bytes 或 file-like）
            object_key: 对象键，如 {tenant_id}/{kb_id}/{doc_id}/{filename}
            content_type: MIME 类型

        Returns:
            object_key
        """
        if isinstance(data, bytes):
            data = io.BytesIO(data)
        length = data.seek(0, 2)
        data.seek(0)
        self._client.put_object(
            self._bucket, object_key, data, length=length,
            content_type=content_type,
        )
        logger.info("Uploaded to MinIO: %s/%s", self._bucket, object_key)
        return object_key

    def download(self, object_key: str) -> bytes:
        """从 MinIO 下载文件"""
        response = self._client.get_object(self._bucket, object_key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def download_to_file(self, object_key: str, local_path: str):
        """下载到本地文件"""
        self._client.fget_object(self._bucket, object_key, local_path)

    def delete(self, object_key: str):
        """删除文件"""
        self._client.remove_object(self._bucket, object_key)

    def delete_prefix(self, prefix: str):
        """删除前缀匹配的所有文件"""
        objects = self._client.list_objects(self._bucket, prefix=prefix, recursive=True)
        for obj in objects:
            self._client.remove_object(self._bucket, obj.object_name)

    def get_presigned_url(self, object_key: str, expires: int = 3600) -> str:
        """获取预签名 URL"""
        return self._client.presigned_get_object(self._bucket, object_key, expires=expires)
