"""系统配置服务：数据库读写 + 热更新 AppSettings"""
import logging
from typing import Any
from sqlalchemy.orm import Session
from core.db.models import SystemSetting
from core.config import config

logger = logging.getLogger(__name__)

# ── 配置项定义 ──
SETTINGS_SCHEMA: dict[str, list[dict]] = {
    "llm": [
        {"key": "api_base", "field": "MIMO_API_BASE", "label": "API Base URL", "type": "text", "default": "https://api.siliconflow.cn/v1"},
        {"key": "api_key", "field": "MIMO_API_KEY", "label": "API Key", "type": "password", "default": ""},
        {"key": "model",   "field": "MIMO_MODEL",    "label": "模型名称",      "type": "text", "default": "mimo-v2.5"},
    ],
    "embedding": [
        {"key": "provider", "field": "EMBEDDING_PROVIDER", "label": "Embedding 提供商", "type": "select", "options": ["sentence-transformer", "siliconflow"], "default": "sentence-transformer"},
        {"key": "api_key",  "field": "SILICONFLOW_API_KEY", "label": "SiliconFlow API Key", "type": "password", "default": "", "show_if": {"provider": "siliconflow"}},
        {"key": "model",    "field": "SILICONFLOW_EMBEDDING_MODEL", "label": "模型名称", "type": "text", "default": "BAAI/bge-m3", "show_if": {"provider": "siliconflow"}},
    ],
    "reranking": [
        {"key": "strategy",          "field": "RERANK_STRATEGY",          "label": "Reranking 策略",       "type": "select", "options": ["cohere", "bge", "siliconflow"], "default": "cohere"},
        {"key": "cohere_api_key",    "field": "COHERE_API_KEY",           "label": "Cohere API Key",       "type": "password", "default": "", "show_if": {"strategy": "cohere"}},
        {"key": "model",             "field": "SILICONFLOW_RERANKER_MODEL", "label": "SiliconFlow 模型",  "type": "text", "default": "BAAI/bge-reranker-v2-m3", "show_if": {"strategy": "siliconflow"}},
    ],
    "rag": [
        {"key": "chunk_size",          "field": "CHUNK_SIZE",          "label": "分块大小",       "type": "number", "default": 512},
        {"key": "chunk_overlap",       "field": "CHUNK_OVERLAP",       "label": "分块重叠",       "type": "number", "default": 50},
        {"key": "top_k",               "field": "TOP_K",               "label": "检索 Top K",    "type": "number", "default": 5},
        {"key": "similarity_threshold","field": "SIMILARITY_THRESHOLD", "label": "相似度阈值",     "type": "number", "default": 0.5},
        {"key": "max_history_turns",   "field": "MAX_HISTORY_TURNS",   "label": "最大历史轮数",   "type": "number", "default": 5},
    ],
}

# db key → AppSettings 属性名映射（扁平化）
_KEY_TO_FIELD: dict[str, str] = {}
for _group, _items in SETTINGS_SCHEMA.items():
    for _item in _items:
        _KEY_TO_FIELD[f"{_group}.{_item['key']}"] = _item["field"]

# 需要类型转换的字段
_INT_FIELDS = {"CHUNK_SIZE", "CHUNK_OVERLAP", "TOP_K", "MAX_HISTORY_TURNS"}
_FLOAT_FIELDS = {"SIMILARITY_THRESHOLD"}


def _cast_value(field_name: str, raw: str) -> Any:
    """将字符串值转为 AppSettings 字段对应的 Python 类型"""
    if field_name in _INT_FIELDS:
        return int(raw)
    if field_name in _FLOAT_FIELDS:
        return float(raw)
    return raw


def seed_defaults(db: Session) -> None:
    """首次启动时将 schema 中的默认值写入数据库（仅写入尚不存在的 key）"""
    for group, items in SETTINGS_SCHEMA.items():
        for item in items:
            key = f"{group}.{item['key']}"
            exists = db.query(SystemSetting).filter_by(key=key).first()
            if not exists:
                current = getattr(config, item["field"], None)
                value = str(current) if current is not None else str(item.get("default", ""))
                db.add(SystemSetting(
                    key=key,
                    value=value,
                    group_name=group,
                    description=item["label"],
                ))
    db.commit()
    logger.info("Settings seed 完成")


def get_all_settings(db: Session) -> dict[str, list[dict]]:
    """读取所有设置，按 group 分组返回，API Key 返回掩码值"""
    rows = db.query(SystemSetting).all()
    result: dict[str, list[dict]] = {}
    for row in rows:
        meta = _get_meta(row.key)
        display_value = _mask_api_key(row.key, row.value) if meta and meta["type"] == "password" else row.value
        entry = {
            "key": row.key.split(".", 1)[1] if "." in row.key else row.key,
            "value": display_value,
            "description": row.description or "",
            "type": meta["type"] if meta else "text",
        }
        if meta and "options" in meta:
            entry["options"] = meta["options"]
        if meta and "show_if" in meta:
            entry["show_if"] = meta["show_if"]
        result.setdefault(row.group_name, []).append(entry)
    return result


def update_settings(db: Session, group: str, settings: dict[str, str]) -> None:
    """批量更新某个 group 的设置，并热更新 AppSettings 内存对象"""
    for key_suffix, value in settings.items():
        db_key = f"{group}.{key_suffix}"
        meta = _get_meta(db_key)

        # 如果提交的值为空且是 password 类型，跳过（保留原值）
        if meta and meta["type"] == "password" and value == "":
            continue

        row = db.query(SystemSetting).filter_by(key=db_key).first()
        if row:
            row.value = str(value)
        else:
            db.add(SystemSetting(
                key=db_key,
                value=str(value),
                group_name=group,
                description=meta["label"] if meta else key_suffix,
            ))

        # 热更新 AppSettings
        if meta:
            field_name = meta["field"]
            casted = _cast_value(field_name, str(value))
            try:
                object.__setattr__(config, field_name, casted)
                logger.info("热更新 %s = %s", field_name, "****" if meta["type"] == "password" else casted)
            except Exception as e:
                logger.warning("热更新 %s 失败: %s", field_name, e)

    db.commit()


def _get_meta(db_key: str) -> dict | None:
    """根据 db key（如 'llm.api_key'）查找 schema 元信息"""
    parts = db_key.split(".", 1)
    if len(parts) != 2:
        return None
    group, key = parts
    for item in SETTINGS_SCHEMA.get(group, []):
        if item["key"] == key:
            return item
    return None


def _mask_api_key(db_key: str, value: str) -> str:
    """掩码 API Key"""
    if not value or len(value) <= 8:
        return "****" if value else ""
    return value[:3] + "***" + value[-3:]
