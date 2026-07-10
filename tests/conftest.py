"""根级测试配置。

注意：项目存在两套测试目录：
- tests/（本目录）— 单元测试 + 集成测试，从项目根目录运行
- backend/tests/ — 后端功能测试，从 backend/ 目录运行

TODO: 合并到 backend/tests/ 统一管理，消除 conftest 重复和发现配置冲突。
"""
import sys
import os

# Add backend directory to Python path so `from core.xxx import ...` works
_backend_dir = os.path.join(os.path.dirname(__file__), "..", "backend")
sys.path.insert(0, os.path.abspath(_backend_dir))
