# 文档解析增强设计文档

## 概述

扩展 ALLRAG 的文档解析能力：新增 4 种文件格式（Excel/CSV、PPT、JSON、音频）、4 种 LLM 增强（自动关键词、自动问题、结构化元数据、TOC 提取）、RAPTOR 层级摘要。所有实现参照 RAGFlow 源码对齐，包括 LLM 缓存、并行处理、UMAP+GMM 聚类、Prompt 模板文件化。

## 决策记录

| 决策 | 选择 | 理由 |
|------|------|------|
| 增强范围 | 格式扩展 + LLM 增强 + RAPTOR | 覆盖 80% RAGFlow 能力 |
| 新增格式 | Excel/CSV, PPT, JSON, 音频(ASR) | 全选 |
| LLM 增强 | 关键词、问题、元数据、TOC | 全选 |
| RAPTOR | GMM 聚类 + 递归摘要（UMAP + BIC + 软分配） | 与 RAGFlow 一致 |
| 触发方式 | 可配置开关 | 每个增强独立开关 |
| LLM 缓存 | Redis + xxhash64 + 24h TTL | 与 RAGFlow 一致 |
| 并行处理 | asyncio.gather 所有 chunk | 与 RAGFlow 一致 |
| Prompt 管理 | 独立 .md 文件 + Jinja2 模板 | 与 RAGFlow 一致 |

## 架构

```
文档上传 → Worker → DocumentProcessor.process_file()
    │
    ├── FileReader.read()           ← 新增: Excel/PPT/JSON/Audio
    │
    ├── ChunkingStrategy.split()    ← 现有 5 种策略
    │
    ├── ┌─ LLM Enrichment（可配置）──────────────┐
    │   │  keyword_extraction()   (并行+缓存)     │
    │   │  question_proposal()    (并行+缓存)     │
    │   │  gen_metadata()         (并行+缓存)     │
    │   │  build_toc()            (两阶段+并发)    │
    │   └─────────────────────────────────────────┘
    │
    ├── ┌─ RAPTOR（可配置）──────────────────────┐
    │   │  UMAP 降维                              │
    │   │  GMM 聚类 (BIC 选 K, 软分配)            │
    │   │  递归摘要 (并行 per 层)                  │
    │   │  → 生成 summary chunks                  │
    │   └─────────────────────────────────────────┘
    │
    ▼
Embedding + Index (ES)
```

## 新增文件格式

### Excel/CSV Reader

`core/providers/readers/excel_reader.py`：
- `.xlsx` → openpyxl 读取，每 sheet 转 Markdown 表格
- `.csv` → csv 标准库，转 Markdown 表格
- 保留 sheet 名作为 section 标题

### PPT Reader

`core/providers/readers/pptx_reader.py`：
- `.pptx` → python-pptx 提取每页文本框 + 表格 + 备注
- 按页分隔，保留页码信息

### JSON Reader

`core/providers/readers/json_reader.py`：
- `.json` → json 标准库递归展平为 key: value 文本行

### Audio Reader

`core/providers/readers/audio_reader.py`：
- `.mp3/.wav/.m4a` → 调用 LLMBundle（ASR 类型）转文字

### 依赖新增

```
openpyxl>=3.1.0
python-pptx>=0.6.23
```

## LLM 缓存层

`core/enrichment/cache.py`：

```python
class LLMCache:
    def __init__(self, redis_client, ttl: int = 86400): ...
    def get(self, llm_name, content, task_type, params=None) -> str | None: ...
    def set(self, llm_name, content, task_type, value, params=None): ...
```

- Key: `llm_cache:{sha256(llm_name|content|task_type|params)[:16]}`
- TTL: 24 小时（与 RAGFlow 一致）
- 所有增强器统一使用缓存，重复文档不浪费 LLM 调用

## LLM 增强

### 模块结构

```
core/enrichment/
├── __init__.py
├── cache.py                  # LLM 缓存
├── keyword_extractor.py      # 自动关键词
├── question_generator.py     # 自动问题
├── metadata_extractor.py     # 结构化元数据
├── toc_builder.py            # 目录提取
├── raptor.py                 # RAPTOR 聚类摘要
└── prompts/                  # Prompt 模板
    ├── keyword_prompt.md
    ├── question_prompt.md
    ├── metadata_prompt.md
    ├── toc_system_prompt.md
    ├── toc_user_prompt.md
    ├── toc_level_prompt.md
    └── raptor_summary_prompt.md
```

### 自动关键词提取

- Prompt: 与 RAGFlow 对齐的 `keyword_prompt.md`
- 输入: chunk 文本（截断 1000 字符）
- 输出: 逗号分隔关键词列表
- 存储: `chunk.metadata["keywords"]` + 分词后的 `chunk.metadata["keywords_tks"]`
- 并行: `asyncio.gather` 所有 chunk
- 缓存: Redis 24h

### 自动问题生成

- Prompt: 与 RAGFlow 对齐的 `question_prompt.md`
- 输入: chunk 文本
- 输出: 每行一个问题
- 存储: `chunk.metadata["questions"]` + `chunk.metadata["questions_tks"]`
- 并行 + 缓存同上

### 结构化元数据生成

- Prompt: 与 RAGFlow 对齐的 `metadata_prompt.md`
- Schema: 可配置，支持用户自定义 JSON Schema + enum 过滤
- 默认 Schema: `{topic, entities, summary}`
- 规则: Strict Evidence Only、Zero-Hallucination、Empty Result → `{}`
- 存储: `chunk.metadata` 合并

### TOC 提取（两阶段）

与 RAGFlow 对齐的两阶段流程：

1. **Stage 1 — 标题提取**: 按 token 预算分批，`asyncio.gather` 并发提取。Prompt 包含中英文标题检测规则。
2. **Stage 2 — 层级分配**: 单次 LLM 调用，为标题分配层级。

输出: `[{level, title, chunk_ids}]`，存为特殊 chunk（`chunk_type: "toc"`）。

## RAPTOR

`core/enrichment/raptor.py`：

### 参数（与 RAGFlow 对齐）

```python
max_cluster: int = 64           # 最大簇数
threshold: float = 0.1          # GMM 软分配阈值
clustering_method: str = "gmm"  # "gmm" 或 "ahc"
small_layer_collapse: int = 8   # 小层折叠阈值
max_errors: int = 3             # 最大错误数后中止
max_depth: int = 3              # 最大递归深度
```

### 流程

```
原始 chunks (N 个)
    │
    ▼ Embedding（带缓存）
    │
    ▼ UMAP 降维（n_neighbors=min((N-1)^0.8, 100), n_components=min(12, N-2)）
    │
    ▼ GMM 聚类（BIC 选最优 K, 软分配 prob > threshold）
    │
    ▼ 每个簇并行 LLM 摘要（asyncio.gather）
    │
    ▼ 如果剩余 > 1 个摘要，递归
    │
    ▼ 小层折叠：≤ small_layer_collapse 时合并为一个摘要并终止
    │
    ▼ 所有层级的 summary chunks 合并入库
```

### 关键行为（与 RAGFlow 对齐）

- **UMAP 降维**: 聚类前先降维，提高 GMM 效果
- **BIC 选 K**: 遍历 k=1..max_cluster，选 BIC 最小的 K
- **软分配**: prob > threshold 的簇都分配，一个 chunk 可属于多个簇
- **小层折叠**: ≤ 8 个节点时合并为一个摘要，防止 N→N-1→N-2 退化
- **防退化**: n_clusters >= n_inputs 时强制 n_clusters=1
- **并行摘要**: 每层内所有簇的摘要并发执行
- **错误容忍**: 单簇摘要失败跳过，累计超过 max_errors 中止
- **重试**: LLM 调用 3 次重试 + 指数退避

### 摘要 Prompt（与 RAGFlow 对齐）

```
System: You're a helpful assistant.

Help me with the following task.

Please summarize the following paragraphs. Be careful with the numbers, do not make things up.
Paragraphs as following:
      {cluster_content}
The above is the content you need to summarize.

User: Beside the summarization, give a title at the first line of your summarization.
Must be in the same language as the paragraphs.
```

输出第一行为标题，其余为摘要。

### 依赖新增

```
scikit-learn>=1.3.0
umap-learn>=0.5.0
jinja2>=3.1.0
```

## 配置

### config.py 新增

```python
# -- 文档格式支持 ------------------------------------------------
SUPPORTED_FILE_EXTENSIONS: str = ".pdf,.docx,.html,.htm,.txt,.md,.png,.jpg,.jpeg,.bmp,.tiff,.tif,.xlsx,.csv,.pptx,.json,.mp3,.wav,.m4a"

# -- LLM 增强（分块后执行）--------------------------------------
ENABLE_AUTO_KEYWORDS: bool = False
ENABLE_AUTO_QUESTIONS: bool = False
ENABLE_METADATA_EXTRACTION: bool = False
ENABLE_TOC_EXTRACTION: bool = False
AUTO_KEYWORDS_TOPN: int = 5
AUTO_QUESTIONS_TOPN: int = 3

# -- RAPTOR -------------------------------------------------------
ENABLE_RAPTOR: bool = False
RAPTOR_MAX_CLUSTERS: int = 64
RAPTOR_THRESHOLD: float = 0.1
RAPTOR_CLUSTERING_METHOD: str = "gmm"  # gmm 或 ahc
RAPTOR_SMALL_LAYER_COLLAPSE: int = 8
RAPTOR_MAX_ERRORS: int = 3
RAPTOR_MAX_DEPTH: int = 3

# -- LLM 缓存 ----------------------------------------------------
ENRICHMENT_CACHE_TTL: int = 86400  # 24h
```

### requirements.txt 新增

```
openpyxl>=3.1.0
python-pptx>=0.6.23
scikit-learn>=1.3.0
umap-learn>=0.5.0
jinja2>=3.1.0
```

## 集成点

### ingestion_service.py 改造

在 `ingest_document()` 中，分块之后、embedding 之前插入：

```python
# LLM 缓存
from core.enrichment.cache import LLMCache
cache = LLMCache(self._infra.cache_manager._redis, config.ENRICHMENT_CACHE_TTL)

# LLM 增强（可选）
if any([config.ENABLE_AUTO_KEYWORDS, config.ENABLE_AUTO_QUESTIONS,
        config.ENABLE_METADATA_EXTRACTION, config.ENABLE_TOC_EXTRACTION]):
    chat = self._infra.llm_client  # LLMBundle

    if config.ENABLE_AUTO_KEYWORDS:
        from core.enrichment.keyword_extractor import KeywordExtractor
        chunks = await KeywordExtractor(chat, cache).extract_async(chunks)

    if config.ENABLE_AUTO_QUESTIONS:
        from core.enrichment.question_generator import QuestionGenerator
        chunks = await QuestionGenerator(chat, cache).generate_async(chunks)

    if config.ENABLE_METADATA_EXTRACTION:
        from core.enrichment.metadata_extractor import MetadataExtractor
        chunks = await MetadataExtractor(chat, cache).extract_async(chunks)

    if config.ENABLE_TOC_EXTRACTION:
        from core.enrichment.toc_builder import TOCBuilder
        toc = await TOCBuilder(chat, cache).build_async(source, chunks)

# RAPTOR（可选）
if config.ENABLE_RAPTOR:
    from core.enrichment.raptor import RAPTORProcessor
    raptor = RAPTORProcessor(chat, self._embedding_service, cache, ...)
    summaries = await raptor.process_async(chunks, source)
    chunks.extend(summaries)
```

### document_processor.py 改造

注册新 FileReader：

```python
from core.providers.readers.excel_reader import ExcelReader
from core.providers.readers.pptx_reader import PptxReader
from core.providers.readers.json_reader import JsonReader
from core.providers.readers.audio_reader import AudioReader

# 在 _build_file_reader_registry 中注册
file_reader_registry.register(ExcelReader())   # .xlsx, .csv
file_reader_registry.register(PptxReader())    # .pptx
file_reader_registry.register(JsonReader())    # .json
file_reader_registry.register(AudioReader())   # .mp3, .wav, .m4a
```

## 变更文件清单

### 新增（~16 个）

- `core/providers/readers/excel_reader.py`
- `core/providers/readers/pptx_reader.py`
- `core/providers/readers/json_reader.py`
- `core/providers/readers/audio_reader.py`
- `core/enrichment/__init__.py`
- `core/enrichment/cache.py`
- `core/enrichment/keyword_extractor.py`
- `core/enrichment/question_generator.py`
- `core/enrichment/metadata_extractor.py`
- `core/enrichment/toc_builder.py`
- `core/enrichment/raptor.py`
- `core/enrichment/prompts/keyword_prompt.md`
- `core/enrichment/prompts/question_prompt.md`
- `core/enrichment/prompts/metadata_prompt.md`
- `core/enrichment/prompts/toc_system_prompt.md`
- `core/enrichment/prompts/toc_user_prompt.md`
- `core/enrichment/prompts/toc_level_prompt.md`
- `core/enrichment/prompts/raptor_summary_prompt.md`

### 修改（4 个）

- `core/document_processor.py` — 注册新 FileReader
- `core/services/ingestion_service.py` — 插入增强 + RAPTOR
- `core/config.py` — 新增配置项
- `requirements.txt` — 新增依赖
