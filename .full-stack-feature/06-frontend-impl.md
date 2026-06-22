# Frontend Implementation Summary

## 新增文件

### API 层（按领域拆分）
- `src/api/auth.js` — login, register, getMe
- `src/api/chat.js` — chatStream（SSE 逻辑原样保留）
- `src/api/documents.js` — upload, batch, list, delete, sync, stats
- `src/api/conversations.js` — list, get, delete, clearAll

### Store 层（按领域拆分）
- `src/stores/useAuthStore.js` — token, username, isAuthenticated, login/logout/checkAuth
- `src/stores/useChatStore.js` — messages, mode, loading, sendMessage, clearChatHistory
- `src/stores/useDocumentStore.js` — documents, stats, upload, delete, sync
- `src/stores/useConversationStore.js` — conversations, fetch, load, delete
- `src/stores/useToastStore.js` — 统一 Toast 通知

### Feature 目录
- `src/features/auth/LoginView.vue`
- `src/features/chat/ChatView.vue`, `ChatMessage.vue`, `ChatSidebar.vue`
- `src/features/documents/DocumentPanel.vue`, `BatchUploadProgress.vue`

## 修改的文件
- `src/api/index.js` — 精简为仅 Axios 实例 + 拦截器
- `src/App.vue` — 使用 useAuthStore + useToastStore，更新组件导入路径

## 删除的文件
- `src/stores/chat.js` — 原 God Store
- `src/components/` 下 6 个已迁移的组件
