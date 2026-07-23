"""Prompt 模板加载器

从 .md 文件加载 Jinja2 模板并渲染。
与 RAGFlow 的 template.py 对齐。
"""
from __future__ import annotations

import os
import logging
from jinja2 import Template

logger = logging.getLogger(__name__)

_PROMPT_DIR = os.path.join(os.path.dirname(__file__), "prompts")


def load_prompt(name: str, **kwargs) -> str:
    """加载并渲染 prompt 模板

    Args:
        name: 模板文件名（如 "keyword_prompt.md"）
        **kwargs: 模板变量

    Returns:
        渲染后的 prompt 字符串
    """
    path = os.path.join(_PROMPT_DIR, name)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Prompt template not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        template = Template(f.read())

    return template.render(**kwargs)
