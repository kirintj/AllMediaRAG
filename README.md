# 多模态 RAG 智能问答系统

> 基于 RAG（检索增强生成）技术的企业级知识问答平台。支持多模态文档解析（PDF / Word / 图片 / OCR）、混合向量 + BM25 检索、HyDE 查询扩展、多策略重排序、Self-RAG 自适应回答验证、全链路 RAGAS 评测与结构化可观测性。后端 FastAPI + SSE 流式输出，前端 Vue 3 + Element Plus，Docker Compose 一键部署。

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Vue.js](https://img.shields.io/badge/Vue.js-3.x-4FC08D?logo=vue.js&logoColor=white)](https://vuejs.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 项目亮点

- **5 阶段检索管线**：查询理解 → 多路召回（向量 + BM25 并行） → 加权 RRF 融合 → Cross-Encoder 重排序 → 置信度评估与自适应补召回，端到端命中率显著优于单路检索
- **多模态文档全链路**：原生支持 PDF / DOCX / Markdown / HTML / 图片，集成 PaddleOCR、Tesseract、VLM 视觉语言模型三级 OCR 引擎，图表亦可检索
- **可插拔组件工厂**：Embedding（本地 BGE-M3 / SiliconFlow 云端）、向量存储（ChromaDB / pgvector）、重排序（Cohere / BGE / SiliconFlow / 混合）均通过 Provider 模式热切换，零代码更换底层实现
- **全链路评测框架**：内置 RAGAS 标准评测 + 自定义检索指标（Hit Rate / MRR / NDCG / MAP），支持 A/B 配对 t 检验、自动配置对比、分维度（查询类型 × 难度）分析，评测数据集可由 LLM 自动生成
- **生产级基础设施**：L1 内存 + L2 Redis 多级缓存（含语义去重）、结构化 JSON 日志、延迟 P95 / 缓存命中率 / 错误率实时指标、可配置告警阈值、JWT 认证与速率限制

---

## 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| **前端框架** | Vue 3.5 + Vite 8 | 响应式 SPA，HMR 开发体验 |
| **UI 组件库** | Element Plus 2.14 | 企业级组件，暗色主题支持 |
| **状态管理** | Pinia 3 | 轻量级 Composition API 状态管理 |
| **后端框架** | FastAPI + Uvicorn | 异步高性能 Python API |
| **流式传输** | SSE (sse-starlette) | Server-Sent Events 逐 token 推送 |
| **大语言模型** | MiMo-v2.5（OpenAI 兼容协议） | SiliconFlow 云端推理 |
| **视觉语言模型** | MiMo-v2.5 VLM | 图表 / 流程图理解 |
| **文本向量化** | BGE-M3（本地 sentence-transformers）/ SiliconFlow 云端 | 多语言稠密向量 |
| **关键词检索** | jieba + rank-bm25 | 中文分词 BM25 |
| **向量数据库** | ChromaDB / PostgreSQL + pgvector | 嵌入式 / 生产级双后端 |
| **关系数据库** | PostgreSQL 16 | 用户、对话、文档元数据存储 |
| **缓存** | Redis 7 + 内存 LRU | L1 / L2 多级缓存 |
| **重排序** | Cohere / BGE / SiliconFlow / 混合 | Cross-Encoder 精排 |
| **OCR** | PaddleOCR / Tesseract / VLM | 三级文字识别引擎 |
| **评测框架** | RAGAS + 自定义指标 | RAG 质量自动化评估 |
| **认证** | JWT (python-jose + bcrypt) | 无状态 Token 鉴权 |
| **数据库迁移** | Alembic | Schema 版本管理 |
| **部署** | Docker Compose + Nginx | 全栈容器化一键部署 |

---

## 目录结构

```
多模态RAG/
├── backend/                              # FastAPI 后端
│   ├── main.py                           # 应用入口
│   ├── requirements.txt                  # Python 依赖清单
│   ├── api/                              # API 路由层
│   │   ├── auth.py                       # 认证接口（注册 / 登录 / 鉴权）
│   │   ├── chat.py                       # 对话接口（SSE 流式响应）
│   │   ├── conversations.py              # 对话历史管理
│   │   ├── documents.py                  # 文档上传 / 删除 / 批量加载
│   │   └── eval.py                       # 评测报告查询接口
│   ├── core/                             # 核心业务模块
│   │   ├── config.py                     # 统一配置管理（pydantic-settings）
│   │   ├── rag_engine.py                 # RAG 引擎门面（三服务编排）
│   │   ├── embedding_service.py          # Embedding 服务（GPU 自动检测 + LRU 缓存）
│   │   ├── vector_store.py               # ChromaDB 向量存储封装
│   │   ├── llm_client.py                 # OpenAI 兼容 LLM 客户端
│   │   ├── document_processor.py         # 文档解析、OCR、分块
│   │   ├── bm25_retriever.py             # BM25 关键词检索（jieba 分词 + 持久化）
│   │   ├── auth.py                       # JWT 认证核心逻辑
│   │   ├── task_manager.py               # 异步任务状态追踪
│   │   ├── services/                     # 三服务架构
│   │   │   ├── __init__.py               # InfraBundle 依赖注入 + create_infra 工厂
│   │   │   ├── retrieval_pipeline.py     # 检索管线（5 阶段）
│   │   │   ├── ingestion_service.py      # 文档摄取服务
│   │   │   └── generation_service.py     # LLM 生成 + 验证服务
│   │   ├── chunking/                     # 分块策略
│   │   │   ├── base.py                   # ChunkingStrategy 抽象基类
│   │   │   ├── fixed_size_strategy.py    # 固定大小分块
│   │   │   ├── recursive_strategy.py     # 递归文本分块
│   │   │   ├── semantic_strategy.py      # 语义相似度分块
│   │   │   └── parent_child_strategy.py  # 层级 Parent-Child 分块
│   │   ├── query_understanding/          # 查询理解模块
│   │   │   ├── classifier.py             # 意图分类器（规则引擎，零 LLM 调用）
│   │   │   ├── router.py                 # 动态路由
│   │   │   ├── hyde_generator.py         # HyDE 假设性文档生成
│   │   │   ├── multi_query.py            # 多查询变体生成
│   │   │   └── rewriters/                # 查询重写器
│   │   ├── reranking/                    # 重排序模块
│   │   │   ├── base.py                   # RerankerProvider 抽象基类
│   │   │   ├── cohere_reranker.py        # Cohere 云端重排序
│   │   │   ├── bge_reranker.py           # BGE 本地重排序
│   │   │   ├── siliconflow_reranker.py   # SiliconFlow 云端重排序
│   │   │   └── manager.py               # 重排序管理器 + 混合策略
│   │   ├── providers/                    # 可插拔组件工厂
│   │   │   ├── base.py                   # 组件抽象基类
│   │   │   ├── factory.py                # ProviderFactory
│   │   │   ├── siliconflow_adapter.py    # SiliconFlow 云 API 适配器
│   │   │   ├── pgvector_adapter.py       # pgvector 向量存储适配器
│   │   │   └── readers/                  # 文件格式读取器
│   │   │       ├── pdf_reader.py
│   │   │       ├── enhanced_pdf_reader.py
│   │   │       ├── markdown_reader.py
│   │   │       ├── docx_reader.py
│   │   │       ├── html_reader.py
│   │   │       └── image_reader.py
│   │   ├── verification/                 # 回答验证模块
│   │   │   ├── citation_verifier.py      # 引用核查
│   │   │   └── self_rag_reflector.py     # Self-RAG 自适应反思
│   │   ├── observability/                # 可观测性
│   │   │   ├── logger.py                 # 结构化 JSON 日志
│   │   │   └── metrics_collector.py      # 线程安全指标收集器
│   │   ├── performance/cache/            # 多级缓存
│   │   │   ├── l1_cache.py               # L1 内存 LRU 缓存
│   │   │   ├── l2_cache.py               # L2 Redis 缓存
│   │   │   └── manager.py                # 缓存管理器（语义去重）
│   │   ├── ocr/                          # OCR 引擎
│   │   └── db/                           # 数据库模型与引擎
│   ├── eval/                             # 评测框架
│   │   ├── run_eval.py                   # 评测主入口
│   │   ├── evaluator.py                  # 自定义评测器
│   │   ├── ragas_evaluator.py            # RAGAS 标准评测器
│   │   ├── metrics.py                    # 检索指标（Hit Rate / MRR / NDCG / MAP）
│   │   ├── ab_runner.py                  # A/B 测试框架（配对 t 检验）
│   │   ├── config_comparator.py          # 自动配置对比
│   │   ├── reranker_benchmark.py         # 重排序策略基准测试
│   │   ├── chunking_benchmark.py         # 分块策略基准测试
│   │   ├── dimensional_eval.py           # 分维度评测（查询类型 × 难度）
│   │   └── generate_dataset.py           # LLM 辅助评测数据集生成
│   ├── scripts/                          # 运维脚本
│   └── alembic/                          # 数据库迁移
├── frontend/                             # Vue 3 前端
│   ├── src/
│   │   ├── features/
│   │   │   ├── auth/LoginView.vue        # 登录 / 注册
│   │   │   ├── chat/                     # 对话模块
│   │   │   ├── documents/                # 文档管理模块
│   │   │   └── eval/EvalDashboard.vue    # 评测结果仪表盘
│   │   ├── stores/                       # Pinia 状态管理
│   │   └── api/                          # Axios API 封装
│   ├── package.json
│   └── vite.config.js
├── tests/                                # 测试套件
│   └── unit/                             # 单元测试（60+ 测试用例）
├── data/                                 # 运行时数据
│   ├── knowledge-base/                   # 知识库文档目录
│   └── conversations/                    # 对话历史持久化
├── docs/                                 # 部署与设计文档
├── docker-compose.yml                    # Docker 全栈编排
├── Dockerfile                            # 后端镜像构建
├── nginx.conf                            # Nginx 反向代理配置
├── .env.example                          # 环境变量模板
└── README.md
```

---

## 环境要求

| 组件 | 最低版本 | 说明 |
|------|----------|------|
| Python | 3.11+ | 后端运行环境 |
| Node.js | 18+ | 前端构建环境 |
| Docker | 24+ | 容器化部署（可选） |
| Docker Compose | 2.20+ | 多服务编排（可选） |
| 内存 | 8 GB+ | 本地 Embedding 模型需约 2 GB |
| 磁盘 | 10 GB+ | 模型文件 + 向量数据 |
| GPU | 可选 | CUDA 12.1+ 可加速 Embedding / OCR |

> 无 GPU 环境可使用 SiliconFlow 云端 Embedding（`EMBEDDING_PROVIDER=siliconflow`），无需本地加载模型。

---

## 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/your-username/multimodal-rag.git
cd multimodal-rag
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，填入必要配置（至少需要 LLM API Key）：

```bash
# 必填
MIMO_API_KEY=your_siliconflow_api_key

# 可选：使用云端 Embedding 免去本地模型下载
EMBEDDING_PROVIDER=siliconflow
SILICONFLOW_API_KEY=your_siliconflow_api_key
```

### 3. 启动后端

```bash
cd backend
pip install -r requirements.txt

# 安装 PyTorch（根据硬件选择）
pip install torch                          # CPU 版本
pip install torch --index-url https://download.pytorch.org/whl/cu121  # CUDA 12.1

python main.py
# 后端运行在 http://localhost:8000
# Swagger 文档：http://localhost:8000/docs
```

### 4. 启动前端

```bash
cd frontend
npm install
npm run dev
# 前端运行在 http://localhost:5173
```

### 5. Docker Compose 一键部署（推荐）

```bash
cp .env.example .env
# 编辑 .env 填入 API Key

docker compose up -d
```

启动后访问：

| 服务 | 地址 | 说明 |
|------|------|------|
| 前端 | http://localhost | Nginx 托管 Vue SPA |
| 后端 API | http://localhost:8000 | FastAPI 服务 |
| Swagger 文档 | http://localhost:8000/docs | 交互式 API 文档 |
| Redis | localhost:6381 | L2 缓存 |
| PostgreSQL | localhost:5433 | pgvector 向量数据库 |

```bash
# 查看日志
docker compose logs -f backend

# 停止服务
docker compose down

# 清除全部数据重新开始
docker compose down -v
```

---

## 功能使用指南

### 文档管理

通过前端右侧面板或 API 上传文档：

```bash
# 单文件上传
curl -X POST http://localhost:8000/api/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@document.pdf"

# 批量上传（< 20 文件同步处理，>= 20 文件异步处理返回 task_id）
curl -X POST http://localhost:8000/api/upload/batch \
  -H "Authorization: Bearer <token>" \
  -F "files=@doc1.pdf" -F "files=@doc2.md" -F "files=@doc3.docx"

# 查询批量上传进度
curl http://localhost:8000/api/upload/batch/status/<task_id> \
  -H "Authorization: Bearer <token>"

# 加载本地知识库目录
curl -X POST http://localhost:8000/api/documents/load \
  -H "Authorization: Bearer <token>"

# 增量同步（仅处理变更文件，基于文件哈希比对）
curl -X POST http://localhost:8000/api/documents/sync \
  -H "Authorization: Bearer <token>"
```

支持格式：`.pdf`、`.docx`、`.md`、`.txt`、`.html`、`.png`、`.jpg`、`.jpeg`、`.bmp`、`.tiff`

### 对话问答

```bash
# RAG 模式（基于知识库检索回答）
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "query": "什么是 RAG？",
    "mode": "rag",
    "conversation_id": "可选-对话ID"
  }'

# 直接模式（不检索知识库，纯 LLM 对话）
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "query": "解释一下 Transformer 架构",
    "mode": "direct"
  }'
```

响应为 SSE 流式格式，逐 token 推送生成内容及引用来源。

### 分块策略切换

在 `.env` 中配置分块策略：

```bash
CHUNKING_STRATEGY=semantic       # 语义分块（默认）
CHUNK_SIZE=512                   # 分块大小（token）
CHUNK_OVERLAP=50                 # 分块重叠
```

可选策略：`semantic`（语义相似度）、`fixed_size`（固定大小）、`recursive`（递归分割）、`parent_child`（层级分块）

### 重排序策略

```bash
# Cohere 云端（默认，需 API Key）
RERANK_STRATEGY=cohere
COHERE_API_KEY=your_key

# SiliconFlow 云端（免费额度）
RERANK_STRATEGY=siliconflow
SILICONFLOW_API_KEY=your_key

# BGE 本地（需下载模型）
RERANK_STRATEGY=bge
BGE_RERANKER_PATH=./models/bge-reranker-base

# 混合策略（Cohere 0.6 + BGE 0.4）
RERANK_STRATEGY=hybrid
```

### 向量存储切换

```bash
# ChromaDB 嵌入式（默认，零配置）
VECTOR_STORE_PROVIDER=chroma
CHROMA_PERSIST_DIR=./chroma_db

# PostgreSQL + pgvector（生产推荐）
VECTOR_STORE_PROVIDER=pgvector
DATABASE_URL=postgresql://rag_user:rag_password@localhost:5432/rag_db
```

切换后需重建索引：

```bash
cd backend
python scripts/rebuild_index.py
```

### 评测与基准测试

```bash
cd backend

# 运行全量评测（自定义指标 + RAGAS）
python eval/run_eval.py --framework both

# 仅运行 RAGAS 评测
python eval/run_eval.py --framework ragas

# A/B 测试（两组配置配对 t 检验）
python eval/ab_runner.py --config-a .env.variant_a --config-b .env.variant_b

# 自动配置对比（内置预设方案）
python eval/config_comparator.py --preset chunking     # 分块策略对比
python eval/config_comparator.py --preset reranker     # 重排序策略对比
python eval/config_comparator.py --preset retrieval    # 检索策略对比

# 重排序基准测试（多策略延迟与质量对比）
python eval/reranker_benchmark.py

# 分块策略基准测试
python eval/chunking_benchmark.py

# 分维度评测（按查询类型和难度分析）
python eval/dimensional_eval.py

# LLM 辅助生成评测数据集
python eval/generate_dataset.py --count 5 --output eval_dataset_auto.json
```

---

## 关键接口 / 参数说明

### API 接口一览

| 接口 | 方法 | 说明 | 认证 |
|------|------|------|------|
| `/api/auth/register` | POST | 用户注册（返回 JWT Token，速率限制） | 否 |
| `/api/auth/login` | POST | 用户登录（返回 JWT Token，速率限制） | 否 |
| `/api/auth/me` | GET | 获取当前用户信息 | 是 |
| `/api/chat` | POST | 发送消息（SSE 流式响应，支持 `mode: rag/direct`） | 是 |
| `/api/conversations` | GET | 获取当前用户对话列表 | 是 |
| `/api/conversations/{conv_id}` | GET | 获取单个对话详情 | 是 |
| `/api/conversations/{conv_id}` | DELETE | 删除单个对话 | 是 |
| `/api/conversations` | DELETE | 清空当前用户所有对话 | 是 |
| `/api/upload` | POST | 上传单个文档（最大 10 MB） | 是 |
| `/api/upload/batch` | POST | 批量上传（最大 200 文件 / 500 MB） | 是 |
| `/api/upload/batch/status/{task_id}` | GET | 查询批量上传进度 | 是 |
| `/api/documents` | GET | 获取已加载文档列表 | 是 |
| `/api/documents/detail` | GET | 获取文档详情（分块数、大小、类型） | 是 |
| `/api/documents/{source}` | DELETE | 删除单个文档及其向量 | 是 |
| `/api/documents` | DELETE | 清空所有文档 | 是 |
| `/api/documents/load` | POST | 批量加载本地文档（后台任务） | 是 |
| `/api/documents/load/status` | GET | 查询批量加载进度 | 是 |
| `/api/documents/sync` | POST | 增量同步（文件哈希比对） | 是 |
| `/api/stats` | GET | 系统统计（文档数、向量数、BM25 状态） | 是 |
| `/api/metrics` | GET | 运行时性能指标（延迟百分位、缓存命中率） | 是 |
| `/api/eval/reports` | GET | 评测报告列表 | 是 |
| `/api/eval/reports/{filename}` | GET | 评测报告详情 | 是 |
| `/health` | GET | 健康检查（含 P95 延迟、缓存命中率） | 否 |

### 核心环境变量参数表

| 参数名 | 类型 | 必填 | 说明 | 默认值 |
|--------|------|------|------|--------|
| `MIMO_API_KEY` | string | **是** | LLM API Key | - |
| `MIMO_API_BASE` | string | 否 | LLM API 地址 | `https://api.siliconflow.cn/v1` |
| `MIMO_MODEL` | string | 否 | LLM 模型名称 | `mimo-v2.5` |
| `EMBEDDING_MODEL_PATH` | string | 否 | 本地 Embedding 模型路径 | `./models/bge-m3` |
| `EMBEDDING_PROVIDER` | string | 否 | Embedding 提供商：`sentence-transformer` / `siliconflow` | `sentence-transformer` |
| `SILICONFLOW_API_KEY` | string | 否 | SiliconFlow API Key（云端 Embedding / Reranking） | - |
| `VECTOR_STORE_PROVIDER` | string | 否 | 向量存储后端：`chroma` / `pgvector` | `chroma` |
| `CHROMA_PERSIST_DIR` | string | 否 | ChromaDB 数据目录 | `./chroma_db` |
| `DATABASE_URL` | string | 否 | PostgreSQL 完整连接 URL（优先于分项配置） | - |
| `PG_HOST` | string | 否 | PostgreSQL 主机 | `localhost` |
| `PG_PORT` | int | 否 | PostgreSQL 端口 | `5432` |
| `PG_USER` | string | 否 | PostgreSQL 用户名 | `rag_user` |
| `PG_PASSWORD` | string | 否 | PostgreSQL 密码 | `rag_password` |
| `PG_DATABASE` | string | 否 | PostgreSQL 数据库名 | `rag_db` |
| `CHUNK_SIZE` | int | 否 | 分块大小（token） | `512` |
| `CHUNK_OVERLAP` | int | 否 | 分块重叠（token） | `50` |
| `CHUNKING_STRATEGY` | string | 否 | 分块策略：`semantic` / `fixed_size` / `recursive` / `parent_child` | `semantic` |
| `TOP_K` | int | 否 | 向量检索返回数量 | `5` |
| `BM25_TOP_K` | int | 否 | BM25 检索返回数量 | `6` |
| `SIMILARITY_THRESHOLD` | float | 否 | 相似度过滤阈值 | `0.5` |
| `RRF_K` | int | 否 | RRF 融合常数 | `60` |
| `RRF_WEIGHT_VECTOR` | float | 否 | 向量检索 RRF 权重 | `0.7` |
| `RRF_WEIGHT_BM25` | float | 否 | BM25 检索 RRF 权重 | `0.3` |
| `USE_HYDE` | bool | 否 | 启用 HyDE 假设性文档扩展 | `true` |
| `MULTI_QUERY_ENABLED` | bool | 否 | 启用多查询变体生成 | `true` |
| `MULTI_QUERY_COUNT` | int | 否 | 查询变体数量 | `3` |
| `RERANK_STRATEGY` | string | 否 | 重排序策略：`cohere` / `bge` / `hybrid` / `siliconflow` | `cohere` |
| `COHERE_API_KEY` | string | 否 | Cohere API Key（cohere 策略必填） | - |
| `RERANK_TOP_K` | int | 否 | 重排序保留数量 | `15` |
| `RERANK_GATE_THRESHOLD` | float | 否 | 重排序相关性门槛 | `0.5` |
| `OCR_PROVIDER` | string | 否 | OCR 引擎：`paddle` / `tesseract` / `none` | `paddle` |
| `OCR_LANG` | string | 否 | OCR 语言 | `ch` |
| `OCR_USE_GPU` | bool | 否 | OCR 使用 GPU | `false` |
| `USE_VLM` | bool | 否 | 启用视觉语言模型 | `false` |
| `VLM_MODEL` | string | 否 | VLM 模型名称 | - |
| `USE_CACHE` | bool | 否 | 启用缓存 | `true` |
| `USE_REDIS` | bool | 否 | 启用 Redis L2 缓存 | `false` |
| `CACHE_L1_MAX_SIZE` | int | 否 | L1 内存缓存容量 | `1000` |
| `CACHE_L1_TTL` | int | 否 | L1 缓存过期时间（秒） | `300` |
| `CACHE_L2_TTL` | int | 否 | L2 Redis 缓存过期时间（秒） | `600` |
| `SEMANTIC_CACHE_ENABLED` | bool | 否 | 启用语义缓存去重 | `true` |
| `SEMANTIC_CACHE_THRESHOLD` | float | 否 | 语义缓存相似度阈值 | `0.95` |
| `JWT_SECRET_KEY` | string | 否 | JWT 签名密钥（**上线前必须更换**） | `change-me-to-a-random-secret` |
| `JWT_EXPIRE_HOURS` | int | 否 | Token 有效期（小时） | `24` |
| `ALLOW_REGISTRATION` | bool | 否 | 允许新用户注册 | `true` |
| `CORS_ORIGINS` | string | 否 | CORS 允许来源（逗号分隔） | `http://localhost:5173` |
| `ENABLE_METRICS` | bool | 否 | 启用性能指标收集 | `true` |
| `METRICS_PORT` | int | 否 | 指标暴露端口 | `9090` |
| `LOG_LEVEL` | string | 否 | 日志级别 | `INFO` |
| `LOG_FORMAT` | string | 否 | 日志格式：`json` | `json` |
| `CITATION_VERIFY_ENABLED` | bool | 否 | 启用引用核查 | `true` |
| `SELF_RAG_ENABLED` | bool | 否 | 启用 Self-RAG 自适应反思 | `true` |
| `RETRIEVAL_REFETCH_ENABLED` | bool | 否 | 启用低置信度补召回 | `true` |
| `PARALLEL_RETRIEVAL` | bool | 否 | 启用向量 + BM25 并行检索 | `true` |
| `BATCH_SIZE` | int | 否 | Embedding 批处理大小 | `32` |

> 完整配置项请参考 [`.env.example`](.env.example)

---

## 测评 / 实验说明

### 评测指标

| 指标 | 类型 | 说明 |
|------|------|------|
| `hit_rate` | 检索 | 是否至少命中一个相关文档 |
| `recall@k` | 检索 | Top-K 中相关文档占比 |
| `mrr` | 检索 | 首个相关结果排名倒数均值 |
| `precision` | 检索 | 检索结果中相关文档占比 |
| `ndcg@k` | 检索 | 归一化折损累积增益 |
| `map` | 检索 | 平均精度均值 |
| `keyword_coverage` | 生成 | 答案中关键词覆盖率 |
| `faithfulness` | 生成 | 生成内容与检索依据一致性（1-5，RAGAS） |
| `answer_relevancy` | 生成 | 答案与问题相关性（RAGAS） |
| `context_precision` | 检索 | 上下文精确度（RAGAS） |
| `context_recall` | 检索 | 上下文召回率（RAGAS） |

### 评测数据集

- `backend/eval/eval_dataset.json`：基础评测数据集
- `backend/eval/eval_dataset_extended.json`：扩展数据集（含 `query_type` 和 `difficulty` 字段）
- 支持 LLM 自动生成评测数据集，覆盖 4 类查询意图 × 3 级难度矩阵（12 个维度）

### 运行评测

```bash
cd backend

# 全量评测
python eval/run_eval.py --framework both --dataset ./eval/eval_dataset.json

# A/B 配对测试
python eval/ab_runner.py

# 自动配置对比（输出 JSON 报告）
python eval/config_comparator.py --preset chunking

# 重排序基准测试（输出延迟统计 avg / P50 / P95）
python eval/reranker_benchmark.py

# 分维度评测
python eval/dimensional_eval.py
```

评测报告以 JSON 格式输出至 `backend/eval/report.json`，同时可通过前端 EvalDashboard 仪表盘可视化查看。

---

## 性能优化方案

### 内置优化策略

| 策略 | 配置项 | 说明 |
|------|--------|------|
| L1 内存缓存 | `USE_CACHE=true` | LRU 缓存高频查询结果，命中时跳过整个检索管线 |
| L2 Redis 缓存 | `USE_REDIS=true` | 跨进程共享缓存，TTL 默认 600 秒 |
| 语义缓存去重 | `SEMANTIC_CACHE_ENABLED=true` | 相似度 > 0.95 的查询直接返回缓存结果 |
| 并行检索 | `PARALLEL_RETRIEVAL=true` | 向量检索与 BM25 通过 ThreadPoolExecutor 并行执行 |
| Embedding 批处理 | `BATCH_SIZE=32` | 批量向量化减少 API 调用次数 |
| 模型懒加载 | 默认启用 | Embedding / Reranker 模型首次调用时才加载，减少启动时间 |
| GPU 自动检测 | 默认启用 | 有 CUDA 则自动使用 FP16 加速 |

### 低配环境适配

```bash
# 无 GPU：使用云端 Embedding + 云端 Reranking
EMBEDDING_PROVIDER=siliconflow
RERANK_STRATEGY=siliconflow

# 低内存：关闭语义缓存和 Self-RAG
SEMANTIC_CACHE_ENABLED=false
SELF_RAG_ENABLED=false
CACHE_L1_MAX_SIZE=200

# 最小资源模式：关闭 OCR 和 VLM
OCR_PROVIDER=none
USE_VLM=false
```

---

## 常见问题 FAQ

### Q: 首次启动报 `torch` 相关错误

`sentence-transformers` 依赖 PyTorch，请根据硬件环境单独安装：

```bash
pip install torch                                    # CPU 版本
pip install torch --index-url https://download.pytorch.org/whl/cu121  # CUDA 12.1
```

或改用云端 Embedding 免除本地模型依赖：

```bash
EMBEDDING_PROVIDER=siliconflow
SILICONFLOW_API_KEY=your_key
```

### Q: ChromaDB 报错 `readonly` 或数据损坏

```bash
rm -rf ./chroma_db
python backend/scripts/rebuild_index.py
```

### Q: pgvector 模式连接失败

确认 PostgreSQL 已安装 pgvector 扩展，并运行数据库迁移：

```bash
cd backend
alembic upgrade head
```

详细安装指南参考 `docs/pgvector-install.md` 和 `docs/postgresql-setup.md`。

### Q: 前端无法访问后端 API

- 开发模式：确认 Vite 代理配置正确（`frontend/vite.config.js` 中 `/api` 代理到 `http://localhost:8000`）
- Docker 模式：检查 `CORS_ORIGINS` 是否包含前端域名
- 生产部署：确认 Nginx 反向代理配置（`nginx.conf`）中 `proxy_pass` 指向后端服务

### Q: 上传大文件超时

单文件限制 10 MB，批量上传限制 200 文件 / 500 MB。超过 20 个文件自动切换为异步处理，通过 `/api/upload/batch/status/{task_id}` 查询进度。

### Q: JWT Token 过期

默认有效期 24 小时，修改 `JWT_EXPIRE_HOURS` 调整。**上线前务必更换 `JWT_SECRET_KEY`**：

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

---

## 开发者指南

### 新增组件流程

本项目采用 Provider 模式实现可插拔架构。新增组件（如自定义 Embedding、向量存储、Reranker）步骤：

1. 在 `backend/core/providers/base.py` 中确认对应抽象基类
2. 实现新 Provider，继承基类并实现所有抽象方法
3. 在 `backend/core/providers/factory.py` 的 `ProviderFactory` 中注册
4. 在 `.env` 中添加对应配置项
5. 编写单元测试，置于 `tests/unit/` 对应目录

### 代码规范

- Python：遵循 PEP 8，类型注解覆盖公开接口
- Vue：Composition API + `<script setup>` 语法
- 提交信息：遵循 [Conventional Commits](https://www.conventionalcommits.org/) 规范

```
feat: 新功能
fix: Bug 修复
docs: 文档更新
test: 测试相关
refactor: 代码重构
perf: 性能优化
```

### 运行测试

```bash
# 运行全部测试
python -m pytest tests/ -v

# 按模块运行
python -m pytest tests/unit/test_query_understanding/ -v
python -m pytest tests/unit/test_reranking/ -v
python -m pytest tests/unit/test_eval/ -v

# 生成覆盖率报告
python -m pytest tests/ --cov=backend --cov-report=html
```

| 测试模块 | 目录 | 覆盖内容 |
|----------|------|----------|
| 查询理解 | `tests/unit/test_query_understanding/` | 意图分类、HyDE、多查询、路由 |
| 重排序 | `tests/unit/test_reranking/` | 基类、BGE、Cohere、管理器 |
| 分块策略 | `tests/unit/test_chunking/` | 四种分块策略 |
| 评测指标 | `tests/unit/test_eval/` | Hit Rate、MRR、NDCG、MAP |
| 缓存系统 | `tests/unit/test_performance/` | L1 / L2 缓存 |
| 可观测性 | `tests/unit/test_observability/` | 结构化日志 |
| 文档读取 | `tests/unit/test_providers/` | PDF、Markdown、DOCX 读取器 |
| 引用核查 | `backend/tests/` | 引用验证、任务管理 |

---

## 开源许可

本项目采用 [MIT License](LICENSE) 开源许可。

---

## 联系方式 & 贡献指南

欢迎参与贡献！无论是 Bug 修复、新功能、文档改进还是评测数据集补充，我们都期待你的 PR。

### 参与方式

1. **提交 Issue**：报告 Bug、提出功能建议或询问使用问题
2. **提交 Pull Request**：
   - Fork 本仓库
   - 创建特性分支：`git checkout -b feature/your-feature`
   - 提交更改：`git commit -m 'feat: add your feature'`
   - 推送分支：`git push origin feature/your-feature`
   - 创建 Pull Request 并描述变更内容
3. **完善文档**：修正错误、补充示例、翻译文档

### 提交规范

使用 [Conventional Commits](https://www.conventionalcommits.org/) 规范，详见上文「代码规范」。

### 行为准则

参与本项目即表示同意遵守开源社区的基本礼仪：尊重他人、建设性讨论、聚焦技术。
