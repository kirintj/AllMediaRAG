<template>
  <div class="chat-sidebar">
    <!-- 品牌标题 -->
    <div class="sidebar-header">
      <div class="brand-area">
        <div class="brand-icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
            <rect width="24" height="24" rx="8" fill="url(#brandGrad)"/>
            <path d="M7 8h10M7 12h6M7 16h8" stroke="white" stroke-width="2" stroke-linecap="round"/>
            <defs>
              <linearGradient id="brandGrad" x1="0" y1="0" x2="24" y2="24">
                <stop stop-color="#0A59F7"/>
                <stop offset="1" stop-color="#337BF7"/>
              </linearGradient>
            </defs>
          </svg>
        </div>
        <div class="brand-text">
          <h2>知识库助手</h2>
          <span class="brand-subtitle">RAG 智能问答</span>
        </div>
      </div>

      <!-- 新对话按钮 -->
      <button class="hm-action-btn primary new-chat-btn" @click="newChat">
        <span class="btn-icon">+</span>
        新对话
      </button>
    </div>

    <!-- 历史对话 -->
    <div class="conversation-list" ref="listRef">
      <div class="list-header">
        <div class="list-title">历史对话</div>
        <button
          v-if="conversationStore.conversations.length > 0"
          class="clear-all-btn"
          @click="handleClearAll"
          title="清空全部"
        >
          清空全部
        </button>
      </div>
      <div v-if="conversationStore.conversations.length === 0" class="list-empty">
        <div class="empty-icon">
          <svg width="40" height="40" viewBox="0 0 40 40" fill="none">
            <rect width="40" height="40" rx="12" fill="var(--hm-bg-container-secondary)"/>
            <path d="M14 16h12M14 20h8M14 24h10" stroke="var(--hm-font-tertiary)" stroke-width="2" stroke-linecap="round"/>
          </svg>
        </div>
        <p>暂无历史对话</p>
        <p class="empty-hint">发送消息开始新对话</p>
      </div>
      <div v-else class="conv-items">
        <div
          v-for="conv in conversationStore.conversations"
          :key="conv.id"
          class="conv-item"
          :class="{ active: chatStore.activeConversationId === conv.id }"
          @click="conversationStore.loadConversation(conv.id)"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" flex-shrink="0">
            <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          <span class="conv-title" :title="conv.title">{{ conv.title }}</span>
          <span class="conv-count">{{ conv.message_count }}条</span>
          <button
            class="conv-delete"
            @click.stop="handleDelete(conv)"
            title="删除"
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
              <path d="M18 6L6 18M6 6l12 12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessageBox } from 'element-plus'
import { useChatStore } from '../../stores/useChatStore.js'
import { useConversationStore } from '../../stores/useConversationStore.js'

const chatStore = useChatStore()
const conversationStore = useConversationStore()
const listRef = ref(null)

function newChat() {
  chatStore.clearChatHistory()
}

async function handleDelete(conv) {
  try {
    await ElMessageBox.confirm(
      `删除后不可恢复，确定删除「${conv.title}」？`,
      '删除对话',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning',
        customClass: 'delete-confirm-box',
        confirmButtonClass: 'el-button--danger',
      }
    )
    await conversationStore.removeConversation(conv.id)
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') {
      console.error('删除对话失败:', e)
    }
  }
}

async function handleClearAll() {
  const count = conversationStore.conversations.length
  try {
    await ElMessageBox.confirm(
      `将删除全部 ${count} 条对话记录，删除后不可恢复。`,
      '清空全部对话',
      {
        confirmButtonText: '全部清空',
        cancelButtonText: '取消',
        type: 'warning',
        customClass: 'delete-confirm-box',
        confirmButtonClass: 'el-button--danger',
      }
    )
    await conversationStore.removeAllConversations()
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') {
      console.error('清空对话失败:', e)
    }
  }
}

onMounted(() => {
  conversationStore.fetchConversations()
})
</script>

<style scoped>
.chat-sidebar {
  padding: 20px 16px;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.sidebar-header {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.brand-area {
  display: flex;
  align-items: center;
  gap: 10px;
}

.brand-icon {
  flex-shrink: 0;
}

.brand-text h2 {
  font-size: 16px;
  font-weight: 700;
  color: var(--hm-font-primary);
  line-height: 1.2;
}

.brand-subtitle {
  font-size: 12px;
  color: var(--hm-font-tertiary);
  font-weight: 500;
}

.new-chat-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 8px 16px;
  font-size: 14px;
  font-weight: 600;
}

.new-chat-btn::after {
  display: none;
}

.new-chat-btn:hover {
  transform: none;
  box-shadow: none;
  opacity: 1;
  background: var(--hm-brand-gradient);
  color: var(--hm-font-on-brand);
}

.btn-icon {
  font-size: 18px;
  font-weight: 300;
}

/* ── 对话列表 ── */
.conversation-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  padding-right: 2px;
  scroll-behavior: smooth;
}

/* 侧边栏专用滚动条：更细、更精致 */
.conversation-list::-webkit-scrollbar {
  width: 4px;
}

.conversation-list::-webkit-scrollbar-track {
  background: transparent;
}

.conversation-list::-webkit-scrollbar-thumb {
  background: transparent;
  border-radius: 2px;
  transition: background 0.3s;
}

.conversation-list:hover::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.12);
}

.conversation-list:hover::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.22);
}

html.dark .conversation-list:hover::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.12);
}

html.dark .conversation-list:hover::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.22);
}

.list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.list-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--hm-font-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.clear-all-btn {
  font-size: 12px;
  color: var(--hm-font-tertiary);
  background: none;
  border: none;
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 4px;
  transition: all 0.2s;
}

.clear-all-btn:hover {
  color: var(--hm-error);
  background: var(--hm-danger-hover-bg);
}

.list-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px 16px;
  text-align: center;
}

.empty-icon {
  margin-bottom: 12px;
}

.list-empty p {
  font-size: 14px;
  color: var(--hm-font-secondary);
  margin-bottom: 4px;
}

.empty-hint {
  font-size: 12px !important;
  color: var(--hm-font-tertiary) !important;
}

.conv-items {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.conv-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: var(--hm-radius-md);
  cursor: pointer;
  color: var(--hm-font-secondary);
  transition: all 0.2s var(--hm-spring);
}

.conv-item:hover {
  background: var(--hm-hover-bg);
  color: var(--hm-font-primary);
}

.conv-item.active {
  background: var(--hm-brand-bg-light);
  color: var(--hm-brand);
}

.conv-title {
  flex: 1;
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
}

.conv-count {
  font-size: 11px;
  color: var(--hm-font-tertiary);
  flex-shrink: 0;
}

.conv-delete {
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  border-radius: 4px;
  color: var(--hm-font-tertiary);
  cursor: pointer;
  opacity: 0;
  transition: all 0.2s;
}

.conv-item:hover .conv-delete {
  opacity: 1;
}

.conv-delete:hover {
  background: rgba(232, 64, 38, 0.1);
  color: var(--hm-error);
}
</style>
