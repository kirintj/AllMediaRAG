<template>
  <div class="chat-sidebar">
    <!-- 品牌标题 -->
    <div class="sidebar-header">
      <div class="brand-area">
        <div class="brand-icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
            <rect width="24" height="24" rx="8" fill="var(--harmony-brand)"/>
            <path d="M7 8h10M7 12h6M7 16h8" stroke="var(--harmony-font-on-primary)" stroke-width="2" stroke-linecap="round"/>
          </svg>
        </div>
        <div class="brand-text">
          <h2>知识库助手</h2>
          <span class="brand-subtitle">RAG 智能问答</span>
        </div>
      </div>

      <!-- 新对话按钮 -->
      <button class="harmony-action-btn primary new-chat-btn" @click="newChat">
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
            <rect width="40" height="40" rx="12" fill="var(--harmony-comp-background-secondary)"/>
            <path d="M14 16h12M14 20h8M14 24h10" stroke="var(--harmony-font-tertiary)" stroke-width="2" stroke-linecap="round"/>
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
  padding: var(--harmony-padding-level10) var(--harmony-padding-level8);
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: var(--harmony-padding-level8);
}

.sidebar-header {
  display: flex;
  flex-direction: column;
  gap: var(--harmony-padding-level8);
}

.brand-area {
  display: flex;
  align-items: center;
  gap: var(--harmony-padding-level6);
}

.brand-icon {
  flex-shrink: 0;
}

.brand-text h2 {
  font-size: var(--harmony-font-size-subtitle-l);
  font-weight: var(--harmony-font-weight-title-s);
  color: var(--harmony-font-primary);
  line-height: 1.2;
}

.brand-subtitle {
  font-size: var(--harmony-font-size-body-s);
  color: var(--harmony-font-tertiary);
  font-weight: var(--harmony-font-weight-body-s);
}

.new-chat-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--harmony-padding-level3);
  padding: var(--harmony-padding-level5) var(--harmony-padding-level10);
  font-size: var(--harmony-font-size-subtitle-m);
  font-weight: var(--harmony-font-weight-subtitle-m);
  height: var(--harmony-control-height-40);
  border-radius: var(--harmony-corner-radius-level10);
  background: var(--harmony-comp-background-emphasize);
}

.new-chat-btn:hover {
  background: var(--harmony-brand-hover);
  color: var(--harmony-font-on-primary);
}

.btn-icon {
  font-size: var(--harmony-font-size-subtitle-l);
  font-weight: 300;
}

/* ── 对话列表 ── */
.conversation-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  padding-right: var(--harmony-padding-level1);
  scroll-behavior: smooth;
}

.list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--harmony-padding-level6);
}

.list-title {
  font-size: var(--harmony-font-size-caption-l);
  font-weight: var(--harmony-font-weight-caption-l);
  color: var(--harmony-font-tertiary);
}

.clear-all-btn {
  font-size: var(--harmony-font-size-body-s);
  color: var(--harmony-font-tertiary);
  background: none;
  border: none;
  cursor: pointer;
  padding: var(--harmony-padding-level1) var(--harmony-padding-level3);
  border-radius: var(--harmony-corner-radius-level2);
  transition: all 0.2s var(--harmony-ease-out);
}

.clear-all-btn:hover {
  color: var(--harmony-warning);
  background: var(--harmony-danger-hover-bg);
}

.list-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--harmony-padding-level16) var(--harmony-padding-level8);
  text-align: center;
}

.empty-icon {
  margin-bottom: 12px;
}

.list-empty p {
  font-size: var(--harmony-font-size-body-m);
  color: var(--harmony-font-secondary);
  margin-bottom: var(--harmony-padding-level1);
}

.empty-hint {
  font-size: var(--harmony-font-size-body-s) !important;
  color: var(--harmony-font-tertiary) !important;
}

.conv-items {
  display: flex;
  flex-direction: column;
  gap: var(--harmony-padding-level5);
}

.conv-item {
  display: flex;
  align-items: center;
  gap: var(--harmony-padding-level5);
  padding: var(--harmony-padding-level4) var(--harmony-padding-level6);
  border-radius: var(--harmony-corner-radius-level8);
  cursor: pointer;
  color: var(--harmony-font-secondary);
  transition: background 0.2s var(--harmony-ease-out);
}

.conv-item:hover {
  background: var(--harmony-interactive-hover);
  color: var(--harmony-font-primary);
}

.conv-item:active {
  background: var(--harmony-interactive-pressed);
}

.conv-item.active {
  background: var(--harmony-interactive-select);
  color: var(--harmony-font-emphasize);
}

.conv-title {
  flex: 1;
  font-size: var(--harmony-font-size-body-l);
  font-weight: var(--harmony-font-weight-subtitle-m);
  line-height: 22px;
  color: var(--harmony-font-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
}

.conv-count {
  font-size: var(--harmony-font-size-body-m);
  line-height: 19px;
  color: var(--harmony-font-secondary);
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
  border-radius: var(--harmony-corner-radius-level2);
  color: var(--harmony-font-tertiary);
  cursor: pointer;
  opacity: 0;
  transition: all 0.2s var(--harmony-ease-out);
}

.conv-item:hover .conv-delete {
  opacity: 1;
}

.conv-delete:hover {
  background: var(--harmony-danger-hover-bg);
  color: var(--harmony-warning);
}

.conv-delete:active {
  background: var(--harmony-danger-hover-bg);
  transition-duration: 0.08s;
}

.conv-item:focus-visible {
  outline: 2px solid var(--harmony-interactive-focus);
  outline-offset: -2px;
  border-radius: var(--harmony-corner-radius-level8);
}
</style>
