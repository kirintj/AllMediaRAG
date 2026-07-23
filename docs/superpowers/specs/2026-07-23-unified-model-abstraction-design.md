# 统一模型抽象层设计文档

## 概述

参照 RAGFlow 的 `LLMBundle` + `_FACTORY_NAME` 自动发现注册表，为 ALLRAG 构建统一模型抽象层。支持 7 种模型类型（Chat/Embedding/Rerank/CV/OCR/TTS/ASR），通过 `LLMBundle` 门面统一代理所有操作，使用 `litellm` 作为 Chat 模型的兜底方案覆盖 30+ 提供商，配置存储在数据库中支持多租户。

## 决策记录

| 决策 | 选择 | 理由 |
|------|------|------|
| 目标范围 | 7 种模型类型 + 50+ provider | 与 RAGFlow 完全一致 |
| 配置存储 | 数据库（多租户） | 每用户独立 API Key、模型选择 |
| LiteLLM 策略 | 自定义 provider + LiteLLM 兜底 | 特殊优化 + 广覆盖 |
| 抽象模式 | _FACTORY_NAME + inspect 自动发现 | 与 RAGFlow 一致，开箱即用 |
| 统一门面 | LLMBundle | 一个类代理所有模型类型 |

## 架构

```
┌─────────────────────────────────────────────┐
│                 API Layer                    │
│   /api/models  (CRUD 配置)                   │
│   /api/chat    (使用 LLMBundle.chat)         │
└────────────────┬────────────────────────────┘
                 │
┌────────────────┴────────────────────────────┐
│               LLMBundle                     │
│   .chat() / .encode() / .rerank()           │
│   .describe() / .tts() / .transcription()   │
│   .extract_text()                           │
└────────────────┬────────────────────────────┘
                 │
┌────────────────┴────────────────────────────┐
│         Auto-Discovery Registry              │
│   ChatModel["OpenAI"] → OpenAIChat          │
│   ChatModel["Ollama"] → OllamaChat          │
│   ChatModel["Anthropic"] → LiteLLMChat      │
│   EmbeddingModel["OpenAI"] → OpenAIEmbedding│
│   ...                                       │
└────────────────┬────────────────────────────┘
                 │
┌────────────────┴────────────────────────────┐
│   chat_providers.py  embedding_providers.py  │
│   rerank_providers.py  cv_providers.py       │
│   ocr_providers.py  tts_providers.py         │
│   asr_providers.py                           │
└─────────────────────────────────────────────┘
                 │
┌────────────────┴────────────────────────────┐
│   DB: TenantLLM + TenantDefaultModel        │
│   + LLMFactories (预置厂商数据)              │
└─────────────────────────────────────────────┘
```

## 模型类型定义

```python
class ModelType:
    CHAT = "chat"          # LLM 对话生成
    EMBEDDING = "embedding" # 文本向量化
    RERANK = "rerank"      # 检索结果重排序
    CV = "cv"              # 视觉理解（图片→文本）
    OCR = "ocr"            # 文档/图片文字识别
    TTS = "tts"            # 文本转语音
    ASR = "asr"            # 语音转文本
```

## 自动发现注册表

`backend/core/models/__init__.py`：

- 定义 7 个全局注册表字典：`ChatModel`、`EmbeddingModel`、`RerankModel`、`CvModel`、`OcrModel`、`TtsModel`、`AsrModel`
- 使用 `inspect.getmembers()` 扫描各 provider 模块中的类
- 带有 `_FACTORY_NAME` 类属性的类自动注册到对应注册表
- `_FACTORY_NAME` 可以是 `str` 或 `list[str]`（LiteLLM 覆盖多个厂商）

Provider 目录结构：

```
backend/core/models/
├── __init__.py              # 注册表 + 自动发现
├── llm_bundle.py            # LLMBundle 统一门面
├── tenant_llm_service.py    # 数据库 CRUD 服务
├── chat_providers.py        # OpenAI, Ollama, DeepSeek, LiteLLM ...
├── embedding_providers.py   # OpenAI, Ollama, HuggingFace, SiliconFlow ...
├── rerank_providers.py      # Cohere, Jina, BGE, SiliconFlow ...
├── cv_providers.py          # OpenAI Vision, Gemini, Zhipu ...
├── ocr_providers.py         # PaddleOCR, MinerU, SoMark ...
├── tts_providers.py         # OpenAI, Fish Audio, Tongyi-Qianwen ...
└── asr_providers.py         # OpenAI Whisper, FunASR, Tongyi-Qianwen ...
```

## Provider 接口规范

每种模型类型的 Provider 必须实现的方法：

### Chat Provider

```python
class ChatProviderBase:
    _FACTORY_NAME: str | list[str]  # 厂商标识，自动发现用

    def __init__(self, api_key: str, model_name: str, base_url: str = None, **kwargs): ...
    def chat(self, messages: list[dict], **kwargs) -> str: ...
    async def chat_streamly(self, messages: list[dict], **kwargs): ...  # yields str
```

### Embedding Provider

```python
class EmbeddingProviderBase:
    _FACTORY_NAME: str | list[str]

    def __init__(self, api_key: str, model_name: str, base_url: str = None, **kwargs): ...
    def encode(self, texts: list[str]) -> list[list[float]]: ...
    def encode_queries(self, queries: list[str]) -> list[list[float]]: ...
    def similarity(self, a: list[float], b: list[float]) -> float: ...
```

### Rerank Provider

```python
class RerankProviderBase:
    _FACTORY_NAME: str | list[str]

    def __init__(self, api_key: str, model_name: str, base_url: str = None, **kwargs): ...
    def rerank(self, query: str, documents: list[str], top_k: int = 10) -> list[dict]: ...
```

### CV / Vision Provider

```python
class CvProviderBase:
    _FACTORY_NAME: str | list[str]

    def __init__(self, api_key: str, model_name: str, base_url: str = None, **kwargs): ...
    def describe(self, image_base64: str, prompt: str = "") -> str: ...
```

### OCR Provider

```python
class OcrProviderBase:
    _FACTORY_NAME: str | list[str]

    def __init__(self, **kwargs): ...
    def extract_text(self, image_path: str) -> str: ...
```

### TTS Provider

```python
class TtsProviderBase:
    _FACTORY_NAME: str | list[str]

    def __init__(self, api_key: str, model_name: str, base_url: str = None, **kwargs): ...
    def tts(self, text: str) -> bytes: ...
```

### ASR Provider

```python
class AsrProviderBase:
    _FACTORY_NAME: str | list[str]

    def __init__(self, api_key: str, model_name: str, base_url: str = None, **kwargs): ...
    def transcription(self, audio_path: str) -> str: ...
```

## LLMBundle 统一门面

`backend/core/models/llm_bundle.py`：

```python
class LLMBundle:
    """统一模型门面：一个类代理所有模型类型的所有操作"""

    def __init__(self, tenant_id: str, model_type: str, tenant_llm_service):
        self._model_type = model_type
        model_config = tenant_llm_service.get_default_model(tenant_id, model_type)
        self._mdl = self._model_instance(model_config)

    def _model_instance(self, model_config: dict):
        registry_map = {
            "chat": ChatModel, "embedding": EmbeddingModel,
            "rerank": RerankModel, "cv": CvModel,
            "ocr": OcrModel, "tts": TtsModel, "asr": AsrModel,
        }
        registry = registry_map[self._model_type]
        cls = registry[model_config["llm_factory"]]
        return cls(
            api_key=model_config.get("api_key", ""),
            model_name=model_config["llm_name"],
            base_url=model_config.get("api_base"),
        )

    # ── Chat ──
    def chat(self, messages: list[dict], **kwargs) -> str: ...
    async def chat_streamly(self, messages: list[dict], **kwargs): ...

    # ── Embedding ──
    def encode(self, texts: list[str]) -> list[list[float]]: ...
    def encode_queries(self, queries: list[str]) -> list[list[float]]: ...

    # ── Rerank ──
    def rerank(self, query: str, documents: list[str], top_k: int = 10) -> list[dict]: ...

    # ── CV ──
    def describe(self, image_base64: str, prompt: str = "") -> str: ...

    # ── TTS ──
    def tts(self, text: str) -> bytes: ...

    # ── ASR ──
    def transcription(self, audio_path: str) -> str: ...

    # ── OCR ──
    def extract_text(self, image_path: str) -> str: ...
```

## 数据库 Schema

### LLMFactories 表（预置厂商元数据）

```python
class LLMFactories(Base):
    __tablename__ = "llm_factories"
    name = Column(String(100), primary_key=True)       # "OpenAI"
    logo = Column(String(512), default="")
    tags = Column(String(255), default="")              # "LLM,TEXT EMBEDDING"
    status = Column(String(1), default="1")
    description = Column(Text, default="")
    created_at = Column(DateTime, server_default=func.now())
```

### TenantLLM 表（用户配置的模型实例）

```python
class TenantLLM(Base):
    __tablename__ = "tenant_llm"
    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(64), index=True, default="default")
    llm_factory = Column(String(100), nullable=False)   # "OpenAI"
    model_type = Column(String(32), nullable=False)      # "chat"/"embedding"/...
    llm_name = Column(String(255), nullable=False)       # "gpt-4o"
    api_key = Column(String(512), default="")
    api_base = Column(String(512), default="")
    max_tokens = Column(Integer, default=8192)
    used_tokens = Column(Integer, default=0)
    status = Column(String(1), default="1")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
```

### TenantDefaultModel 表（每租户默认模型）

```python
class TenantDefaultModel(Base):
    __tablename__ = "tenant_default_models"
    tenant_id = Column(String(64), primary_key=True, default="default")
    llm_id = Column(Integer, nullable=True)
    embd_id = Column(Integer, nullable=True)
    rerank_id = Column(Integer, nullable=True)
    img2txt_id = Column(Integer, nullable=True)
    ocr_id = Column(Integer, nullable=True)
    tts_id = Column(Integer, nullable=True)
    asr_id = Column(Integer, nullable=True)
```

## TenantLLMService

`backend/core/models/tenant_llm_service.py`：

- `get_default_model(tenant_id, model_type) -> dict` — 查默认模型表 + TenantLLM 表
- `list_models(tenant_id) -> list[dict]` — 列出租户所有已配置模型
- `add_model(tenant_id, llm_factory, model_type, llm_name, api_key, api_base) -> dict`
- `delete_model(tenant_id, model_id)`
- `set_default(tenant_id, model_type, model_id)`
- `list_factories() -> list[dict]` — 列出可用厂商
- `increment_tokens(model_id, tokens)` — 累计 token 用量

## API 端点

`backend/api/models.py`：

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/models/factories` | GET | 列出可用厂商 |
| `/api/models` | GET | 列出租户已配置模型 |
| `/api/models` | POST | 新增模型配置 |
| `/api/models/{id}` | DELETE | 删除模型配置 |
| `/api/models/default` | POST | 设置默认模型 |

## InfraBundle 改造

### 改造前

```python
class InfraBundle:
    embedding_service: Any    # EmbeddingService 实例
    llm_client: Any           # LLMClient 实例
```

### 改造后

```python
class InfraBundle:
    embedding_bundle: LLMBundle   # type="embedding"
    chat_bundle: LLMBundle        # type="chat"
    rerank_bundle: LLMBundle      # type="rerank"
    cv_bundle: LLMBundle | None   # type="cv"
    ocr_bundle: LLMBundle | None  # type="ocr"
    tts_bundle: LLMBundle | None  # type="tts"
    asr_bundle: LLMBundle | None  # type="asr"
```

改造属于 Phase 2-4，Phase 1 只建基础设施层不影响现有代码。

## Provider 实现范围

### Phase 2 核心 Provider（Chat + Embedding + Rerank）

**Chat（~8 provider + LiteLLM 兜底）**：
- OpenAI、Ollama、DeepSeek、Azure-OpenAI
- LiteLLM 兜底覆盖：Tongyi-Qianwen、Bedrock、Moonshot、xAI、DeepInfra、Groq、Cohere、Gemini、NVIDIA、TogetherAI、Anthropic、StepFun、OpenRouter、SILICONFLOW

**Embedding（~8 provider）**：
- OpenAI、Ollama、HuggingFace（本地 SentenceTransformer）
- SiliconFlow、Tongyi-Qianwen、Zhipu、Jina、Mistral

**Rerank（~6 provider）**：
- Cohere、BGE（本地 CrossEncoder）、SiliconFlow
- Jina、NVIDIA、Tongyi-Qianwen

### Phase 3 扩展 Provider（CV + OCR + TTS + ASR）

**CV（~6 provider）**：OpenAI Vision、Gemini、Zhipu、Tongyi-Qianwen、Anthropic、Ollama

**OCR（~3 provider）**：PaddleOCR、Tesseract、VLM-based

**TTS（~4 provider）**：OpenAI、Fish Audio、Tongyi-Qianwen、SILICONFLOW

**ASR（~4 provider）**：OpenAI Whisper、FunASR、Tongyi-Qianwen、SILICONFLOW

## 配置

### config.py 新增

```python
# -- 模型配置模式 -----------------------------------------------
USE_DB_MODEL_CONFIG: bool = True   # True=数据库驱动, False=环境变量（兼容）
```

### config.py 删除（Phase 4）

```python
MIMO_API_KEY: str           # 移入 TenantLLM 表
MIMO_API_BASE: str          # 移入 TenantLLM 表
MIMO_MODEL: str             # 移入 TenantLLM 表
COHERE_API_KEY: str         # 移入 TenantLLM 表
SILICONFLOW_API_KEY: str    # 移入 TenantLLM 表
```

### requirements.txt 新增

```
# === LLM 统一接入 ===
litellm>=1.30.0
```

## 变更文件清单

### 新增（~14 个）

Phase 1:
- `backend/core/models/__init__.py` — 注册表 + 自动发现
- `backend/core/models/llm_bundle.py` — LLMBundle 统一门面
- `backend/core/models/tenant_llm_service.py` — 数据库 CRUD
- `backend/api/models.py` — 模型管理 API
- `backend/db/models_llm.py` — SQLAlchemy 模型定义

Phase 2:
- `backend/core/models/chat_providers.py` — Chat providers
- `backend/core/models/embedding_providers.py` — Embedding providers
- `backend/core/models/rerank_providers.py` — Rerank providers

Phase 3:
- `backend/core/models/cv_providers.py` — CV providers
- `backend/core/models/ocr_providers.py` — OCR providers
- `backend/core/models/tts_providers.py` — TTS providers
- `backend/core/models/asr_providers.py` — ASR providers
- `backend/db/seed_llm_factories.py` — 预置厂商数据

### 修改（~8 个，Phase 4）

- `backend/core/services/infra_factory.py` — DB 驱动初始化
- `backend/core/services/infra_bundle.py` — LLMBundle 字段
- `backend/core/services/retrieval_pipeline.py` — 用 LLMBundle
- `backend/core/services/ingestion_service.py` — 用 LLMBundle
- `backend/core/services/generation_service.py` — 用 LLMBundle
- `backend/core/config.py` — 删除硬编码 API Key
- `backend/main.py` — 注册 models 路由
- `requirements.txt` — 新增 litellm

### 删除（3 个，Phase 4）

- `backend/core/llm_client.py` — 被 chat_providers 替代
- `backend/core/embedding_service.py` — 被 embedding_providers 替代
- `backend/core/providers/siliconflow_adapter.py` — 被 embedding_providers 替代

## 测试策略

```
tests/unit/test_models_registry.py      # 注册表自动发现
tests/unit/test_llm_bundle.py           # LLMBundle 门面（mock provider）
tests/unit/test_tenant_llm_service.py   # TenantLLMService CRUD
tests/unit/test_chat_providers.py       # Chat provider 接口一致性
tests/unit/test_embedding_providers.py  # Embedding provider 接口一致性
```

## 预置厂商数据

初始 seed 包含以下厂商（与 RAGFlow 对齐）：

| 厂商 | 支持类型 |
|------|----------|
| OpenAI | LLM, EMBEDDING, RERANK, CV, ASR, TTS |
| Ollama | LLM, EMBEDDING |
| DeepSeek | LLM |
| Tongyi-Qianwen | LLM, EMBEDDING, RERANK, CV, ASR, TTS |
| Zhipu | LLM, EMBEDDING, RERANK, CV |
| SiliconFlow | LLM, EMBEDDING, RERANK |
| Cohere | LLM, EMBEDDING, RERANK |
| Jina | EMBEDDING, RERANK |
| Anthropic | LLM |
| Gemini | LLM, EMBEDDING, CV |
| NVIDIA | LLM, EMBEDDING, RERANK, CV |
| Mistral | LLM, EMBEDDING |
| Groq | LLM |
| Moonshot | LLM |
| StepFun | LLM |
| BaiduYiyan | LLM, EMBEDDING |
| VolcEngine | LLM, EMBEDDING |
| Fish Audio | TTS |
| FunASR | ASR |
