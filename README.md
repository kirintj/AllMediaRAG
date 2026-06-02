# AI 应用开发知识问答助手

基于 RAG（检索增强生成）技术的 AI 应用开发知识问答系统，涵盖 Agent、RAG、Prompt Engineering、Fine-tuning 等核心知识点。

## 功能特性

- **智能问答**：基于知识库回答 AI 应用开发技术问题
- **流式回答**：SSE 实时推送，逐 token 显示生成过程
- **引用追溯**：展示回答依据的文档片段和来源
- **对话管理**：多轮对话、历史记录持久化
- **文档管理**：支持上传、删除、批量加载自定义文档
- **深色模式**：支持浅色/深色主题切换

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端框架 | Vue 3 + Vite |
| UI 组件 | Element Plus |
| 状态管理 | Pinia |
| 后端框架 | FastAPI |
| 流式传输 | SSE (Server-Sent Events) |
| 大模型 | MiMo-v2.5（云端 API） |
| Embedding | bge-small-zh-v1.5（本地推理） |
| 向量数据库 | ChromaDB（嵌入式） |

## 项目结构

```
Agent智能助手/
├── backend/                    # FastAPI 后端
│   ├── main.py                 # 应用入口
│   ├── requirements.txt        # Python 依赖
│   ├── api/
│   │   ├── chat.py             # 对话 API (SSE 流式)
│   │   ├── documents.py        # 文档管理 API
│   │   └── conversations.py    # 对话历史 API
│   └── chroma_db/              # 向量数据库 (运行时生成)
├── frontend/                   # Vue 3 前端
│   ├── src/
│   │   ├── App.vue             # 根组件 (三栏布局)
│   │   ├── main.js             # 入口
│   │   ├── style.css           # 全局样式 (HM Design)
│   │   ├── api/index.js        # API 接口封装
│   │   ├── stores/chat.js      # Pinia 状态管理
│   │   └── components/
│   │       ├── ChatSidebar.vue # 左侧栏 (历史对话)
│   │       ├── ChatView.vue    # 主对话区
│   │       ├── ChatMessage.vue # 消息气泡
│   │       └── DocumentPanel.vue # 文档管理面板
│   ├── package.json
│   └── vite.config.js
├── config.py                   # 配置管理
├── rag_engine.py               # RAG 核心引擎
├── embedding_service.py        # Embedding 服务
├── vector_store.py             # 向量数据库封装
├── llm_client.py               # LLM API 客户端
├── document_processor.py       # 文档解析与分块
├── data/
│   ├── python-docs/            # 知识库文档
│   └── conversations/          # 对话记录 (运行时生成)
├── .env.example                # 环境变量模板
└── docs/                       # 设计文档
```

## 快速开始

### 1. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，填入你的 MiMo API Key
```

### 2. 启动后端

```bash
cd backend
pip install -r requirements.txt
python main.py
# 后端运行在 http://localhost:8000
```

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev
# 前端运行在 http://localhost:5173
```

### 4. 加载文档

在右侧文档管理面板中点击"加载本地文档"，或拖拽上传自定义文档。

## 配置说明

在 `.env` 文件中配置：

```bash
MIMO_API_KEY=your_api_key_here       # MiMo API Key
MIMO_API_BASE=https://api.siliconflow.cn/v1  # API 地址
MIMO_MODEL=mimo-v2.5                 # 模型名称
EMBEDDING_MODEL_PATH=./models/bge-small-zh-v1.5  # Embedding 模型路径
CHROMA_PERSIST_DIR=./backend/chroma_db  # 向量数据库目录
DATA_DIR=./data/python-docs          # 文档目录
```

## 许可证

MIT License
