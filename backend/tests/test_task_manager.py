import pytest
import time
from core.task_manager import TaskManager, TaskStatus, TaskPhase


class TestTaskManager:
    """任务管理器测试"""

    def setup_method(self):
        """每个测试前创建新的管理器实例"""
        self.manager = TaskManager()

    def test_create_task(self):
        """测试创建任务"""
        task_id = self.manager.create_task(total=100)

        assert task_id is not None
        assert task_id.startswith("batch_")

        task = self.manager.get_task(task_id)
        assert task is not None
        assert task.total == 100
        assert task.status == TaskStatus.PENDING
        assert task.phase == TaskPhase.UPLOADING

    def test_get_nonexistent_task(self):
        """测试获取不存在的任务"""
        task = self.manager.get_task("nonexistent")
        assert task is None

    def test_update_upload_progress(self):
        """测试更新上传进度"""
        task_id = self.manager.create_task(total=100)

        self.manager.update_upload_progress(task_id, current=50)

        task = self.manager.get_task(task_id)
        assert task.upload_current == 50

    def test_add_upload_failure(self):
        """测试记录上传失败"""
        task_id = self.manager.create_task(total=100)

        self.manager.add_upload_failure(task_id, "bad.txt", "格式错误")

        task = self.manager.get_task(task_id)
        assert len(task.upload_failed) == 1
        assert task.upload_failed[0].filename == "bad.txt"
        assert task.upload_failed[0].error == "格式错误"

    def test_set_phase(self):
        """测试切换阶段"""
        task_id = self.manager.create_task(total=100)

        self.manager.set_phase(task_id, TaskPhase.INDEXING)

        task = self.manager.get_task(task_id)
        assert task.phase == TaskPhase.INDEXING

    def test_update_index_progress(self):
        """测试更新索引进度"""
        task_id = self.manager.create_task(total=100)

        self.manager.update_index_progress(task_id, current=30, success=28)

        task = self.manager.get_task(task_id)
        assert task.index_current == 30
        assert task.index_success == 28

    def test_add_index_failure(self):
        """测试记录索引失败"""
        task_id = self.manager.create_task(total=100)

        self.manager.add_index_failure(task_id, "bad.pdf", "解析失败", retries=3)

        task = self.manager.get_task(task_id)
        assert len(task.index_failed) == 1
        assert task.index_failed[0].filename == "bad.pdf"
        assert task.index_failed[0].retries == 3

    def test_complete_task(self):
        """测试完成任务"""
        task_id = self.manager.create_task(total=100)

        self.manager.complete_task(task_id)

        task = self.manager.get_task(task_id)
        assert task.status == TaskStatus.COMPLETED

    def test_fail_task(self):
        """测试标记任务失败"""
        task_id = self.manager.create_task(total=100)

        self.manager.fail_task(task_id, "磁盘空间不足")

        task = self.manager.get_task(task_id)
        assert task.status == TaskStatus.FAILED

    def test_has_running_task(self):
        """测试检查运行中任务"""
        # 初始状态没有运行中的任务
        assert self.manager.has_running_task() == False

        # 创建任务后应该有运行中的任务
        task_id = self.manager.create_task(total=100)
        assert self.manager.has_running_task() == True

        # 完成任务后应该没有运行中的任务
        self.manager.complete_task(task_id)
        assert self.manager.has_running_task() == False

    def test_snapshot(self):
        """测试生成进度快照"""
        task_id = self.manager.create_task(total=100)
        self.manager.update_upload_progress(task_id, current=50)
        self.manager.update_index_progress(task_id, current=30, success=28)

        task = self.manager.get_task(task_id)
        snapshot = task.snapshot()

        assert snapshot["task_id"] == task_id
        assert snapshot["status"] == "pending"
        assert snapshot["phase"] == "uploading"
        assert snapshot["total"] == 100
        assert snapshot["upload"]["current"] == 50
        assert snapshot["index"]["current"] == 30
        assert snapshot["index"]["success"] == 28

    def test_cleanup_old_tasks(self):
        """测试清理旧任务"""
        # 创建一个任务并手动设置旧时间
        task_id = self.manager.create_task(total=100)
        task = self.manager.get_task(task_id)
        task.started_at = time.time() - (25 * 3600)  # 25 小时前

        # 清理 24 小时前的任务
        self.manager.cleanup_old_tasks(max_age_hours=24)

        # 任务应该被删除
        assert self.manager.get_task(task_id) is None

    def test_thread_safety(self):
        """测试线程安全"""
        import threading

        results = []

        def create_tasks():
            for _ in range(10):
                task_id = self.manager.create_task(total=10)
                results.append(task_id)

        # 并发创建任务
        threads = [threading.Thread(target=create_tasks) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 应该有 50 个任务
        assert len(results) == 50

        # 所有任务都应该存在
        for task_id in results:
            assert self.manager.get_task(task_id) is not None
