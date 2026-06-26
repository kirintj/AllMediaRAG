"""批量上传 API 测试

覆盖同步/异步模式切换、文件数量限制、空文件处理、
任务状态查询和不存在任务查询等场景。
"""
import pytest
from fastapi.testclient import TestClient


class TestBatchUpload:
    """批量上传 API 测试"""

    def test_sync_mode_small_batch(self, client, auth_headers, sample_files_10):
        """测试小批量同步处理（<20个文件）"""
        response = client.post(
            "/api/upload/batch",
            files=sample_files_10,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "sync"
        assert data["total"] == 10
        assert data["success"] == 10

    def test_async_mode_large_batch(self, client, auth_headers, sample_files_25):
        """测试大批量异步处理（>=20个文件）"""
        response = client.post(
            "/api/upload/batch",
            files=sample_files_25,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "async"
        assert "task_id" in data
        assert data["total"] == 25

    def test_file_count_limit(self, client, auth_headers, sample_files_101):
        """测试文件数量限制（100个）"""
        response = client.post(
            "/api/upload/batch",
            files=sample_files_101,
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert "最多上传 200 个文件" in response.json()["detail"]

    def test_empty_files(self, client, auth_headers):
        """测试空文件列表"""
        response = client.post(
            "/api/upload/batch",
            files=[],
            headers=auth_headers,
        )

        assert response.status_code == 422

    def test_query_task_status(self, client, auth_headers, sample_files_25):
        """测试查询任务进度"""
        response = client.post(
            "/api/upload/batch",
            files=sample_files_25,
            headers=auth_headers,
        )
        task_id = response.json()["task_id"]

        status_response = client.get(
            f"/api/upload/batch/status/{task_id}",
            headers=auth_headers,
        )

        assert status_response.status_code == 200
        data = status_response.json()
        assert data["task_id"] == task_id
        assert data["status"] in ["pending", "running", "completed"]

    def test_task_not_found(self, client, auth_headers):
        """测试查询不存在的任务"""
        response = client.get(
            "/api/upload/batch/status/nonexistent_task",
            headers=auth_headers,
        )

        assert response.status_code == 404
        assert "任务不存在" in response.json()["detail"]

    def test_single_file_size_limit(self, client, auth_headers):
        """测试单文件大小限制（10MB）"""
        large_content = b"x" * (11 * 1024 * 1024)
        files = [("files", ("large.txt", large_content, "text/plain"))]

        response = client.post(
            "/api/upload/batch",
            files=files,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        # 超大文件应被标记为失败
        assert data["failed"] == 1
        assert data["results"][0]["status"] == "failed"

    def test_total_size_limit(self, client, auth_headers):
        """测试总大小限制（500MB）"""
        files = [
            ("files", (f"large_{i}.txt", b"x" * (60 * 1024 * 1024), "text/plain"))
            for i in range(9)  # 9 * 60MB = 540MB
        ]

        response = client.post(
            "/api/upload/batch",
            files=files,
            headers=auth_headers,
        )

        assert response.status_code == 400

    def test_response_format_sync(self, client, auth_headers, sample_files_10):
        """测试同步响应格式包含 results 列表"""
        response = client.post(
            "/api/upload/batch",
            files=sample_files_10,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert isinstance(data["results"], list)
        assert len(data["results"]) == data["total"]
        for entry in data["results"]:
            assert "filename" in entry
            assert "status" in entry
            assert entry["status"] in ("success", "failed")

    def test_response_format_async(self, client, auth_headers, sample_files_25):
        """测试异步响应格式包含 message 字段"""
        response = client.post(
            "/api/upload/batch",
            files=sample_files_25,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "task_id" in data
