# DataPilotAI 多模态 RAG 智能问答系统

> 基于 RAG（检索增强生成）技术的企业级知识问答平台。多模态文档解析、混合检索、知识图谱增强、全链路评测与结构化可观测性。后端 FastAPI + SSE 流式，前端 Vue 3 + 自定义 UI，Docker Compose 一键部署。

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Vue.js](https://img.shields.io/badge/Vue.js-3.x-4FC08D?logo=vue.js&logoColor=white)](https://vuejs.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 项目亮点

### 检索增强

- **5 阶段检索管线**：查询理解 → 多路召回（向量 + BM25 并行） → 加权 RRF 融合 → Cross-Encoder 重排序 → 置信度评估与自适应补召回
- **知识图谱增强检索**（GraphRAG）：Neo4j 图存储 + LLM 实体关系抽取 + PageRank 社区发现 + 图谱-向量混合检索，三种抽取策略（通用 / 轻量 / NER）
- **RAPTOR 层级摘要检索**：文档分块 → 聚类 → LLM 摘要 → 递归构建层级树，回答时同时检索原始块与高层摘要，兼顾细节与全局语义
- **查询理解与增强**：意图分类 + 动态路由 + HyDE 假设性文档 + 多查询变体生成 + 查询重写，提升复杂查询召回率
- **Self-RAG 自适应反思**：引用核查 + 自适应反思，低置信度触发补召回或拒答，抑制幻觉
- **多策略分块**：语义相似度 / 递归 / 固定大小 / Parent-Child 层级 / VLM 区域分块，按文档类型自适应选择

### 多模态处理

- **多模态文档全链路**：支持 PDF / DOCX / Markdown / HTML / 图片 / Excel / CSV / PPTX / JSON / 音频等 11 种格式
- **三级 OCR 引擎**：PaddleOCR / Tesseract / VLM 视觉语言模型，按场景降级策略选择
- **VLM 统一提取器**：Qwen-VL-Max 版面分析 + OCR + 图表理解，按区域类型分块，原图附带至多模态 LLM

### 工程化基础设施

- **可插拔组件工厂**：Embedding（本地 BGE-M3 / SiliconFlow / 通义千问 / Ollama）、向量存储、重排序（Cohere / BGE / SiliconFlow / DashScope / 混合）通过 Provider 模式热切换，InfraBundle 依赖注入统一组装
- **L1/L2 多级缓存**：内存 LRU + Redis 双层缓存，语义去重 + 精准失效，降低重复查询成本
- **全链路评测框架**：RAGAS 标准评测 + 自定义检索指标（Hit Rate / MRR / NDCG / MAP），A/B 配对 t 检验，分维度分析，LLM 自动生成评测数据集
- **异步任务队列**：基于 Redis Stream 的异步 Worker 进程，文档上传后后台解析 → 分块 → 向量化 → 索引，支持进度追踪和重试
- **生产级基础设施**：MinIO/S3 文件存储、JWT 认证、速率限制、结构化 JSON 日志、多租户隔离、8 容器 Docker Compose 一键部署

### 前端体验

- **自研 UI 组件库**：基于 Radix Vue 原语，自研按钮 / 对话框 / Tabs / Tooltip / Sheet / 下拉菜单 / Context Menu / Scroll Area 等组件
- **SSE 流式响应**：Server-Sent Events 逐 token 推送，实时渲染 Markdown / 代码块 / 公式
- **响应式跨端适配**：桌面端 L1/L2 双栏布局，移动端底部导航 + 横向滚动标签 + 顶部 Sheet 抽屉，安全区与触摸目标优化
- **知识图谱可视化**：Neo4j 图数据力导向渲染，支持实体关系探索与社区聚类展示

---

## 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| **前端框架** | Vue 3.5 + Vite 8 | 响应式 SPA，HMR 开发体验 |
| **UI 组件** | 自定义组件库 | 基于 Radix Vue 原语，按钮 / 对话框 / Tabs / 下拉菜单 / Tooltip / Sheet 等 |
| **状态管理** | Pinia 3 | 轻量级 Composition API 状态管理 |
| **后端框架** | FastAPI + Uvicorn | 异步高性能 Python API |
| **流式传输** | SSE (sse-starlette) | Server-Sent Events 逐 token 推送 |
| **大语言模型** | MiMo-v2.5（OpenAI 兼容协议） | SiliconFlow 云端推理 |
| **视觉语言模型** | Qwen-VL-Max | DashScope API，统一提取器（版面分析 + OCR + 图表理解） |
| **文本向量化** | BGE-M3 / SiliconFlow / 通义千问 / Ollama | 多语言稠密向量，可热切换 |
| **关键词检索** | jieba + rank-bm25 | 中文分词 BM25 |
| **向量数据库** | Elasticsearch 8.x | 混合检索（向量 + BM25） |
| **关系数据库** | PostgreSQL 16（+ pgvector） | 用户、对话、文档元数据存储 |
| **图数据库** | Neo4j | 知识图谱存储与检索 |
| **缓存** | Redis 7 + 内存 LRU | L1 / L2 多级缓存 |
| **文件存储** | MinIO / S3 | 可扩展对象存储 |
| **任务队列** | Redis Stream | 异步 Worker 任务处理 |
| **重排序** | Cohere / BGE / SiliconFlow / DashScope / 混合 | Cross-Encoder 精排 |
| **OCR** | PaddleOCR / Tesseract / VLM | 三级文字识别引擎 |
| **评测框架** | RAGAS + 自定义指标 | RAG 质量自动化评估 |
| **认证** | JWT（python-jose + bcrypt） | 无状态 Token 鉴权 |
| **部署** | Docker Compose + Nginx | 全栈容器化一键部署 |

---

## 目录结构

```
DataPilotAI/
├── backend/                              # FastAPI 后端
│   ├── main.py                           # 应用入口（lifespan 生命周期、中间件、路由注册）
│   ├── worker.py                         # 独立 Worker 进程（消费 Redis Stream 异步处理文档）
│   ├── requirements.txt                  # Python 依赖清单
│   ├── api/                              # API 路由层
│   │   ├── auth.py                       # 认证接口（注册 / 登录 / 鉴权）
│   │   ├── chat.py                       # 对话接口（SSE 流式响应）
│   │   ├── conversations.py              # 对话历史管理（CRUD / 收藏 / 归档 / 分享 / 复制）
│   │   ├── documents.py                  # 文档上传 / 删除 / 批量加载 / 增量同步 / 任务状态
│   │   ├── knowledgebases.py             # 知识库 CRUD 管理 + 文档列表
│   │   ├── tag_kb.py                     # 标签知识库管理（上传 / 查询 / 删除 / 标签列表）
│   │   ├── graph.py                      # 知识图谱查询（可视化数据 / 搜索 / 统计）
│   │   ├── models.py                     # 模型管理（CRUD / 默认模型 / 类型 / 工厂列表）
│   │   ├── settings.py                   # RAG 系统设置接口
│   │   ├── team.py                       # 团队管理（成员 CRUD / 邀请）
│   │   ├── eval.py                       # 评测报告查询 + 系统指标
│   │   └── deps.py                       # API 依赖注入（InfraBundle / Service / 数据库会话）
│   ├── core/                             # 核心业务模块
│   │   ├── config.py                     # 统一配置管理（AppSettings，全部 .env 映射）
│   │   ├── rag_engine.py                 # RAG 引擎门面（编排 Retrieval / Ingestion / Generation 三服务）
│   │   ├── auth.py                       # JWT 认证核心逻辑
│   │   ├── llm_client.py                 # LLM 统一调用封装
│   │   ├── document_processor.py         # 文档解析、OCR、分块、LLM 增强
│   │   ├── embedding_service.py          # Embedding 服务封装
│   │   ├── image_store.py                # 原图文件系统存储（MD5 去重）
│   │   ├── index_manager.py              # 索引状态管理
│   │   ├── rate_limit.py                 # 速率限制
│   │   ├── tag_kb.py                     # 标签知识库核心逻辑
│   │   ├── services/                     # 四服务架构
│   │   │   ├── infra_bundle.py           # InfraBundle 共享依赖容器（DataClass）
│   │   │   ├── infra_factory.py          # create_infra 工厂组装
│   │   │   ├── infra_init.py             # 基础设施初始化
│   │   │   ├── retrieval_pipeline.py     # 检索管线（5 阶段）
│   │   │   ├── retrieval_bundle.py       # 检索结果数据包
│   │   │   ├── ingestion_service.py      # 文档摄取服务
│   │   │   ├── generation_service.py     # LLM 生成 + 验证服务
│   │   │   ├── generation_bundle.py      # 生成结果数据包
│   │   │   ├── processing_bundle.py      # 处理结果数据包
│   │   │   ├── bundle_factory.py         # Bundle 工厂
│   │   │   ├── protocols.py              # 服务协议定义
│   │   │   └── exceptions.py             # 服务层异常
│   │   ├── chunking/                     # 分块策略
│   │   │   ├── base.py                   # ChunkingStrategy 抽象基类
│   │   │   ├── fixed_size_strategy.py    # 固定大小分块
│   │   │   ├── recursive_strategy.py     # 递归文本分块
│   │   │   ├── semantic_strategy.py      # 语义相似度分块
│   │   │   ├── parent_child_strategy.py  # 层级 Parent-Child 分块
│   │   │   └── region_chunker.py         # 按区域类型分块（VLM 提取专用）
│   │   ├── providers/                    # 可插拔组件提供商
│   │   │   ├── base.py                   # Provider 抽象基类
│   │   │   ├── factory.py                # ProviderFactory 自动发现与注册
│   │   │   ├── elasticsearch_store.py    # Elasticsearch 向量存储适配器（多租户）
│   │   │   ├── siliconflow_adapter.py    # SiliconFlow API 适配器
│   │   │   └── readers/                  # 文件格式读取器
│   │   │       ├── pdf_reader.py
│   │   │       ├── enhanced_pdf_reader.py
│   │   │       ├── markdown_reader.py
│   │   │       ├── docx_reader.py
│   │   │       ├── html_reader.py
│   │   │       ├── image_reader.py
│   │   │       ├── excel_reader.py
│   │   │       ├── csv_reader.py
│   │   │       ├── json_reader.py
│   │   │       ├── pptx_reader.py
│   │   │       └── audio_reader.py
│   │   ├── query_understanding/          # 查询理解模块
│   │   │   ├── classifier.py             # 意图分类器（规则引擎）
│   │   │   ├── router.py                 # 动态路由
│   │   │   ├── hyde_generator.py         # HyDE 假设性文档生成
│   │   │   ├── multi_query.py            # 多查询变体生成
│   │   │   └── rewriters/                # 查询重写器
│   │   │       ├── base.py
│   │   │       ├── hyde_rewriter.py
│   │   │       └── multi_query_rewriter.py
│   │   ├── reranking/                    # 重排序模块
│   │   │   ├── base.py                   # RerankerProvider 抽象基类
│   │   │   ├── cohere_reranker.py        # Cohere 云端重排序
│   │   │   ├── bge_reranker.py           # BGE 本地重排序
│   │   │   ├── siliconflow_reranker.py   # SiliconFlow 云端重排序
│   │   │   ├── dashscope_reranker.py     # DashScope 云端重排序（gte-rerank/qwen3-rerank）
│   │   │   └── manager.py                # 重排序管理器 + 混合策略
│   │   ├── retrieval/                    # 检索增强
│   │   │   └── confidence_evaluator.py   # 置信度评估器
│   │   ├── verification/                 # 回答验证模块
│   │   │   ├── citation_verifier.py      # 引用核查
│   │   │   └── self_rag_reflector.py     # Self-RAG 自适应反思
│   │   ├── enrichment/                   # LLM 增强模块
│   │   │   ├── prompt_loader.py          # Prompt 模板加载器
│   │   │   ├── content_tagger.py         # 内容标签分类
│   │   │   ├── keyword_extractor.py      # 关键词提取
│   │   │   ├── metadata_extractor.py     # 元数据提取
│   │   │   ├── question_generator.py     # 问题生成
│   │   │   ├── raptor.py                 # RAPTOR 层级摘要
│   │   │   ├── toc_builder.py            # 目录结构构建
│   │   │   ├── cache.py                  # 增强缓存
│   │   │   └── prompts/                  # 14 个 Prompt 模板（社区报告 / 实体抽取 / 摘要等）
│   │   ├── kg/                           # 知识图谱模块
│   │   │   ├── graph_store.py            # Neo4j 图存储
│   │   │   ├── extractor.py              # LLM 实体关系抽取（两阶段）
│   │   │   ├── extractors/               # 抽取策略
│   │   │   │   ├── base.py               # 抽象基类
│   │   │   │   ├── general_extractor.py  # 通用抽取器
│   │   │   │   ├── light_extractor.py    # 轻量抽取器
│   │   │   │   └── ner_extractor.py      # NER 抽取器
│   │   │   ├── merger.py                 # 实体合并
│   │   │   ├── entity_resolution.py      # 实体消歧
│   │   │   ├── community.py              # 社区发现（PageRank）
│   │   │   └── graph_retriever.py        # 图检索器
│   │   ├── ocr/                          # OCR 引擎
│   │   │   ├── base.py                   # OCRProvider 抽象基类
│   │   │   ├── paddle_provider.py        # PaddleOCR 引擎
│   │   │   ├── tesseract_provider.py     # Tesseract 引擎
│   │   │   ├── vlm_provider.py           # VLM 视觉语言模型（图表描述）
│   │   │   └── vlm_extractor.py          # VLM 统一提取器
│   │   ├── storage/                      # 文件存储
│   │   │   └── minio_storage.py          # MinIO / S3 对象存储适配器
│   │   ├── task_queue/                   # 异步任务队列
│   │   │   ├── queue.py                  # Redis Stream 封装（队列 / 消费组 / ACK 机制）
│   │   │   └── models.py                 # TaskMessage / TaskState 数据模型
│   │   ├── performance/cache/            # 多级缓存
│   │   │   ├── l1_cache.py               # L1 内存 LRU 缓存
│   │   │   ├── l2_cache.py               # L2 Redis 缓存
│   │   │   └── manager.py                # 缓存管理器（语义去重 + 精准失效）
│   │   ├── observability/                # 可观测性
│   │   │   ├── logger.py                 # 结构化 JSON 日志（JSONFormatter）
│   │   │   └── metrics_collector.py      # 线程安全指标收集器
│   │   └── db/                           # 数据库层
│   │       ├── base.py                   # SQLAlchemy 引擎 + Base 声明
│   │       ├── engine.py                 # 数据库会话工厂
│   │       ├── models.py                 # 核心 ORM 模型（Conversation / Message / Document）
│   │       ├── crud.py                   # 通用 CRUD 操作
│   │       ├── llm_models.py             # LLM 模型 ORM 模型
│   │       ├── seed_llm_factories.py     # LLM 工厂种子数据
│   │       ├── tenant_models.py          # 多租户 ORM 模型（Tenant / UserTenant / Knowledgebase / KBDocument）
│   │       └── user_models.py            # 用户 ORM 模型
│   ├── eval/                             # 评测框架
│   │   ├── run_eval.py                   # 评测主入口
│   │   ├── evaluator.py                  # 自定义评测器
│   │   ├── ragas_evaluator.py            # RAGAS 标准评测器
│   │   ├── metrics.py                    # 检索指标（Hit Rate / MRR / NDCG / MAP）
│   │   ├── ab_runner.py                  # A/B 测试框架（配对 t 检验）
│   │   ├── ab_comparison.py              # A/B 对比分析
│   │   ├── config_comparator.py          # 自动配置对比
│   │   ├── reranker_benchmark.py         # 重排序策略基准测试
│   │   ├── chunking_benchmark.py         # 分块策略基准测试
│   │   ├── dimensional_eval.py           # 分维度评测
│   │   ├── dataset_tools.py              # 数据集工具
│   │   ├── generate_dataset.py           # LLM 辅助评测数据集生成
│   │   ├── generate_resume_data.py       # 简历数据集生成
│   │   ├── performance_benchmark.py      # 性能基准测试
│   │   ├── run_baseline.py               # 基准线运行
│   │   ├── QUICKSTART.md                 # 评测快速入门
│   │   ├── eval_dataset.json             # 评测数据集
│   │   ├── eval_dataset_challenge.json
│   │   └── eval_dataset_extended.json
│   └── scripts/                          # 运维脚本
│       ├── init_database.py              # 数据库初始化
│       └── fetch_docs.py                 # 文档拉取工具
├── frontend/                             # Vue 3 前端
│   ├── src/
│   │   ├── App.vue                       # 根组件（L1/L2 双栏布局 + 页面路由）
│   │   ├── main.js                       # 应用入口
│   │   ├── styles/globals.css            # 全局样式
│   │   ├── components/                   # 通用 UI 组件
│   │   │   ├── layout/PageLayout.vue     # 全页面布局容器
│   │   │   └── ui/                       # 自研组件库（button / dialog / tabs / tooltip / sheet / dropdown-menu / context-menu 等）
│   │   ├── features/                     # 功能模块
│   │   │   ├── navigation/               # 导航体系
│   │   │   │   ├── L1Sidebar.vue         # 一级侧栏（功能切换）
│   │   │   │   ├── L2Sidebar.vue         # 二级侧栏（上下文导航）
│   │   │   │   ├── NavItem.vue           # 导航项
│   │   │   │   └── panels/               # 侧栏面板（Chat / KB / Settings / Team）
│   │   │   ├── auth/LoginView.vue        # 登录 / 注册
│   │   │   ├── chat/                     # 对话模块（ChatShell / MessageBubble / ChatComposer / MarkdownRenderer 等）
│   │   │   ├── conversations/            # 会话管理（AppSidebar / ConversationList / MobileDetailSheet）
│   │   │   ├── documents/                # 文档管理（DocumentContent / DocumentDrawer）
│   │   │   ├── kb/                       # 知识库（KbPage / KnowledgebaseContent / KnowledgebaseDrawer）
│   │   │   ├── tag-kb/                   # 标签知识库（TagKbContent / TagKbDrawer）
│   │   │   ├── team/                     # 团队管理（TeamPage / TeamContent / TeamDrawer）
│   │   │   ├── model-manager/            # 模型管理（ModelContent / ModelManager）
│   │   │   ├── graph/                    # 知识图谱可视化（GraphContent / GraphViewer）
│   │   │   ├── eval/                     # 评测仪表盘（EvalDashboard / EvalContent）
│   │   │   └── settings/                 # 系统设置（总览 / 文档解析 / RAPTOR / 内容标签 / 知识图谱）
│   │   ├── stores/                       # Pinia 状态管理（12 个 Store）
│   │   ├── api/                          # Axios API 封装（12 个模块）
│   │   ├── composables/                  # 组合式函数（useTheme）
│   │   └── lib/utils.ts                  # 工具库
│   ├── package.json
│   └── vite.config.js
├── tests/                                # 测试套件
│   ├── conftest.py                       # Pytest 共享夹具
│   ├── fixtures/                         # 测试数据
│   │   └── kg_golden_set.json            # 知识图谱黄金数据集
│   ├── integration/                      # 集成测试
│   │   ├── test_kg_e2e.py                # 知识图谱端到端测试
│   │   └── test_kg_eval.py               # 知识图谱评测测试
│   └── unit/                             # 单元测试
│       ├── test_chunking/                # 分块策略
│       ├── test_eval/                    # 评测指标
│       ├── test_kg/                      # 知识图谱（抽取器 / 图检索 / 图存储）
│       ├── test_observability/           # 可观测性
│       ├── test_performance/             # 缓存性能
│       ├── test_providers/               # 文件读取器
│       ├── test_query_understanding/     # 查询理解（分类器 / HyDE / 多查询 / 路由）
│       ├── test_reranking/               # 重排序（基类 / BGE / Cohere / 管理器）
│       ├── test_services/                # 服务层（工厂 / Bundle / 异常 / 协议）
│       ├── test_advanced_config.py       # 高级配置测试
│       ├── test_full_pipeline.py         # 完整管线集成测试
│       ├── test_rag_engine.py            # RAG 引擎测试
│       ├── test_task_queue.py            # 任务队列测试
│       ├── test_task_queue_models.py     # 任务队列模型测试
│       └── test_worker.py                # Worker 进程测试
├── docs/                                 # 设计与部署文档
│   └── superpowers/                      # 特性设计文档（PRD / 技术方案）
├── docker-compose.yml                    # Docker 全栈编排（8 容器：ES / Redis / PostgreSQL / Neo4j / MinIO / Backend / Worker / Frontend）
├── Dockerfile                            # 后端镜像构建
├── nginx.conf                            # Nginx 反向代理配置
├── .env.example                          # 环境变量模板
├── start.bat                             # Windows 启动脚本
├── stop.bat                              # Windows 停止脚本
├── dev-start.bat                         # Windows 开发环境启动
├── dev-stop.bat                          # Windows 开发环境停止
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
| 内存 | 8 GB+ | 本地 Embedding 模型约 2 GB |
| 磁盘 | 10 GB+ | 模型文件 + 向量数据 |
| GPU | 可选 | CUDA 12.1+ 加速 Embedding / OCR |

> 无 GPU 可使用云端 Embedding（`EMBEDDING_PROVIDER=siliconflow` 或 `tongyi`），无需本地加载模型。

---

## 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/your-username/datapilotai.git
cd datapilotai
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，至少需要 LLM API Key：

```bash
# 必填
MIMO_API_KEY=your_siliconflow_api_key

# 可选：使用云端 Embedding 免本地模型下载
EMBEDDING_PROVIDER=siliconflow
SILICONFLOW_API_KEY=your_siliconflow_api_key
```

### 3. 启动后端

```bash
cd backend
pip install -r requirements.txt

# 安装 PyTorch（按硬件选择）
pip install torch                          # CPU
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

### 5. Docker Compose 一键部署

```bash
cp .env.example .env
# 编辑 .env 填入 API Key

docker compose up -d
```

| 服务 | 地址 | 说明 |
|------|------|------|
| 前端 | http://localhost | Nginx 托管 Vue SPA |
| 后端 API | http://localhost:8000 | FastAPI 服务 |
| Swagger 文档 | http://localhost:8000/docs | 交互式 API 文档 |
| Redis | localhost:6381 | L2 缓存 / 任务队列 |
| Elasticsearch | localhost:9200 | 向量 + 全文混合检索 |
| PostgreSQL | localhost:5433 | 用户 / 对话 / 文档元数据 |
| Neo4j | localhost:7687 | 知识图谱存储 |
| MinIO Console | localhost:9001 | 文件对象存储管理 |

---

## API 接口一览

### 认证

| 接口 | 方法 | 说明 | 认证 |
|------|------|------|------|
| `/api/auth/register` | POST | 用户注册 | 否 |
| `/api/auth/login` | POST | 用户登录 | 否 |
| `/api/auth/me` | GET | 当前用户信息 | 是 |

### 对话

| 接口 | 方法 | 说明 | 认证 |
|------|------|------|------|
| `/api/chat` | POST | 发送消息（SSE 流式） | 是 |
| `/api/conversations` | GET | 对话列表 | 是 |
| `/api/conversations` | DELETE | 清空对话 | 是 |
| `/api/conversations/{conv_id}` | GET | 对话详情 | 是 |
| `/api/conversations/{conv_id}` | DELETE | 删除对话 | 是 |
| `/api/conversations/{conv_id}` | PATCH | 更新对话（标题 / 收藏 / 归档） | 是 |
| `/api/conversations/{conv_id}/duplicate` | POST | 复制对话 | 是 |
| `/api/conversations/{conv_id}/share` | POST | 分享对话 | 是 |

### 文档

| 接口 | 方法 | 说明 | 认证 |
|------|------|------|------|
| `/api/upload` | POST | 单文件上传 | 是 |
| `/api/upload/batch` | POST | 批量上传 | 是 |
| `/api/knowledgebases/{kb_id}/upload` | POST | 上传到指定知识库 | 是 |
| `/api/documents` | GET | 文档列表 | 是 |
| `/api/documents/overview` | GET | 文档概览 | 是 |
| `/api/documents/detail` | GET | 文档详情 | 是 |
| `/api/documents/{source}` | DELETE | 删除文档 | 是 |
| `/api/documents` | DELETE | 清空文档 | 是 |
| `/api/documents/load` | POST | 加载本地文档 | 是 |
| `/api/documents/sync` | POST | 增量同步 | 是 |
| `/api/tasks/{task_id}` | GET | 异步任务状态 | 是 |
| `/api/batches/{batch_id}` | GET | 批量任务状态 | 是 |
| `/api/stats` | GET | 系统统计 | 是 |

### 知识库

| 接口 | 方法 | 说明 | 认证 |
|------|------|------|------|
| `/api/knowledgebases` | GET | 知识库列表 | 是 |
| `/api/knowledgebases` | POST | 创建知识库 | 是 |
| `/api/knowledgebases/{kb_id}` | GET | 知识库详情 | 是 |
| `/api/knowledgebases/{kb_id}` | PUT | 更新知识库 | 是 |
| `/api/knowledgebases/{kb_id}` | DELETE | 删除知识库 | 是 |
| `/api/knowledgebases/{kb_id}/documents` | GET | 知识库文档列表 | 是 |

### 标签知识库

| 接口 | 方法 | 说明 | 认证 |
|------|------|------|------|
| `/api/tag-kb` | GET | 标签知识库列表 | 是 |
| `/api/tag-kb/upload` | POST | 上传标签知识库 | 是 |
| `/api/tag-kb/{tag_kb_id}` | DELETE | 删除标签知识库 | 是 |
| `/api/tag-kb/{tag_kb_id}/tags` | GET | 标签列表 | 是 |

### 模型管理

| 接口 | 方法 | 说明 | 认证 |
|------|------|------|------|
| `/api/models` | GET | 模型列表 | 是 |
| `/api/models` | POST | 添加模型 | 是 |
| `/api/models/types` | GET | 模型类型列表 | 是 |
| `/api/models/factories` | GET | 模型工厂列表 | 是 |
| `/api/models/defaults` | GET | 默认模型配置 | 是 |
| `/api/models/default` | POST | 设置默认模型 | 是 |
| `/api/models/{model_id}` | GET | 模型详情 | 是 |
| `/api/models/{model_id}` | PUT | 更新模型 | 是 |
| `/api/models/{model_id}` | DELETE | 删除模型 | 是 |

### 知识图谱

| 接口 | 方法 | 说明 | 认证 |
|------|------|------|------|
| `/api/graph/data` | GET | 图谱可视化数据 | 是 |
| `/api/graph/search` | GET | 图谱搜索 | 是 |
| `/api/graph/stats` | GET | 图谱统计 | 是 |

### 设置/团队/评测

| 接口 | 方法 | 说明 | 认证 |
|------|------|------|------|
| `/api/settings/rag` | GET | RAG 系统设置 | 是 |
| `/api/settings/rag` | PUT | 更新 RAG 设置 | 是 |
| `/api/team/members` | GET | 团队成员列表 | 是 |
| `/api/team/members/{user_id}` | PUT | 更新成员角色 | 是 |
| `/api/team/members/{user_id}` | DELETE | 移除成员 | 是 |
| `/api/team/invite` | POST | 邀请成员 | 是 |
| `/api/metrics` | GET | 系统性能指标 | 是 |
| `/api/eval/reports` | GET | 评测报告列表 | 是 |
| `/api/eval/reports/{filename}` | GET | 评测报告详情 | 是 |
| `/health` | GET | 健康检查 | 否 |

---

## 核心环境变量

### LLM & Embedding

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `MIMO_API_KEY` | LLM API Key（**必填**） | - |
| `MIMO_API_BASE` | LLM API 地址 | `https://api.siliconflow.cn/v1` |
| `MIMO_MODEL` | LLM 模型 | `mimo-v2.5` |
| `EMBEDDING_PROVIDER` | `sentence-transformer` / `siliconflow` / `tongyi` | `sentence-transformer` |
| `DASHSCOPE_API_KEY` | 通义千问 API Key | - |
| `DASHSCOPE_EMBEDDING_MODEL` | 通义 Embedding 模型 | `text-embedding-v3` |
| `SILICONFLOW_API_KEY` | SiliconFlow API Key | - |

### 知识图谱

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `GRAPHRAG_ENABLED` | 启用知识图谱 | `false` |
| `GRAPHRAG_METHOD` | 抽取策略：`general` / `light` / `ner` | `general` |
| `GRAPHRAG_ENABLE_COMMUNITY` | 启用社区发现 | `true` |
| `GRAPHRAG_PAGERANK_ENABLED` | 启用 PageRank | `true` |
| `NEO4J_URI` | Neo4j 连接地址 | `bolt://localhost:7687` |
| `NEO4J_USER` | Neo4j 用户 | `neo4j` |
| `NEO4J_PASSWORD` | Neo4j 密码 | `neo4jtest` |
| `USE_KNOWLEDGE_GRAPH` | 启用知识图谱集成 | `false` |

### RAPTOR

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `ENABLE_RAPTOR` | 启用 RAPTOR | `false` |
| `RAPTOR_MAX_CLUSTERS` | 最大聚类数 | `64` |
| `RAPTOR_CLUSTERING_METHOD` | 聚类方法：`gmm` / `kmeans` / `hdbscan` | `gmm` |
| `RAPTOR_MAX_DEPTH` | 最大递归深度 | `3` |

### 重排序

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `RERANK_STRATEGY` | `cohere` / `bge` / `siliconflow` / `dashscope` / `hybrid` | `cohere` |
| `DASHSCOPE_RERANKER_MODEL` | DashScope 重排序模型 | `gte-rerank` |
| `RERANK_TOP_K` | 重排序保留数 | `15` |

### 存储

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `VECTOR_STORE_PROVIDER` | 向量存储（仅支持 `elasticsearch`） | `elasticsearch` |
| `ES_HOSTS` | ES 地址 | `http://localhost:9200` |
| `ES_INDEX_PREFIX` | 索引前缀 | `datapilotai` |
| `MINIO_ENDPOINT` | MinIO 地址 | `localhost:9000` |
| `MINIO_ACCESS_KEY` | MinIO 访问密钥 | `minioadmin` |
| `MINIO_BUCKET` | MinIO 存储桶 | `datapilotai-files` |

### 任务队列

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `REDIS_URL` | Redis 连接串（任务队列用） | `redis://localhost:6379/0` |
| `WORKER_CONCURRENCY` | Worker 并发数 | `4` |
| `WORKER_MAX_RETRIES` | 最大重试次数 | `3` |
| `TASK_TTL_HOURS` | 任务过期时间（小时） | `24` |

### LLM 增强（文档分块后）

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `ENABLE_AUTO_KEYWORDS` | 自动提取关键词 | `false` |
| `ENABLE_AUTO_QUESTIONS` | 自动生成问题 | `false` |
| `ENABLE_CONTENT_TAGGING` | 内容标签分类 | `false` |

> 完整配置项请参考 [`.env.example`](.env.example) 与 `backend/core/config.py`

---

## 关键功能配置

### 分块策略

```bash
CHUNKING_STRATEGY=semantic       # semantic / fixed_size / recursive / parent_child
CHUNK_SIZE=512
CHUNK_OVERLAP=50
```

### 多路检索

```bash
PARALLEL_RETRIEVAL=true          # 向量 + BM25 并行
RRF_WEIGHT_VECTOR=0.7
RRF_WEIGHT_BM25=0.3
```

### 查询扩展

```bash
USE_HYDE=true                    # HyDE 假设性文档
MULTI_QUERY_ENABLED=true         # 多查询变体
MULTI_QUERY_COUNT=3
```

### 缓存

```bash
USE_CACHE=true
USE_REDIS=false                  # 需要 Redis 实例
SEMANTIC_CACHE_ENABLED=true      # 语义缓存去重
```

---

## 架构设计

### 服务分层

项目采用四层架构设计：

```
API 路由层（api/）          → HTTP 请求 / 响应，认证，参数校验
     │
Service 服务层（core/services/） → 业务逻辑编排（Retrieval / Ingestion / Generation）
     │
InfraBundle 基础设施层      → 所有共享依赖容器（Embedding / VectorStore / LLM / OCR / Cache 等）
     │
Provider 提供商层（core/providers/） → 可插拔组件实现（Elasticsearch / SiliconFlow / 读取器等）
```

### InfraBundle 依赖注入

项目使用 `InfraBundle`（DataClass）作为所有共享依赖的容器，由 `create_infra()` 工厂组装：

```
create_infra(settings)
  ├─ 核心三件套（Embedding / VectorStore / LLM）
  ├─ 可选组件（OCR / VLM / 文件读取器 / 分块策略）
  ├─ 检索增强（Query Understanding / Reranking / Cache）
  ├─ 验证与可观测性
  └─ 知识图谱（Neo4j / Extractor / Retriever）
```

### 异步任务架构

```
用户上传文档 → API 生成任务 → Redis Stream → Worker 进程消费
                                                    │
                                          ┌─────────┴──────────┐
                                          │ 解析 → 分块 → 向量化 │
                                          │ → 索引 → 标记完成    │
                                          └────────────────────┘
```

### 查询链路

```
用户问题 → 查询理解（分类/重写/HyDE/多查询）
         → 多路召回（稠密向量 + 稀疏 BM25 + 图谱检索）
         → RRF 融合
         → Cross-Encoder 重排序
         → 置信度评估（低置信度触发补召回或拒答）
         → 构建 Prompt + 引用验证
         → LLM 流式生成
```

---

## 功能使用指南

### 文档管理

通过前端或 API 上传文档：

```bash
# 单文件上传
curl -X POST http://localhost:8000/api/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@document.pdf"

# 上传到指定知识库
curl -X POST http://localhost:8000/api/knowledgebases/{kb_id}/upload \
  -H "Authorization: Bearer <token>" \
  -F "files=@doc1.pdf -F "files=@doc2.md"
```

支持格式：`.pdf` `.docx` `.md` `.txt` `.html` `.png` `.jpg` `.jpeg` `.bmp` `.tiff` `.xlsx` `.csv` `.pptx` `.json` `.mp3` `.wav` `.m4a`

### 对话问答

```bash
# RAG 模式（基于知识库检索）
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"query": "什么是 RAG？", "mode": "rag", "conversation_id": "可选"}'

# 直接模式（纯 LLM）
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"query": "解释 Transformer 架构", "mode": "direct"}'
```

### 知识图谱（GraphRAG）

```bash
# .env 启用
GRAPHRAG_ENABLED=true
GRAPHRAG_METHOD=general    # general / light / ner
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=neo4jtest
```

文档摄取时自动抽取实体关系写入 Neo4j，查询时图检索 + 向量检索融合。

### RAPTOR 层级摘要

```bash
ENABLE_RAPTOR=true
RAPTOR_MAX_CLUSTERS=64
RAPTOR_CLUSTERING_METHOD=gmm   # gmm / kmeans / hdbscan
RAPTOR_MAX_DEPTH=3
```

### 内容标签（Content Tagging）

```bash
ENABLE_CONTENT_TAGGING=true
CONTENT_TAG_TOPN=3
CONTENT_TAG_KB_IDS=tag_kb_id1,tag_kb_id2
```

### VLM 统一提取器

```bash
USE_VLM_EXTRACTOR=true
VLM_EXTRACTOR_API_KEY=your_dashscope_api_key
VLM_EXTRACTOR_MODEL=qwen-vl-max
```

图片/PDF → VLMExtractor（版面分析）→ 按区域类型分块 → 查询时原图附带给多模态 LLM。

### 评测与基准测试

```bash
cd backend

# 全量评测
python eval/run_eval.py --framework both

# A/B 测试
python eval/ab_runner.py --config-a .env.variant_a --config-b .env.variant_b

# 配置对比
python eval/config_comparator.py --preset chunking

# 重排序基准测试
python eval/reranker_benchmark.py

# 性能基准测试
python eval/performance_benchmark.py

# 分维度评测
python eval/dimensional_eval.py
```

---

## 开发者指南

### 新增 Provider

1. 在 `backend/core/providers/` 下实现新 Provider 类，设置 `_FACTORY_NAME`
2. 通过 `ProviderFactory` 自动发现注册
3. 在 `config.py` 中添加对应配置项
4. 在 `infra_factory.py` 的条件分支中集成

### 代码规范

- Python：PEP 8，类型注解覆盖公开接口
- Vue：Composition API + `<script setup>`
- 提交信息：[Conventional Commits](https://www.conventionalcommits.org/)
- 提交类型：`feat` / `fix` / `docs` / `test` / `refactor` / `perf`

### 运行测试

```bash
# 全部测试
python -m pytest tests/ -v

# 按模块
python -m pytest tests/unit/test_kg/ -v           # 知识图谱
python -m pytest tests/unit/test_services/ -v     # 服务层
python -m pytest tests/unit/test_query_understanding/ -v
python -m pytest tests/unit/test_reranking/ -v
python -m pytest tests/unit/test_chunking/ -v
python -m pytest tests/unit/test_eval/ -v
python -m pytest tests/unit/test_performance/ -v
python -m pytest tests/unit/test_providers/ -v    # 文件读取器
```

---

## 低配环境适配

```bash
# 全云端组件
EMBEDDING_PROVIDER=siliconflow
RERANK_STRATEGY=siliconflow

# 关闭可选模块
SEMANTIC_CACHE_ENABLED=false
SELF_RAG_ENABLED=false
GRAPHRAG_ENABLED=false
ENABLE_RAPTOR=false
OCR_PROVIDER=none
USE_VLM=false
```

---

## 开源许可

MIT License

---

## 贡献

欢迎 Pull Request 或提交 Issue。提交前请确保测试通过，遵循 Conventional Commits 规范。