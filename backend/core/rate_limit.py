"""API 速率限制模块

基于 slowapi 实现，使用内存存储（适合单实例部署）。
多实例部署时建议替换为 Redis 后端。
"""
import logging

# --- Patch starlette Config to read .env with UTF-8 encoding ---
# 中文 Windows 默认 GBK 编码无法解码含中文注释的 UTF-8 .env 文件，
# 导致 slowapi.Limiter 初始化时 UnicodeDecodeError。
# 在 slowapi 导入前打补丁，强制使用 UTF-8 读取 .env。
import starlette.config as _sc


def _read_file_utf8(self, path):
    """Read .env with UTF-8 encoding instead of system default (fixes GBK error on Chinese Windows)."""
    if not path:
        return {}
    try:
        file_path = _sc.Path(path)
    except Exception:
        return {}
    if not file_path.is_file():
        return {}
    result = {}
    with open(file_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip("'\"")
                result[key.lower()] = value
    return result


_sc.Config._read_file = _read_file_utf8
# --- End patch ---

from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)

# 使用客户端 IP 作为限流 key
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["120/minute"],
    storage_uri="memory://",
)

# 各端点的限流策略
RATE_LIMIT_CHAT = "30/minute"       # LLM 调用成本高
RATE_LIMIT_UPLOAD = "30/minute"     # 文档上传
RATE_LIMIT_LOGIN = "10/minute"      # 防暴力破解
RATE_LIMIT_REGISTER = "5/minute"    # 注册更严格
RATE_LIMIT_BATCH_UPLOAD = "5/minute"  # 批量上传
