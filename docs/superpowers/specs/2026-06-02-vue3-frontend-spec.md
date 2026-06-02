# Vue 3 前端重构设计规格

## 架构

前后端分离架构：
- **后端**: FastAPI (Port 8000) - 提供 REST API
- **前端**: Vue 3 + Element Plus (Port 5173) - 独立 SPA

## 后端 API 设计

### 流式对话
```
POST /api/chat
Request: { "message": "问题", "mode": "rag"|"direct" }
Response: SSE stream
  data: { "chunk": "token", "full_answer": "完整回答", "sources": [...] }
```

### 文档管理
```
POST /api/upload          - 上传文档
GET  /api/documents       - 获取文档列表
POST /api/documents/load  - 批量加载本地文档
GET  /api/stats           - 获取统计信息
DELETE /api/history       - 清空对话历史
```

## 前端组件设计

### 页面布局 (三栏)
- **左侧栏** (260px): 历史对话列表 + 新建对话
- **中间区** (flex): 消息列表 + 输入框
- **右侧栏** (280px): 文档上传/管理/统计

### 组件结构
```
App.vue
├── ChatSidebar.vue       # 左侧历史对话
├── ChatView.vue          # 主对话区
│   ├── ChatMessage.vue   # 单条消息
│   └── ChatInput.vue     # 输入框
└── DocumentPanel.vue     # 右侧文档管理
```

### 状态管理 (Pinia)
```javascript
// stores/chat.js
state: {
  conversations: [],
  currentMessages: [],
  mode: 'rag',
  documents: [],
  stats: {}
}
```

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端框架 | Vue 3 + Vite |
| UI 组件 | Element Plus |
| 状态管理 | Pinia |
| HTTP 客户端 | Axios |
| 后端框架 | FastAPI |
| 流式传输 | SSE (Server-Sent Events) |

## 目录结构

```
项目1/
├── backend/
│   ├── main.py           # FastAPI 入口
│   ├── api/
│   │   ├── chat.py       # 对话 API
│   │   └── documents.py  # 文档 API
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── views/
│   │   ├── components/
│   │   ├── stores/
│   │   ├── api/
│   │   └── App.vue
│   ├── package.json
│   └── vite.config.js
└── ... (现有文件)
```
