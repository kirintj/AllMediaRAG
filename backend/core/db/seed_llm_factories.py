"""预置模型厂商数据"""
from __future__ import annotations

from sqlalchemy.orm import Session

from core.db.llm_models import LLMFactories

FACTORIES = [
    {"name": "OpenAI", "tags": "LLM,TEXT EMBEDDING,RERANK,CV,ASR,TTS", "description": "GPT-4o, text-embedding-3, Whisper, DALL-E"},
    {"name": "Ollama", "tags": "LLM,TEXT EMBEDDING,CV", "description": "本地部署: Llama3, Qwen2, Mistral, LLaVA"},
    {"name": "DeepSeek", "tags": "LLM", "description": "DeepSeek-V3, DeepSeek-R1"},
    {"name": "Azure-OpenAI", "tags": "LLM,TEXT EMBEDDING,CV,ASR,TTS", "description": "Azure OpenAI Service"},
    {"name": "Tongyi-Qianwen", "tags": "LLM,TEXT EMBEDDING,RERANK,CV,ASR,TTS", "description": "通义千问全系列"},
    {"name": "Zhipu", "tags": "LLM,TEXT EMBEDDING,RERANK,CV", "description": "智谱 GLM 系列"},
    {"name": "SILICONFLOW", "tags": "LLM,TEXT EMBEDDING,RERANK,ASR,TTS", "description": "硅基流动云推理"},
    {"name": "Anthropic", "tags": "LLM,CV", "description": "Claude 系列"},
    {"name": "Gemini", "tags": "LLM,TEXT EMBEDDING,CV", "description": "Google Gemini 系列"},
    {"name": "Cohere", "tags": "LLM,TEXT EMBEDDING,RERANK", "description": "Command, Embed, Rerank"},
    {"name": "Jina", "tags": "TEXT EMBEDDING,RERANK", "description": "Jina Embeddings, Reranker"},
    {"name": "NVIDIA", "tags": "LLM,TEXT EMBEDDING,RERANK,CV", "description": "NVIDIA NIM 推理"},
    {"name": "Mistral", "tags": "LLM,TEXT EMBEDDING", "description": "Mistral, Mixtral 系列"},
    {"name": "Groq", "tags": "LLM", "description": "Groq LPU 推理"},
    {"name": "Moonshot", "tags": "LLM", "description": "月之暗面 Kimi"},
    {"name": "xAI", "tags": "LLM", "description": "Grok 系列"},
    {"name": "Bedrock", "tags": "LLM,TEXT EMBEDDING,RERANK", "description": "AWS Bedrock"},
    {"name": "TogetherAI", "tags": "LLM,TEXT EMBEDDING,RERANK", "description": "Together AI 推理"},
    {"name": "StepFun", "tags": "LLM", "description": "阶跃星辰"},
    {"name": "OpenRouter", "tags": "LLM", "description": "OpenRouter 路由"},
    {"name": "DeepInfra", "tags": "LLM", "description": "DeepInfra 推理"},
    {"name": "BaiduYiyan", "tags": "LLM,TEXT EMBEDDING", "description": "百度文心一言"},
    {"name": "VolcEngine", "tags": "LLM,TEXT EMBEDDING", "description": "火山引擎"},
    {"name": "PaddleOCR", "tags": "OCR", "description": "百度 PaddleOCR"},
    {"name": "Tesseract", "tags": "OCR", "description": "Google Tesseract OCR"},
    {"name": "FunASR", "tags": "ASR", "description": "阿里达摩院 FunASR"},
    {"name": "HuggingFace", "tags": "TEXT EMBEDDING,RERANK", "description": "HuggingFace 模型"},
    {"name": "BGE", "tags": "RERANK", "description": "BAAI BGE Reranker"},
    {"name": "VLM", "tags": "OCR", "description": "视觉语言模型 OCR"},
]


def seed_factories(session: Session) -> int:
    """预置厂商数据（幂等）

    Returns:
        新增条数；已全部存在时返回 0。
    """
    existing = {r.name for r in session.query(LLMFactories.name).all()}
    added = 0
    for f in FACTORIES:
        if f["name"] not in existing:
            session.add(LLMFactories(**f))
            added += 1
    if added:
        session.commit()
    return added
