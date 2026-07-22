<template>
  <div class="chat-sidebar">
    <!-- 品牌标题 -->
    <div class="sidebar-header">
      <div class="brand-area">
        <div class="brand-icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
            <rect width="24" height="24" rx="8" fill="hsl(var(--nb-brand))"/>
            <path d="M7 8h10M7 12h6M7 16h8" stroke="white" stroke-width="2" stroke-linecap="round"/>
          </svg>
        </div>
        <div class="brand-text">
          <h2>知识库助手</h2>
          <span class="brand-subtitle">RAG 智能问答</span>
        </div>
      </div>

      <!-- 新对话按钮 -->
      <button class="nb-btn primary new-chat-btn" @click="newChat">
        <span class="btn-icon">+</span>
        新对话
      </button>
    </div>

    <!-- 历史对话 -->
    <div class="conversation-list cus-scroll" ref="listRef">
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
            <rect width="40" height="40" rx="12" fill="hsl(var(--muted))"/>
            <path d="M14 16h12M14 20h8M14 24h10" stroke="hsl(var(--muted-foreground))" stroke-width="2" stroke-linecap="round"/>
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
  padding: var(--nb-space-5) var(--nb-space-4);
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: var(--nb-space-4);
}

.sidebar-header {
  display: flex;
  flex-direction: column;
  gap: var(--nb-space-4);
}

.brand-area {
  display: flex;
  align-items: center;
  gap: var(--nb-space-3);
}

.brand-icon {
  flex-shrink: 0;
}

.brand-text h2 {
  font-size: var(--nb-font-lg);
  font-weight: 600;
  color: hsl(var(--foreground));
  line-height: 1.2;
}

.brand-subtitle {
  font-size: var(--nb-font-xs);
  color: hsl(var(--muted-foreground));
}

.new-chat-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--nb-space-2);
  padding: var(--nb-space-2) var(--nb-space-4);
  font-size: var(--nb-font-base);
  font-weight: 500;
  height: 36px;
}

.btn-icon {
  font-size: var(--nb-font-lg);
  font-weight: 300;
}

/* ── 对话列表 ── */
.conversation-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  scroll-behavior: smooth;
}

.list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--nb-space-3);
}

.list-title {
  font-size: var(--nb-font-xs);
  font-weight: 500;
  color: hsl(var(--muted-foreground));
}

.clear-all-btn {
  font-size: var(--nb-font-xs);
  color: hsl(var(--muted-foreground));
  background: none;
  border: none;
  cursor: pointer;
  padding: var(--nb-space-1) var(--nb-space-2);
  border-radius: var(--radius);
  transition: all 0.15s ease;
}

.clear-all-btn:hover {
  color: hsl(var(--destructive));
  background: hsl(var(--nb-danger-bg));
}

.list-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--nb-space-10) var(--nb-space-4);
  text-align: center;
}

.empty-icon {
  margin-bottom: 12px;
}

.list-empty p {
  font-size: var(--nb-font-base);
  color: hsl(var(--muted-foreground));
  margin-bottom: var(--nb-space-1);
}

.empty-hint {
  font-size: var(--nb-font-xs) !important;
  color: hsl(var(--muted-foreground) / 0.7) !important;
}

.conv-items {
  display: flex;
  flex-direction: column;
  gap: var(--nb-space-1);
}

.conv-item {
  display: flex;
  align-items: center;
  gap: var(--nb-space-2);
  padding: var(--nb-space-2) var(--nb-space-3);
  border-radius: var(--radius);
  cursor: pointer;
  color: hsl(var(--muted-foreground));
  transition: background 0.15s ease;
}

.conv-item:hover {
  background: hsl(var(--accent));
  color: hsl(var(--foreground));
}

.conv-item.active {
  background: hsl(var(--accent));
  color: hsl(var(--accent-foreground));
}

.conv-title {
  flex: 1;
  font-size: var(--nb-font-sm);
  font-weight: 500;
  line-height: 22px;
  color: hsl(var(--foreground));
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
}

.conv-count {
  font-size: var(--nb-font-xs);
  color: hsl(var(--muted-foreground));
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
  border-radius: var(--radius);
  color: hsl(var(--muted-foreground));
  cursor: pointer;
  opacity: 0;
  transition: all 0.15s ease;
}

.conv-item:hover .conv-delete {
  opacity: 1;
}

.conv-delete:hover {
  background: hsl(var(--nb-danger-bg));
  color: hsl(var(--destructive));
}

.conv-item:focus-visible {
  outline: 2px solid hsl(var(--ring));
  outline-offset: -2px;
  border-radius: var(--radius);
}
</style>
