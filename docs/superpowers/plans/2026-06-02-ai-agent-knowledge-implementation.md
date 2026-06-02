# AI Agent 知识问答助手 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 扩展现有 RAG 系统，新增知识浏览视图和 RAG 可视化面板，实现完整的多页面知识问答应用。

**Architecture:** 基于 Vue Router 实现多页面架构，新增 Knowledge API 提供主题和卡片数据，扩展 SSE sources 字段携带检索元数据，使用 marked + highlight.js 实现 Markdown 渲染。

**Tech Stack:** Vue 3, Vue Router 4, Pinia, Element Plus, FastAPI, ChromaDB, marked, highlight.js

---

## 文件结构

**新增文件:**
```
frontend/
├── src/
│   ├── router/
│   │   └── index.js              # 路由配置
│   ├── views/
│   │   ├── LandingPage.vue       # Landing 首页
│   │   └── KnowledgePage.vue     # 知识浏览页
│   ├── components/
│   │   ├── RagVisualization.vue  # RAG 可视化面板
│   │   ├── SourceCard.vue        # 检索结果卡片
│   │   ├── KnowledgeCard.vue     # 知识卡片
│   │   ├── KnowledgeDetail.vue   # 知识详情抽屉
│   │   └── TopicFilter.vue       # 主题筛选标签栏
│   └── stores/
│       └── knowledge.js          # 知识库状态

backend/
├── api/
│   └── knowledge.py              # 知识库 API
```

**修改文件:**
```
config.py                         # 添加主题映射配置
document_processor.py             # 扩展 metadata 字段
rag_engine.py                     # 扩展 sources 返回字段
backend/api/chat.py               # 修改 sources 返回
frontend/src/main.js              # 添加 Vue Router
frontend/src/App.vue              # 添加 router-view
frontend/src/api/index.js         # 添加知识库 API 函数
frontend/src/components/ChatMessage.vue  # Markdown 渲染
frontend/src/stores/chat.js       # 扩展 sources 数据
```

---

## Task 1: 安装依赖并配置 Vue Router

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/src/main.js`
- Modify: `frontend/src/App.vue`

- [ ] **Step 1: 安装前端依赖**

```bash
cd frontend
npm install vue-router@4 marked highlight.js
```

- [ ] **Step 2: 创建路由配置文件**

创建 `frontend/src/router/index.js`:

```javascript
import { createRouter, createWebHistory } from 'vue-router'
import LandingPage from '../views/LandingPage.vue'
import ChatPage from '../components/ChatView.vue'
import KnowledgePage from '../views/KnowledgePage.vue'

const routes = [
  {
    path: '/',
    name: 'Landing',
    component: LandingPage
  },
  {
    path: '/chat',
    name: 'Chat',
    component: ChatPage
  },
  {
    path: '/knowledge',
    name: 'Knowledge',
    component: KnowledgePage
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
```

- [ ] **Step 3: 更新 main.js 注册路由**

修改 `frontend/src/main.js`:

```javascript
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import './style.css'
import App from './App.vue'
import router from './router'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(ElementPlus)
app.use(router)
app.mount('#app')
```

- [ ] **Step 4: 更新 App.vue 添加 router-view**

修改 `frontend/src/App.vue`，将当前布局移至 ChatPage，App.vue 只保留 router-view：

```vue
<template>
  <router-view />
</template>

<script setup>
</script>
```

- [ ] **Step 5: 提交变更**

```bash
git add frontend/package.json frontend/package-lock.json frontend/src/router/index.js frontend/src/main.js frontend/src/App.vue
git commit -m "feat: add Vue Router and dependencies for multi-page navigation"
```

---

## Task 2: 创建 Landing 首页

**Files:**
- Create: `frontend/src/views/LandingPage.vue`

- [ ] **Step 1: 创建 LandingPage.vue**

创建 `frontend/src/views/LandingPage.vue`:

```vue
<template>
  <div class="landing-page">
    <div class="hero-section">
      <h1 class="title">AI Agent 知识问答助手</h1>
      <p class="subtitle">基于 RAG 技术的智能问答系统，聚焦 Agent 架构、框架对比、记忆系统等领域</p>

      <div class="action-buttons">
        <el-button type="primary" size="large" @click="$router.push('/chat')">
          开始问答
        </el-button>
        <el-button size="large" @click="$router.push('/knowledge')">
          探索知识
        </el-button>
      </div>
    </div>

    <div class="rag-flow-section">
      <h2>RAG 5 步流程</h2>
      <div class="flow-steps">
        <div class="step" v-for="step in ragSteps" :key="step.id">
          <div class="step-icon">{{ step.icon }}</div>
          <div class="step-label">{{ step.label }}</div>
        </div>
      </div>
    </div>

    <div class="tech-stack-section">
      <h2>技术栈</h2>
      <div class="tech-tags">
        <el-tag v-for="tech in techStack" :key="tech" type="info">
          {{ tech }}
        </el-tag>
      </div>
    </div>

    <div class="stats-section">
      <h2>知识覆盖</h2>
      <div class="stats-grid">
        <div class="stat-item">
          <div class="stat-value">{{ stats.document_count }}</div>
          <div class="stat-label">文档数量</div>
        </div>
        <div class="stat-item">
          <div class="stat-value">{{ stats.source_count }}</div>
          <div class="stat-label">知识来源</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getStats } from '../api'

const stats = ref({ document_count: 0, source_count: 0 })

const ragSteps = [
  { id: 1, icon: '📄', label: '文档解析' },
  { id: 2, icon: '✂️', label: '分块' },
  { id: 3, icon: '🔢', label: '向量化' },
  { id: 4, icon: '🔍', label: '检索' },
  { id: 5, icon: '💡', label: '生成' }
]

const techStack = ['FastAPI', 'Vue 3', 'ChromaDB', 'MiMo', 'bge']

onMounted(async () => {
  try {
    const data = await getStats()
    stats.value = data
  } catch (error) {
    console.error('获取统计失败:', error)
  }
})
</script>

<style scoped>
.landing-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 60px 20px;
}

.hero-section {
  text-align: center;
  max-width: 800px;
  margin: 0 auto 60px;
}

.title {
  font-size: 48px;
  font-weight: bold;
  margin-bottom: 16px;
}

.subtitle {
  font-size: 18px;
  opacity: 0.9;
  margin-bottom: 32px;
}

.action-buttons {
  display: flex;
  gap: 16px;
  justify-content: center;
}

.rag-flow-section,
.tech-stack-section,
.stats-section {
  max-width: 800px;
  margin: 0 auto 40px;
  text-align: center;
}

h2 {
  font-size: 24px;
  margin-bottom: 24px;
}

.flow-steps {
  display: flex;
  justify-content: center;
  gap: 40px;
}

.step {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.step-icon {
  font-size: 48px;
  margin-bottom: 8px;
}

.step-label {
  font-size: 14px;
}

.tech-tags {
  display: flex;
  gap: 12px;
  justify-content: center;
  flex-wrap: wrap;
}

.stats-grid {
  display: flex;
  gap: 60px;
  justify-content: center;
}

.stat-item {
  text-align: center;
}

.stat-value {
  font-size: 48px;
  font-weight: bold;
}

.stat-label {
  font-size: 14px;
  opacity: 0.9;
}
</style>
```

- [ ] **Step 2: 验证页面可访问**

启动开发服务器并访问 http://localhost:5173/，确认 Landing 页面正确显示。

```bash
cd frontend
npm run dev
```

- [ ] **Step 3: 提交变更**

```bash
git add frontend/src/views/LandingPage.vue
git commit -m "feat: add Landing page with RAG flow visualization"
```

---

## Task 3: 扩展后端 - 主题映射配置

**Files:**
- Modify: `config.py`

- [ ] **Step 1: 添加主题映射配置到 config.py**

修改 `config.py`，在 Config 类中添加 KNOWLEDGE_TOPICS：

```python
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """配置管理类，从环境变量加载配置"""

    # MiMo API 配置
    MIMO_API_KEY: str = os.getenv("MIMO_API_KEY", "")
    MIMO_BASE: str = os.getenv("MIMO_BASE", "https://api.siliconflow.cn/v1")
    MIMO_MODEL: str = os.getenv("MIMO_MODEL", "Qwen/Qwen3-8B")

    # Embedding 配置
    EMBEDDING_MODEL_PATH: str = os.getenv("EMBEDDING_MODEL_PATH", "./models/bge-small-zh-v1.5")
    EMBEDDING_DEVICE: str = os.getenv("EMBEDDING_DEVICE", "cpu")

    # ChromaDB 配置
    CHROMA_PERSIST_DIR: str = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")

    # 文档处理配置
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "512"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "50"))

    # RAG 配置
    TOP_K: int = int(os.getenv("TOP_K", "5"))
    SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.3"))
    MAX_HISTORY_TURNS: int = int(os.getenv("MAX_HISTORY_TURNS", "5"))

    # 主题映射配置
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


config = Config()
```

- [ ] **Step 2: 验证配置加载**

```bash
cd backend
python -c "from config import config; print(config.KNOWLEDGE_TOPICS.keys())"
```

预期输出：`dict_keys(['agent-arch', 'framework-compare', 'sdk-select', 'train-deploy', 'interview', 'project'])`

- [ ] **Step 3: 提交变更**

```bash
git add config.py
git commit -m "feat: add knowledge topics mapping configuration"
```

---

## Task 4: 扩展文档处理器 - Metadata 字段

**Files:**
- Modify: `document_processor.py`

- [ ] **Step 1: 修改 process_document 方法添加 topic、doc_id、title 字段**

修改 `document_processor.py` 的 `process_document` 方法：

```python
def process_document(self, html_content: str, source: str, topic: str = None, doc_id: str = None, title: str = None) -> list[dict]:
    """完整文档处理流程，返回带元数据的 chunks

    Args:
        html_content: HTML 内容
        source: 文档来源
        topic: 主题分类
        doc_id: 文档 ID
        title: 文档标题

    Returns:
        带元数据的 chunks 列表
    """
    text = self.parse_html(html_content)
    sections = self.split_by_headings(text)

    all_chunks = []
    for section in sections:
        if len(section["content"]) > self.chunk_size:
            chunks = self.split_by_paragraph(section["content"])
        else:
            chunks = [section["content"].strip()]

        for i, chunk in enumerate(chunks):
            if chunk:
                all_chunks.append({
                    "text": chunk,
                    "metadata": {
                        "source": source,
                        "section": section["heading"] or "概述",
                        "chunk_index": i,
                        "topic": topic or "",
                        "doc_id": doc_id or "",
                        "title": title or source.replace(".md", "")
                    }
                })

    return all_chunks
```

- [ ] **Step 2: 修改 process_file 方法自动提取 topic**

修改 `document_processor.py` 的 `process_file` 方法：

```python
def process_file(self, file_path: str, topic: str = None) -> list[dict]:
    """处理文件，自动识别格式

    Args:
        file_path: 文件路径
        topic: 主题分类（可选）

    Returns:
        带元数据的 chunks 列表
    """
    content = self.read_file(file_path)
    source = os.path.basename(file_path)

    # 自动提取 doc_id（文件名前的数字）
    doc_id = ""
    if source[0:2].isdigit():
        doc_id = source[0:2]

    # 提取 title（去掉扩展名和前缀数字）
    title = source.replace(".md", "").replace(".txt", "")
    if len(title) > 3 and title[0:2].isdigit() and title[2] in ["-", "_", " "]:
        title = title[3:].strip()

    return self.process_document(content, source, topic, doc_id, title)
```

- [ ] **Step 3: 验证修改**

```bash
cd backend
python -c "
from document_processor import DocumentProcessor
dp = DocumentProcessor(512, 50)
chunks = dp.process_file('../data/python-docs/01-Agent基础概念学习笔记.md', 'agent-arch')
print(chunks[0]['metadata'])
"
```

预期输出包含 topic、doc_id、title 字段。

- [ ] **Step 4: 提交变更**

```bash
git add document_processor.py
git commit -m "feat: extend document metadata with topic, doc_id, title fields"
```

---

## Task 5: 扩展 RAG 引擎 - Sources 返回字段

**Files:**
- Modify: `rag_engine.py`
- Modify: `backend/api/chat.py`

- [ ] **Step 1: 修改 RAG 引擎返回完整 sources 数据**

修改 `rag_engine.py` 的 `query_stream` 方法：

```python
def query_stream(self, question: str) -> Generator[dict, None, None]:
    """流式查询，返回 {answer_chunk, sources}

    Args:
        question: 用户问题

    Yields:
        包含 answer_chunk 和 sources 的字典
    """
    results = self.retrieve(question)

    # 将 results 转换为 contexts 格式
    contexts = []
    for doc, meta, dist in zip(results["documents"], results["metadatas"], results["distances"]):
        similarity = 1 - dist
        contexts.append({
            "text": doc,
            "metadata": meta,
            "similarity": similarity
        })

    prompt = self.build_prompt(question, contexts)

    sources = []
    for ctx in contexts:
        text_preview = ctx["text"][:200] + "..." if len(ctx["text"]) > 200 else ctx["text"]
        sources.append({
            "source": ctx["metadata"]["source"],
            "section": ctx["metadata"]["section"],
            "similarity": round(ctx["similarity"], 2),
            "text_preview": text_preview,
            "topic": ctx["metadata"].get("topic", "")
        })

    full_answer = ""
    for chunk in self.llm_client.stream_generate(prompt):
        full_answer += chunk
        yield {
            "answer_chunk": chunk,
            "full_answer": full_answer,
            "sources": sources
        }

    self.update_history(question, full_answer)
```

- [ ] **Step 2: 修改 chat.py 返回扩展的 sources**

修改 `backend/api/chat.py` 的 `generate` 函数：

```python
async def generate():
    sources = []
    try:
        if request.mode == "rag":
            contexts = engine.retrieve(request.message)
            if contexts["documents"]:
                for meta, dist in zip(contexts["metadatas"], contexts["distances"]):
                    similarity = 1 - dist
                    text_preview = ""  # 需要从文档获取
                    sources.append({
                        "source": meta["source"],
                        "section": meta["section"],
                        "similarity": round(similarity, 2),
                        "text_preview": text_preview,
                        "topic": meta.get("topic", "")
                    })
                context_list = []
                for doc, meta in zip(contexts["documents"], contexts["metadatas"]):
                    context_list.append({"text": doc, "metadata": meta})
                prompt = engine.build_prompt(request.message, context_list)
            else:
                prompt = f"你是一个 Agent 技术专家。请简洁明了地回答以下问题：\n\n{request.message}"
        else:
            prompt = f"你是一个 Agent 技术专家。请简洁明了地回答以下问题：\n\n{request.message}"

        # ... 其余代码保持不变
```

- [ ] **Step 3: 提交变更**

```bash
git add rag_engine.py backend/api/chat.py
git commit -m "feat: extend SSE sources with similarity, text_preview, topic fields"
```

---

## Task 6: 创建知识库 API

**Files:**
- Create: `backend/api/knowledge.py`
- Modify: `backend/main.py`

- [ ] **Step 1: 创建 knowledge.py API**

创建 `backend/api/knowledge.py`:

```python
import os
from fastapi import APIRouter, Query
from typing import Optional

router = APIRouter()

# 延迟导入
engine = None
config = None

def get_engine_and_config():
    global engine, config
    if engine is None:
        from config import config as cfg
        from rag_engine import RAGEngine
        config = cfg
        engine = RAGEngine(config)
    return engine, config


@router.get("/knowledge/topics")
async def get_topics():
    """获取主题列表"""
    _, config = get_engine_and_config()
    topics = []
    for key, value in config.KNOWLEDGE_TOPICS.items():
        topics.append({
            "id": key,
            "name": value["name"],
            "file_count": len(value["files"])
        })
    return {"topics": topics}


@router.get("/knowledge/cards")
async def get_cards(
    topic: Optional[str] = Query(None, description="主题筛选"),
    search: Optional[str] = Query(None, description="搜索关键词")
):
    """获取知识卡片列表"""
    engine, config = get_engine_and_config()

    # 获取所有文档来源
    sources = engine.vector_store.get_all_sources()

    # 按主题筛选
    if topic and topic in config.KNOWLEDGE_TOPICS:
        topic_files = config.KNOWLEDGE_TOPICS[topic]["files"]
        sources = [s for s in sources if s in topic_files]

    # 搜索过滤
    if search:
        sources = [s for s in sources if search.lower() in s.lower()]

    # 构建卡片数据
    cards = []
    for source in sources:
        # 获取该文档的块数
        doc_count = engine.vector_store.count_by_source(source)

        # 查找主题
        doc_topic = ""
        for topic_key, topic_value in config.KNOWLEDGE_TOPICS.items():
            if source in topic_value["files"]:
                doc_topic = topic_key
                break

        # 提取标题
        title = source.replace(".md", "")
        if len(title) > 3 and title[0:2].isdigit() and title[2] in ["-", "_", " "]:
            title = title[3:].strip()

        cards.append({
            "id": source.replace(".md", "").replace(" ", "-"),
            "source": source,
            "title": title,
            "topic": doc_topic,
            "chunk_count": doc_count,
            "summary": f"包含 {doc_count} 个知识块"
        })

    return {"cards": cards}


@router.get("/knowledge/cards/{card_id}")
async def get_card_detail(card_id: str):
    """获取卡片详情（完整 Markdown）"""
    engine, config = get_engine_and_config()

    # 根据 card_id 查找 source
    sources = engine.vector_store.get_all_sources()
    source = None
    for s in sources:
        if s.replace(".md", "").replace(" ", "-") == card_id:
            source = s
            break

    if not source:
        return {"error": "卡片不存在"}

    # 读取原始 Markdown 文件
    data_dir = config.DATA_DIR
    file_path = os.path.join(data_dir, source)

    if not os.path.exists(file_path):
        return {"error": "文档文件不存在"}

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 提取标题
    title = source.replace(".md", "")
    if len(title) > 3 and title[0:2].isdigit() and title[2] in ["-", "_", " "]:
        title = title[3:].strip()

    # 查找主题
    doc_topic = ""
    for topic_key, topic_value in config.KNOWLEDGE_TOPICS.items():
        if source in topic_value["files"]:
            doc_topic = topic_key
            break

    return {
        "id": card_id,
        "source": source,
        "title": title,
        "topic": doc_topic,
        "content": content
    }
```

- [ ] **Step 2: 在 main.py 注册 knowledge 路由**

修改 `backend/main.py`：

```python
import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 切换工作目录到项目根目录
os.chdir(project_root)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from api.chat import router as chat_router
from api.documents import router as documents_router
from api.conversations import router as conversations_router
from api.knowledge import router as knowledge_router

app = FastAPI(title="AI Agent 知识问答助手 API")

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(chat_router, prefix="/api")
app.include_router(documents_router, prefix="/api")
app.include_router(conversations_router, prefix="/api")
app.include_router(knowledge_router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "AI Agent 知识问答助手 API"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

- [ ] **Step 3: 验证 API 可用**

```bash
cd backend
python -c "
import requests
response = requests.get('http://localhost:8000/api/knowledge/topics')
print(response.json())
"
```

- [ ] **Step 4: 提交变更**

```bash
git add backend/api/knowledge.py backend/main.py
git commit -m "feat: add Knowledge API with topics and cards endpoints"
```

---

## Task 7: 创建前端知识库 Store

**Files:**
- Create: `frontend/src/stores/knowledge.js`
- Modify: `frontend/src/api/index.js`

- [ ] **Step 1: 添加知识库 API 函数**

修改 `frontend/src/api/index.js`，在末尾添加：

```javascript
// 知识库 API
export async function getTopics() {
  const response = await api.get('/knowledge/topics')
  return response.data
}

export async function getCards(topic = null, search = null) {
  const params = {}
  if (topic) params.topic = topic
  if (search) params.search = search
  const response = await api.get('/knowledge/cards', { params })
  return response.data
}

export async function getCardDetail(cardId) {
  const response = await api.get(`/knowledge/cards/${cardId}`)
  return response.data
}
```

- [ ] **Step 2: 创建 knowledge store**

创建 `frontend/src/stores/knowledge.js`:

```javascript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getTopics, getCards, getCardDetail } from '../api'

export const useKnowledgeStore = defineStore('knowledge', () => {
  // 状态
  const topics = ref([])
  const cards = ref([])
  const activeTopic = ref(null)
  const selectedCard = ref(null)
  const searchQuery = ref('')
  const loading = ref(false)
  const cardDetail = ref(null)

  // 计算属性
  const filteredCards = computed(() => {
    if (!searchQuery.value) return cards.value
    return cards.value.filter(card =>
      card.title.toLowerCase().includes(searchQuery.value.toLowerCase())
    )
  })

  // 获取主题列表
  async function fetchTopics() {
    try {
      const data = await getTopics()
      topics.value = data.topics || []
    } catch (error) {
      console.error('获取主题失败:', error)
    }
  }

  // 获取卡片列表
  async function fetchCards(topic = null) {
    loading.value = true
    try {
      const data = await getCards(topic)
      cards.value = data.cards || []
    } catch (error) {
      console.error('获取卡片失败:', error)
    } finally {
      loading.value = false
    }
  }

  // 获取卡片详情
  async function fetchCardDetail(cardId) {
    loading.value = true
    try {
      const data = await getCardDetail(cardId)
      cardDetail.value = data
    } catch (error) {
      console.error('获取卡片详情失败:', error)
    } finally {
      loading.value = false
    }
  }

  // 设置活动主题
  function setActiveTopic(topic) {
    activeTopic.value = topic
    fetchCards(topic)
  }

  // 设置选中卡片
  function selectCard(card) {
    selectedCard.value = card
    if (card) {
      fetchCardDetail(card.id)
    } else {
      cardDetail.value = null
    }
  }

  // 搜索
  function setSearchQuery(query) {
    searchQuery.value = query
  }

  return {
    topics,
    cards,
    activeTopic,
    selectedCard,
    searchQuery,
    loading,
    cardDetail,
    filteredCards,
    fetchTopics,
    fetchCards,
    fetchCardDetail,
    setActiveTopic,
    selectCard,
    setSearchQuery
  }
})
```

- [ ] **Step 3: 提交变更**

```bash
git add frontend/src/api/index.js frontend/src/stores/knowledge.js
git commit -m "feat: add knowledge store and API functions for frontend"
```

---

## Task 8: 创建主题筛选组件

**Files:**
- Create: `frontend/src/components/TopicFilter.vue`

- [ ] **Step 1: 创建 TopicFilter.vue**

创建 `frontend/src/components/TopicFilter.vue`:

```vue
<template>
  <div class="topic-filter">
    <el-tag
      v-for="topic in topics"
      :key="topic.id"
      :type="activeTopic === topic.id ? '' : 'info'"
      @click="handleTopicClick(topic.id)"
      class="topic-tag"
    >
      {{ topic.name }}
      <span class="count">({{ topic.file_count }})</span>
    </el-tag>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useKnowledgeStore } from '../stores/knowledge'

const store = useKnowledgeStore()

const topics = computed(() => store.topics)
const activeTopic = computed(() => store.activeTopic)

function handleTopicClick(topicId) {
  if (store.activeTopic === topicId) {
    store.setActiveTopic(null)
  } else {
    store.setActiveTopic(topicId)
  }
}
</script>

<style scoped>
.topic-filter {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  padding: 16px 0;
}

.topic-tag {
  cursor: pointer;
  transition: all 0.2s;
}

.topic-tag:hover {
  transform: translateY(-2px);
}

.count {
  opacity: 0.7;
  font-size: 12px;
}
</style>
```

- [ ] **Step 2: 提交变更**

```bash
git add frontend/src/components/TopicFilter.vue
git commit -m "feat: add TopicFilter component for knowledge page"
```

---

## Task 9: 创建知识卡片组件

**Files:**
- Create: `frontend/src/components/KnowledgeCard.vue`

- [ ] **Step 1: 创建 KnowledgeCard.vue**

创建 `frontend/src/components/KnowledgeCard.vue`:

```vue
<template>
  <div class="knowledge-card" @click="$emit('click', card)">
    <div class="card-header">
      <h3 class="card-title">{{ card.title }}</h3>
      <el-tag v-if="topicName" size="small" type="primary">{{ topicName }}</el-tag>
    </div>
    <div class="card-body">
      <p class="card-summary">{{ card.summary }}</p>
      <div class="card-meta">
        <span class="chunk-count">{{ card.chunk_count }} 个知识块</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useKnowledgeStore } from '../stores/knowledge'

const props = defineProps({
  card: {
    type: Object,
    required: true
  }
})

defineEmits(['click'])

const store = useKnowledgeStore()

const topicName = computed(() => {
  const topic = store.topics.find(t => t.id === props.card.topic)
  return topic ? topic.name : ''
})
</script>

<style scoped>
.knowledge-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.knowledge-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: #333;
  margin: 0;
  flex: 1;
}

.card-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.card-summary {
  font-size: 14px;
  color: #666;
  margin: 0;
  line-height: 1.5;
}

.card-meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: #999;
}

.chunk-count {
  display: flex;
  align-items: center;
  gap: 4px;
}
</style>
```

- [ ] **Step 2: 提交变更**

```bash
git add frontend/src/components/KnowledgeCard.vue
git commit -m "feat: add KnowledgeCard component for knowledge grid"
```

---

## Task 10: 创建知识详情抽屉组件

**Files:**
- Create: `frontend/src/components/KnowledgeDetail.vue`

- [ ] **Step 1: 创建 KnowledgeDetail.vue**

创建 `frontend/src/components/KnowledgeDetail.vue`:

```vue
<template>
  <el-drawer
    :model-value="!!selectedCard"
    @update:model-value="handleClose"
    :title="selectedCard?.title || ''"
    size="60%"
    direction="rtl"
  >
    <div v-if="loading" class="loading-container">
      <el-icon class="is-loading"><Loading /></el-icon>
      <span>加载中...</span>
    </div>

    <div v-else-if="cardDetail" class="detail-content">
      <div class="detail-header">
        <el-tag v-if="topicName" type="primary">{{ topicName }}</el-tag>
        <span class="source">{{ cardDetail.source }}</span>
      </div>

      <div class="markdown-body" v-html="renderedContent"></div>

      <div class="detail-actions">
        <el-button type="primary" @click="handleAskQuestion">
          向它提问
        </el-button>
      </div>
    </div>
  </el-drawer>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useKnowledgeStore } from '../stores/knowledge'
import { Loading } from '@element-plus/icons-vue'
import { marked } from 'marked'
import hljs from 'highlight.js'

const router = useRouter()
const store = useKnowledgeStore()

const selectedCard = computed(() => store.selectedCard)
const cardDetail = computed(() => store.cardDetail)
const loading = computed(() => store.loading)

const topicName = computed(() => {
  if (!cardDetail.value) return ''
  const topic = store.topics.find(t => t.id === cardDetail.value.topic)
  return topic ? topic.name : ''
})

const renderedContent = computed(() => {
  if (!cardDetail.value?.content) return ''
  return marked(cardDetail.value.content, {
    highlight: function (code, lang) {
      if (lang && hljs.getLanguage(lang)) {
        return hljs.highlight(code, { language: lang }).value
      }
      return hljs.highlightAuto(code).value
    }
  })
})

function handleClose(value) {
  if (!value) {
    store.selectCard(null)
  }
}

function handleAskQuestion() {
  if (cardDetail.value) {
    const question = `请介绍一下${cardDetail.value.title}`
    router.push({
      path: '/chat',
      query: { q: question }
    })
  }
}
</script>

<style scoped>
.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 200px;
  gap: 12px;
}

.detail-header {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid #eee;
}

.source {
  font-size: 14px;
  color: #999;
}

.markdown-body {
  font-size: 15px;
  line-height: 1.8;
}

.markdown-body :deep(pre) {
  background: #f5f5f5;
  border-radius: 8px;
  padding: 16px;
  overflow-x: auto;
}

.markdown-body :deep(code) {
  font-family: 'Fira Code', monospace;
}

.detail-actions {
  margin-top: 32px;
  padding-top: 16px;
  border-top: 1px solid #eee;
}
</style>
```

- [ ] **Step 2: 提交变更**

```bash
git add frontend/src/components/KnowledgeDetail.vue
git commit -m "feat: add KnowledgeDetail drawer with Markdown rendering"
```

---

## Task 11: 创建知识浏览页面

**Files:**
- Create: `frontend/src/views/KnowledgePage.vue`

- [ ] **Step 1: 创建 KnowledgePage.vue**

创建 `frontend/src/views/KnowledgePage.vue`:

```vue
<template>
  <div class="knowledge-page">
    <div class="page-header">
      <el-button @click="$router.push('/chat')" link>
        <el-icon><ArrowLeft /></el-icon>
        返回问答
      </el-button>
      <h1>知识浏览</h1>
      <div class="search-box">
        <el-input
          v-model="searchQuery"
          placeholder="搜索知识..."
          clearable
          @input="handleSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
      </div>
    </div>

    <div class="page-content">
      <TopicFilter />

      <div v-if="loading" class="loading-container">
        <el-skeleton :rows="6" animated />
      </div>

      <div v-else-if="filteredCards.length === 0" class="empty-container">
        <el-empty description="暂无知识卡片" />
      </div>

      <div v-else class="cards-grid">
        <KnowledgeCard
          v-for="card in filteredCards"
          :key="card.id"
          :card="card"
          @click="handleCardClick"
        />
      </div>
    </div>

    <KnowledgeDetail />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useKnowledgeStore } from '../stores/knowledge'
import { ArrowLeft, Search } from '@element-plus/icons-vue'
import TopicFilter from '../components/TopicFilter.vue'
import KnowledgeCard from '../components/KnowledgeCard.vue'
import KnowledgeDetail from '../components/KnowledgeDetail.vue'

const store = useKnowledgeStore()

const searchQuery = ref('')

const loading = computed(() => store.loading)
const filteredCards = computed(() => store.filteredCards)

onMounted(() => {
  store.fetchTopics()
  store.fetchCards()
})

function handleSearch(value) {
  store.setSearchQuery(value)
}

function handleCardClick(card) {
  store.selectCard(card)
}
</script>

<style scoped>
.knowledge-page {
  min-height: 100vh;
  background: #f5f7fa;
}

.page-header {
  background: white;
  padding: 16px 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  display: flex;
  align-items: center;
  gap: 24px;
}

.page-header h1 {
  font-size: 20px;
  font-weight: 600;
  margin: 0;
  flex: 1;
}

.search-box {
  width: 300px;
}

.page-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
}

.loading-container {
  padding: 40px 0;
}

.empty-container {
  padding: 80px 0;
}

.cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
}
</style>
```

- [ ] **Step 2: 提交变更**

```bash
git add frontend/src/views/KnowledgePage.vue
git commit -m "feat: add KnowledgePage with search and grid layout"
```

---

## Task 12: 创建 RAG 可视化面板

**Files:**
- Create: `frontend/src/components/SourceCard.vue`
- Create: `frontend/src/components/RagVisualization.vue`
- Modify: `frontend/src/components/ChatView.vue`

- [ ] **Step 1: 创建 SourceCard.vue**

创建 `frontend/src/components/SourceCard.vue`:

```vue
<template>
  <div class="source-card">
    <div class="card-header">
      <span class="source-name">{{ source.source }}</span>
      <span class="section">{{ source.section }}</span>
    </div>
    <div class="card-body">
      <div class="similarity-bar">
        <div class="bar-label">相似度</div>
        <div class="bar-container">
          <div class="bar-fill" :style="{ width: similarityPercent + '%' }"></div>
        </div>
        <span class="bar-value">{{ similarityPercent }}%</span>
      </div>
      <div class="text-preview" v-if="source.text_preview">
        <p>{{ source.text_preview }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  source: {
    type: Object,
    required: true
  }
})

const similarityPercent = computed(() => {
  return Math.round((props.source.similarity || 0) * 100)
})
</script>

<style scoped>
.source-card {
  background: white;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 12px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.1);
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.source-name {
  font-size: 13px;
  font-weight: 600;
  color: #333;
}

.section {
  font-size: 12px;
  color: #999;
}

.card-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.similarity-bar {
  display: flex;
  align-items: center;
  gap: 8px;
}

.bar-label {
  font-size: 12px;
  color: #666;
  min-width: 40px;
}

.bar-container {
  flex: 1;
  height: 6px;
  background: #e0e0e0;
  border-radius: 3px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
  border-radius: 3px;
  transition: width 0.3s;
}

.bar-value {
  font-size: 12px;
  font-weight: 600;
  color: #667eea;
  min-width: 35px;
}

.text-preview {
  margin-top: 4px;
}

.text-preview p {
  font-size: 12px;
  color: #666;
  line-height: 1.6;
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
```

- [ ] **Step 2: 创建 RagVisualization.vue**

创建 `frontend/src/components/RagVisualization.vue`:

```vue
<template>
  <div class="rag-visualization">
    <h3 class="panel-title">RAG 检索结果</h3>

    <div v-if="loading" class="loading-container">
      <el-skeleton :rows="3" animated />
    </div>

    <div v-else-if="sources.length === 0" class="empty-container">
      <p>暂无检索结果</p>
    </div>

    <div v-else class="sources-list">
      <SourceCard
        v-for="(source, index) in sources"
        :key="index"
        :source="source"
      />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useChatStore } from '../stores/chat'
import SourceCard from './SourceCard.vue'

const store = useChatStore()

const sources = computed(() => {
  const lastAssistantMsg = [...store.messages]
    .reverse()
    .find(msg => msg.role === 'assistant')
  return lastAssistantMsg?.sources || []
})

const loading = computed(() => store.loading)
</script>

<style scoped>
.rag-visualization {
  padding: 16px;
}

.panel-title {
  font-size: 16px;
  font-weight: 600;
  color: #333;
  margin: 0 0 16px 0;
}

.loading-container {
  padding: 16px 0;
}

.empty-container {
  padding: 32px 0;
  text-align: center;
}

.empty-container p {
  font-size: 14px;
  color: #999;
  margin: 0;
}

.sources-list {
  display: flex;
  flex-direction: column;
}
</style>
```

- [ ] **Step 3: 提交变更**

```bash
git add frontend/src/components/SourceCard.vue frontend/src/components/RagVisualization.vue
git commit -m "feat: add RAG visualization with source cards"
```

---

## Task 13: 更新 ChatView 集成可视化

**Files:**
- Modify: `frontend/src/components/ChatView.vue`

- [ ] **Step 1: 修改 ChatView 为三栏布局**

修改 `frontend/src/components/ChatView.vue`，集成 RAG 可视化：

```vue
<template>
  <div class="chat-container">
    <!-- 中间消息区 -->
    <div class="message-area">
      <div class="messages-list" ref="messagesContainer">
        <ChatMessage
          v-for="(msg, index) in messages"
          :key="index"
          :message="msg"
        />
        <div v-if="loading" class="loading-indicator">
          <el-icon class="is-loading"><Loading /></el-icon>
          <span>思考中...</span>
        </div>
      </div>

      <div class="input-area">
        <el-input
          v-model="inputMessage"
          :rows="1"
          type="textarea"
          placeholder="输入问题..."
          @keydown.enter.exact.prevent="handleSend"
          :disabled="loading"
        />
        <el-button
          type="primary"
          @click="handleSend"
          :loading="loading"
          :disabled="!inputMessage.trim()"
        >
          发送
        </el-button>
      </div>
    </div>

    <!-- 右侧 RAG 面板 -->
    <div class="rag-panel">
      <RagVisualization />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useChatStore } from '../stores/chat'
import { Loading } from '@element-plus/icons-vue'
import ChatMessage from './ChatMessage.vue'
import RagVisualization from './RagVisualization.vue'

const route = useRoute()
const store = useChatStore()

const inputMessage = ref('')
const messagesContainer = ref(null)

const messages = computed(() => store.messages)
const loading = computed(() => store.loading)

onMounted(() => {
  // 处理从知识页跳转过来的提问
  if (route.query.q) {
    inputMessage.value = route.query.q
  }
})

watch(messages, () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}, { deep: true })

async function handleSend() {
  if (!inputMessage.value.trim() || loading.value) return

  const message = inputMessage.value
  inputMessage.value = ''
  await store.sendMessage(message)
}
</script>

<style scoped>
.chat-container {
  display: flex;
  height: 100%;
}

.message-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.messages-list {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.loading-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  color: #999;
  font-size: 14px;
}

.input-area {
  display: flex;
  gap: 12px;
  padding: 16px 20px;
  background: white;
  border-top: 1px solid #eee;
}

.rag-panel {
  width: 280px;
  background: #f5f7fa;
  border-left: 1px solid #eee;
  overflow-y: auto;
}
</style>
```

- [ ] **Step 2: 提交变更**

```bash
git add frontend/src/components/ChatView.vue
git commit -m "feat: integrate RAG visualization into ChatView"
```

---

## Task 14: 更新 ChatMessage 支持 Markdown

**Files:**
- Modify: `frontend/src/components/ChatMessage.vue`

- [ ] **Step 1: 添加 Markdown 渲染支持**

修改 `frontend/src/components/ChatMessage.vue`：

```vue
<template>
  <div class="chat-message" :class="[message.role]">
    <div class="message-content">
      <div class="message-avatar">
        <span v-if="message.role === 'user'">U</span>
        <span v-else>A</span>
      </div>
      <div class="message-body">
        <div class="message-text" v-html="renderedContent"></div>
        <div class="message-meta">
          <span class="timestamp">{{ formatTime(message.timestamp) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { marked } from 'marked'
import hljs from 'highlight.js'

const props = defineProps({
  message: {
    type: Object,
    required: true
  }
})

const renderedContent = computed(() => {
  if (!props.message.content) return ''
  return marked(props.message.content, {
    highlight: function (code, lang) {
      if (lang && hljs.getLanguage(lang)) {
        return hljs.highlight(code, { language: lang }).value
      }
      return hljs.highlightAuto(code).value
    }
  })
})

function formatTime(timestamp) {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}
</script>

<style scoped>
.chat-message {
  margin-bottom: 20px;
}

.message-content {
  display: flex;
  gap: 12px;
}

.message-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  flex-shrink: 0;
}

.user .message-avatar {
  background: #667eea;
  color: white;
}

.assistant .message-avatar {
  background: #764ba2;
  color: white;
}

.message-body {
  flex: 1;
}

.message-text {
  font-size: 15px;
  line-height: 1.8;
  color: #333;
}

.message-text :deep(pre) {
  background: #f5f5f5;
  border-radius: 8px;
  padding: 16px;
  overflow-x: auto;
  margin: 12px 0;
}

.message-text :deep(code) {
  font-family: 'Fira Code', monospace;
}

.message-text :deep(p) {
  margin: 8px 0;
}

.message-meta {
  margin-top: 8px;
}

.timestamp {
  font-size: 12px;
  color: #999;
}
</style>
```

- [ ] **Step 2: 提交变更**

```bash
git add frontend/src/components/ChatMessage.vue
git commit -m "feat: add Markdown rendering to ChatMessage with syntax highlighting"
```

---

## Task 15: 更新 ChatPage 为三栏布局

**Files:**
- Create: `frontend/src/views/ChatPage.vue`
- Modify: `frontend/src/router/index.js`

- [ ] **Step 1: 创建 ChatPage.vue 容器**

创建 `frontend/src/views/ChatPage.vue`：

```vue
<template>
  <div class="chat-page">
    <el-container class="page-layout">
      <!-- 左侧栏 -->
      <el-aside width="260px" class="sidebar">
        <ChatSidebar />
      </el-aside>

      <!-- 中间对话区 + 右侧 RAG 面板 -->
      <el-main class="main-content">
        <ChatView />
      </el-main>
    </el-container>

    <!-- 深色模式切换 -->
    <button class="dark-toggle" @click="toggleDark">
      <span v-if="isDark">☀️</span>
      <span v-else>🌙</span>
    </button>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import ChatSidebar from '../components/ChatSidebar.vue'
import ChatView from '../components/ChatView.vue'

const isDark = ref(false)

function toggleDark() {
  isDark.value = !isDark.value
  document.documentElement.classList.toggle('dark', isDark.value)
}
</script>

<style scoped>
.chat-page {
  height: 100vh;
  position: relative;
}

.page-layout {
  height: 100%;
}

.sidebar {
  background: white;
  border-right: 1px solid #eee;
  overflow-y: auto;
}

.main-content {
  display: flex;
  flex-direction: column;
  padding: 0;
  overflow: hidden;
}

.dark-toggle {
  position: fixed;
  top: 12px;
  right: 12px;
  z-index: 100;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: white;
  border: 1px solid #ddd;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
```

- [ ] **Step 2: 更新路由配置**

修改 `frontend/src/router/index.js`：

```javascript
import { createRouter, createWebHistory } from 'vue-router'
import LandingPage from '../views/LandingPage.vue'
import ChatPage from '../views/ChatPage.vue'
import KnowledgePage from '../views/KnowledgePage.vue'

const routes = [
  {
    path: '/',
    name: 'Landing',
    component: LandingPage
  },
  {
    path: '/chat',
    name: 'Chat',
    component: ChatPage
  },
  {
    path: '/knowledge',
    name: 'Knowledge',
    component: KnowledgePage
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
```

- [ ] **Step 3: 提交变更**

```bash
git add frontend/src/views/ChatPage.vue frontend/src/router/index.js
git commit -m "feat: add ChatPage with three-column layout"
```

---

## Task 16: 端到端测试

- [ ] **Step 1: 启动后端服务**

```bash
cd backend
python main.py
```

确认服务在 http://localhost:8000 启动。

- [ ] **Step 2: 启动前端开发服务器**

```bash
cd frontend
npm run dev
```

确认服务在 http://localhost:5173 启动。

- [ ] **Step 3: 测试 Landing 页面**

访问 http://localhost:5173/，验证：
- 页面标题和副标题显示正确
- 两个按钮可以跳转到对应页面
- RAG 流程图和技术栈标签显示正确
- 统计数据正确加载

- [ ] **Step 4: 测试问答页面**

访问 http://localhost:5173/chat，验证：
- 左侧对话历史正常加载
- 可以发送消息并收到流式响应
- RAG 可视化面板正确显示检索结果
- SourceCard 显示相似度和文本预览
- Markdown 渲染和代码高亮正常工作

- [ ] **Step 5: 测试知识浏览页面**

访问 http://localhost:5173/knowledge，验证：
- 主题筛选标签正确显示
- 可以点击标签筛选卡片
- 卡片网格布局正常
- 搜索功能正常工作
- 点击卡片可以打开详情抽屉
- 详情抽屉显示 Markdown 内容
- "向它提问"按钮可以跳转到问答页

- [ ] **Step 6: 最终提交**

```bash
git add -A
git commit -m "feat: complete AI Agent knowledge Q&A assistant with multi-page navigation"
```

---

## 实施检查清单

- [ ] 所有依赖已安装（vue-router, marked, highlight.js）
- [ ] 路由配置正确，三个页面可访问
- [ ] Landing 页面显示正常
- [ ] Chat 页面三栏布局正常
- [ ] Knowledge 页面主题筛选和卡片显示正常
- [ ] RAG 可视化面板正确显示
- [ ] Markdown 渲染和代码高亮正常
- [ ] SSE sources 包含 similarity、text_preview、topic 字段
- [ ] 所有 API 端点正常工作
- [ ] 错误处理符合规格要求
