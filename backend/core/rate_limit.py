"""API 速率限制模块

基于 slowapi 实现，使用内存存储（适合单实例部署）。
多实例部署时建议替换为 Redis 后端。
"""
import logging
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
