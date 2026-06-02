# AI Agent 知识问答助手 — 设计规格

## 项目定位

基于 RAG 技术的 AI Agent 知识问答系统，聚焦 Agent 架构、框架对比、记忆系统、训练部署等领域。作为作品集/面试展示项目，重点展示 RAG 全流程技术能力。

## 页面结构

```
/           → Landing 首页
/chat       → 问答视图（RAG 可视化 + 文档管理）
/knowledge  → 知识浏览视图（卡片 + 主题筛选）
```

### Landing 首页

- 项目标题 + 一句话定位
- 两个入口按钮：[开始问答] [探索知识]
- RAG 5 步流程展示：文档解析 → 分块 → 向量化 → 检索 → 生成
- 技术栈标签：FastAPI / Vue 3 / ChromaDB / MiMo / bge
- 知识覆盖统计

### 问答视图 (/chat)

三栏布局：
- **左侧栏**：历史对话列表 + 新建对话
- **中间**：消息列表 + 输入框，消息支持 Markdown 渲染和代码高亮
- **右侧栏**：上半部分 RAG 可视化面板，下半部分文档管理

#### RAG 可视化面板

每次问答后实时展示检索过程：

- 三个状态：检索中（骨架屏）→ 检索完成（卡片淡入）→ 无结果（降级提示）
- 片段卡片展示：文档名、章节标题、相似度（百分比+进度条）、文本预览（可展开）
- 后端 SSE sources 字段扩展：增加 `similarity`、`text_preview`、`topic`

### 知识视图 (/knowledge)

- 顶部搜索框 + 返回问答按钮
- 主题筛选标签栏（6 个主题）
- 知识卡片网格：标题、主题标签、摘要、文档块数
- 点击卡片 → 右侧滑出详情抽屉，渲染 Markdown 原文
- 详情抽屉操作：[向它提问] 跳转 `/chat` 并自动填入问题

#### 主题分类

| 主题 | 包含文档 |
|------|----------|
| Agent 架构 | 01-基础概念、06-OpenClaw架构 |
| 框架对比 | 05-LangGraph、07-横向调研、09-详细对比、10-深度对比 |
| SDK 选型 | 04-三大SDK对比 |
| 训练部署 | 08-SFT到部署、11-RL实战 |
| 面试准备 | 03-面试指南、Agent岗面试题 |
| 项目实战 | 02-Claude Code架构 |

## 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| 前端框架 | Vue 3 + Vite | 保留 |
| UI 组件 | Element Plus | 保留 |
| 状态管理 | Pinia | 保留 |
| 路由 | Vue Router 4 | 新增 |
| Markdown | marked + highlight.js | 新增 |
| 后端框架 | FastAPI | 保留 |
| 流式传输 | SSE | 保留 |
| 大模型 | MiMo-v2.5 | 保留 |
| Embedding | bge-small-zh-v1.5 | 保留 |
| 向量数据库 | ChromaDB | 保留 |

## 后端 API 设计

### 保留现有

```
POST /api/chat                → SSE 流式对话
GET  /api/documents           → 文档列表
POST /api/upload              → 上传文档
POST /api/documents/load      → 批量加载
DELETE /api/documents/{name}  → 删除文档
DELETE /api/documents         → 清空文档
GET  /api/stats               → 统计信息
GET  /api/conversations       → 对话列表
GET  /api/conversations/{id}  → 对话详情
DELETE /api/conversations/{id} → 删除对话
DELETE /api/history            → 清空历史
```

### 新增

```
GET /api/knowledge/topics         → 主题列表
GET /api/knowledge/cards?topic=x  → 卡片列表（支持主题筛选和搜索）
GET /api/knowledge/cards/{id}     → 卡片详情（完整 Markdown）
```

### SSE sources 扩展

```json
{
  "sources": [
    {
      "source": "01-Agent基础概念学习笔记.md",
      "section": "Agent 核心组件",
      "similarity": 0.87,
      "text_preview": "Agent 的核心组件包括...",
      "topic": "agent-arch"
    }
  ]
}
```

## 数据模型

### 文档 metadata 扩展

```python
{
    "source": "01-Agent基础概念学习笔记.md",
    "section": "什么是 Agent",
    "chunk_index": 0,
    "topic": "agent-arch",           # 新增
    "doc_id": "01",                  # 新增
    "title": "Agent 基础概念学习笔记"   # 新增
}
```

### 主题映射配置（config.py）

```python
KNOWLEDGE_TOPICS = {
    "agent-arch": {
        "name": "Agent 架构",
        "files": [
            "01-Agent基础概念学习笔记.md",
            "06-OpenClaw_Agent架构与记忆系统.md"
        ]
    },
    "framework-compare": {
        "name": "框架对比",
        "files": [
            "05-LangGraph核心概念.md",
            "07-Agent框架横向调研索引.md",
            "09-Agent框架详细对比与选型.md",
            "10-Agent框架深度对比续-Mastra-SK-Eino-AU-Vercel.md"
        ]
    },
    "sdk-select": {
        "name": "SDK 选型",
        "files": ["04-三大AI_SDK横向对比与选型.md"]
    },
    "train-deploy": {
        "name": "训练部署",
        "files": [
            "08-Agent训练实战从SFT到部署.md",
            "11-Agent_RL实战与评测部署全流程.md"
        ]
    },
    "interview": {
        "name": "面试准备",
        "files": [
            "03-面试准备与项目讲述指南.md",
            "Agent岗面试题完整汇总.md"
        ]
    },
    "project": {
        "name": "项目实战",
        "files": ["02-Claude_Code_Agent架构深度解析.md"]
    }
}
```

## 前端组件结构

```
App.vue
├── views/
│   ├── LandingPage.vue         # 首页
│   ├── ChatPage.vue            # 问答页（三栏容器）
│   └── KnowledgePage.vue       # 知识浏览页
├── components/
│   ├── ChatSidebar.vue         # 历史对话
│   ├── ChatView.vue            # 消息区 + 输入框
│   ├── ChatMessage.vue         # 消息气泡（增强 Markdown）
│   ├── DocumentPanel.vue       # 文档管理（精简）
│   ├── RagVisualization.vue    # RAG 可视化面板
│   ├── SourceCard.vue          # 检索结果卡片
│   ├── KnowledgeCard.vue       # 知识卡片
│   ├── KnowledgeDetail.vue     # 知识详情抽屉
│   └── TopicFilter.vue         # 主题筛选标签栏
├── stores/
│   ├── chat.js                 # 对话状态（保留）
│   └── knowledge.js            # 知识库状态（新增）
└── router/
    └── index.js                # 路由配置（新增）
```

### knowledge store

```javascript
state: {
  topics: [],
  cards: [],
  activeTopic: null,
  selectedCard: null,
  searchQuery: '',
  loading: false
}
```

## 错误处理

| 场景 | 处理 |
|------|------|
| LLM API 超时/失败 | SSE 返回 error，前端显示错误气泡 |
| 检索无结果 | 降级直接对话，RAG 面板显示"未找到相关内容" |
| 文档上传失败 | Toast 提示具体原因 |
| 后端不可达 | 统一拦截，连接失败提示 |
| 知识卡片加载失败 | 骨架屏替换为"加载失败，点击重试" |
| 空文档库 | 引导用户上传文档 |
| 搜索无结果 | 提示文字 + 清除搜索按钮 |

## 改动范围汇总

| 类型 | 改动 |
|------|------|
| 新增页面 | LandingPage、KnowledgePage |
| 新增组件 | RagVisualization、SourceCard、KnowledgeCard、KnowledgeDetail、TopicFilter |
| 新增后端 | `api/knowledge.py`，3 个接口 |
| 新增 store | `knowledge.js` |
| 新增依赖 | vue-router@4、marked、highlight.js |
| 修改 | config.py（主题映射）、document_processor.py（metadata 扩展）、rag_engine.py（sources 扩展）、chat.py（sources 返回）、ChatMessage.vue（Markdown 渲染） |
| 保留 | RAG 引擎核心、对话管理、文档管理、全部现有 API |
