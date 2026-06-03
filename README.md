# AI 应用开发知识问答助手

> 基于 RAG（检索增强生成）技术的智能问答系统，支持混合检索、查询扩展、重排序等高级功能

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![Vue.js](https://img.shields.io/badge/Vue.js-3.x-brightgreen.svg)](https://vuejs.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 目录

- [功能特性](#功能特性)
- [技术栈](#技术栈)
- [项目结构](#项目结构)
- [快速开始](#快速开始)
- [配置说明](#配置说明)
- [API 文档](#api-文档)
- [测试](#测试)
- [架构设计](#架构设计)
- [贡献指南](#贡献指南)
- [许可证](#许可证)

---

## 功能特性

### 核心功能

- **智能问答**：基于知识库回答 AI 应用开发技术问题
- **流式回答**：SSE 实时推送，逐 token 显示生成过程
- **引用追溯**：展示回答依据的文档片段和来源
- **对话管理**：多轮对话、历史记录持久化
- **文档管理**：支持上传、删除、批量加载自定义文档

### 高级检索功能（新增）

- **混合检索**：向量检索 + BM25 关键词检索，RRF 融合排序
- **查询理解**：自动识别查询意图（事实型、分析型、步骤型、探索型）
- **查询扩展**：
  - HyDE（假设性文档嵌入）：生成假设性文档提升召回率
  - 多查询生成：自动生成多个查询变体
- **智能重排序**：
  - Cohere Reranker（云端）
  - BGE Reranker（本地）
  - 混合重排序策略
- **动态路由**：根据查询复杂度自动选择最优检索策略

### 系统能力

- **结构化日志**：JSON 格式日志，支持日志聚合和分析
- **多级缓存**：LRU 内存缓存，支持 TTL 过期和容量限制
- **性能监控**：检索延迟、缓存命中率等指标追踪
- **错误恢复**：各模块支持优雅降级，确保系统稳定性

---

## 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| 前端框架 | Vue 3 + Vite | 响应式 UI |
| UI 组件 | Element Plus | 组件库 |
| 状态管理 | Pinia | 轻量级状态管理 |
| 后端框架 | FastAPI | 异步高性能 API |
| 流式传输 | SSE | Server-Sent Events |
| 大模型 | MiMo-v2.5 | 云端 API |
| Embedding | bge-small-zh-v1.5 | 本地推理 |
| 向量数据库 | ChromaDB | 嵌入式存储 |
| 重排序 | Cohere / BGE | 多策略支持 |
| 日志 | structlog | 结构化日志 |
| 缓存 | 自实现 LRU | 多级缓存 |

---

## 项目结构

```
Agent智能助手/
├── backend/                        # FastAPI 后端
│   ├── main.py                     # 应用入口
│   ├── requirements.txt            # Python 依赖
│   ├── api/                        # API 接口
│   │   ├── chat.py                 # 对话 API (SSE 流式)
│   │   ├── conversations.py        # 对话历史 API
│   │   └── documents.py            # 文档管理 API
│   └── core/                       # 核心模块
│       ├── advanced_config.py      # 高级配置管理
│       ├── rag_engine.py           # RAG 核心引擎
│       ├── embedding_service.py    # Embedding 服务
│       ├── vector_store.py         # 向量数据库封装
│       ├── llm_client.py           # LLM API 客户端
│       ├── document_processor.py   # 文档解析与分块
│       ├── bm25_retriever.py       # BM25 关键词检索
│       ├── query_understanding/    # 查询理解模块
│       │   ├── classifier.py       # 查询意图分类器
│       │   ├── hyde_generator.py   # HyDE 假设性文档生成
│       │   ├── multi_query.py      # 多查询生成器
│       │   └── router.py           # 动态路由器
│       ├── reranking/              # 重排序模块
│       │   ├── base.py             # 重排序器抽象基类
│       │   ├── cohere_reranker.py  # Cohere Reranker 实现
│       │   ├── bge_reranker.py     # BGE Reranker 实现
│       │   └── manager.py          # 重排序策略管理器
│       ├── observability/          # 可观测性模块
│       │   └── logger.py           # 结构化日志系统
│       └── performance/            # 性能优化模块
│           └── cache/              # 多级缓存系统
│               ├── l1_cache.py     # L1 内存缓存
│               └── manager.py      # 缓存管理器
├── frontend/                       # Vue 3 前端
│   ├── src/
│   │   ├── App.vue                 # 根组件 (三栏布局)
│   │   ├── main.js                 # 入口
│   │   ├── style.css               # 全局样式
│   │   ├── api/index.js            # API 接口封装
│   │   ├── stores/chat.js          # Pinia 状态管理
│   │   └── components/
│   │       ├── ChatSidebar.vue     # 左侧栏 (历史对话)
│   │       ├── ChatView.vue        # 主对话区
│   │       ├── ChatMessage.vue     # 消息气泡
│   │       └── DocumentPanel.vue   # 文档管理面板
│   ├── package.json
│   └── vite.config.js
├── tests/                          # 测试套件
│   └── unit/                       # 单元测试
│       ├── test_advanced_config.py
│       ├── test_query_understanding/
│       ├── test_reranking/
│       ├── test_observability/
│       └── test_performance/
├── data/                           # 数据目录
│   ├── python-docs/                # 知识库文档
│   └── conversations/              # 对话记录
├── docs/                           # 文档
│   ├── superpowers/plans/          # 实施计划
│   └── superpowers/specs/          # 设计规格
├── .env.example                    # 环境变量模板
└── README.md                       # 本文件
```

---

## 快速开始

### 前置要求

- Python 3.11+
- Node.js 18+
- npm 或 yarn

### 1. 克隆项目

```bash
git clone https://github.com/your-username/agent-smart-assistant.git
cd agent-smart-assistant
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入你的配置：

```bash
MIMO_API_KEY=your_api_key_here       # MiMo API Key
MIMO_API_BASE=https://api.siliconflow.cn/v1
MIMO_MODEL=mimo-v2.5
EMBEDDING_MODEL_PATH=./models/bge-small-zh-v1.5
CHROMA_PERSIST_DIR=./backend/chroma_db
DATA_DIR=./data/python-docs

# 可选：Cohere Reranker
COHERE_API_KEY=your_cohere_api_key
```

### 3. 启动后端

```bash
cd backend
pip install -r requirements.txt
python main.py
# 后端运行在 http://localhost:8000
```

### 4. 启动前端

```bash
cd frontend
npm install
npm run dev
# 前端运行在 http://localhost:5173
```

### 5. 加载文档

在右侧文档管理面板中点击"加载本地文档"，或拖拽上传自定义文档。

---

## 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `MIMO_API_KEY` | MiMo API Key | 必填 |
| `MIMO_API_BASE` | API 地址 | `https://api.siliconflow.cn/v1` |
| `MIMO_MODEL` | 模型名称 | `mimo-v2.5` |
| `EMBEDDING_MODEL_PATH` | Embedding 模型路径 | `./models/bge-small-zh-v1.5` |
| `CHROMA_PERSIST_DIR` | 向量数据库目录 | `./backend/chroma_db` |
| `DATA_DIR` | 文档目录 | `./data/python-docs` |

### 高级配置

在 `backend/core/advanced_config.py` 中可以调整：

- **查询扩展**：`USE_HYDE`、`MULTI_QUERY_COUNT`
- **重排序**：`RERANK_STRATEGY`（cohere/bge/hybrid）、`RERANK_TOP_K`
- **缓存**：`USE_CACHE`、`CACHE_L1_MAX_SIZE`、`CACHE_L1_TTL`
- **日志**：`LOG_LEVEL`、`LOG_FORMAT`

---

## API 文档

启动后端后，访问 http://localhost:8000/docs 查看 Swagger API 文档。

### 主要接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/chat` | POST | 发送消息（SSE 流式响应） |
| `/api/conversations` | GET | 获取对话列表 |
| `/api/conversations/{id}` | GET | 获取单个对话详情 |
| `/api/documents` | GET | 获取文档列表 |
| `/api/documents/upload` | POST | 上传文档 |
| `/api/documents/{id}` | DELETE | 删除文档 |

### 请求示例

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "什么是RAG？",
    "conversation_id": "optional-conversation-id"
  }'
```

---

## 测试

### 运行测试

```bash
# 运行所有测试
python -m pytest tests/ -v

# 运行特定模块测试
python -m pytest tests/unit/test_query_understanding/ -v
python -m pytest tests/unit/test_reranking/ -v

# 运行并显示覆盖率
python -m pytest tests/ --cov=backend --cov-report=html
```

### 测试覆盖

| 模块 | 测试文件 | 测试数量 |
|------|----------|----------|
| 高级配置 | `test_advanced_config.py` | 5 |
| 查询理解 | `test_query_understanding/` | 14 |
| 重排序 | `test_reranking/` | 17 |
| 可观测性 | `test_observability/` | 4 |
| 性能优化 | `test_performance/` | 7 |
| **总计** | - | **62** |

---

## 架构设计

### 检索管线

```
用户查询
    ↓
┌─────────────────────────────────────────┐
│  Stage 1: 查询理解与扩展               │
│  - 查询意图分类                         │
│  - HyDE 假设性文档生成                  │
│  - 多查询生成                           │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│  Stage 2: 多路召回                      │
│  - 向量检索（ChromaDB）                 │
│  - BM25 关键词检索                      │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│  Stage 3: 结果融合                      │
│  - 加权 RRF 融合                        │
│  - 相似度阈值过滤                       │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│  Stage 4: 重排序                        │
│  - Cross-Encoder 精排                   │
│  - 业务规则过滤                         │
└─────────────────────────────────────────┘
    ↓
检索结果输出
```

### 设计文档

详细设计文档位于 `docs/superpowers/specs/` 目录：

- [2026-06-03-advanced-rag-retrieval-design.md](docs/superpowers/specs/2026-06-03-advanced-rag-retrieval-design.md)

---

## 贡献指南

欢迎贡献！请遵循以下步骤：

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/your-feature`)
3. 提交更改 (`git commit -m 'feat: add your feature'`)
4. 推送到分支 (`git push origin feature/your-feature`)
5. 创建 Pull Request

### 提交规范

使用 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

- `feat:` 新功能
- `fix:` Bug 修复
- `docs:` 文档更新
- `test:` 测试相关
- `refactor:` 代码重构

---

## 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

---

## 致谢

- [FastAPI](https://fastapi.tiangolo.com/) - 高性能 Python Web 框架
- [Vue.js](https://vuejs.org/) - 渐进式 JavaScript 框架
- [ChromaDB](https://www.trychroma.com/) - 向量数据库
- [sentence-transformers](https://www.sbert.net/) - 文本向量化工具
- [Cohere](https://cohere.com/) - Reranker API
