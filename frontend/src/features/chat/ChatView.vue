<template>
  <div class="chat-view">
    <!-- 顶部标题栏 -->
    <div class="chat-header">
      <div class="header-left">
        <h3>对话</h3>
        <span class="chat-status" v-if="store.loading">
          <span class="typing-dot"></span>
          <span class="typing-dot"></span>
          <span class="typing-dot"></span>
        </span>
      </div>
      <!-- HM Tab Bar 模式切换 -->
      <div class="hm-tab-bar">
        <button
          class="hm-tab-item"
          :class="{ active: store.mode === 'rag' }"
          @click="store.mode = 'rag'"
        >
          RAG 模式
        </button>
        <button
          class="hm-tab-item"
          :class="{ active: store.mode === 'direct' }"
          @click="store.mode = 'direct'"
        >
          直接对话
        </button>
      </div>
    </div>

    <!-- 消息列表 -->
    <div class="messages-container cus-scroll" ref="messagesRef">
      <!-- 空状态 -->
      <div v-if="store.messages.length === 0" class="empty-chat hm-animate-in-scale">
        <div class="empty-icon-wrap">
          <svg width="64" height="64" viewBox="0 0 64 64" fill="none">
            <rect x="4" y="4" width="56" height="56" rx="20" fill="var(--hm-brand-light)" stroke="var(--hm-brand)" stroke-width="2"/>
            <path d="M22 26h20M22 32h14M22 38h18" stroke="var(--hm-brand)" stroke-width="2.5" stroke-linecap="round"/>
            <circle cx="46" cy="42" r="8" fill="var(--hm-brand)" opacity="0.2"/>
            <path d="M43 42h6M46 39v6" stroke="var(--hm-brand)" stroke-width="2" stroke-linecap="round"/>
          </svg>
        </div>
        <h3>开始你的智能问答之旅</h3>
        <p class="empty-sub">基于 RAG 检索增强，精准回答知识库问题</p>
        <div class="empty-suggestions">
          <button class="suggestion-chip" @click="quickAsk('什么是 RAG？')">什么是 RAG？</button>
          <button class="suggestion-chip" @click="quickAsk('如何使用向量数据库？')">如何使用向量数据库？</button>
          <button class="suggestion-chip" @click="quickAsk('如何优化检索效果？')">如何优化检索效果？</button>
        </div>
      </div>

      <!-- 消息列表 -->
      <ChatMessage
        v-for="(msg, index) in store.messages"
        :key="index"
        :message="msg"
        :style="{ animationDelay: `${Math.min(index * 0.06, 0.3)}s` }"
        class="hm-animate-in"
      />
    </div>

    <!-- 输入框区域 -->
    <div class="input-area">
      <div class="input-wrapper hm-input-box">
        <input
          ref="inputRef"
          v-model="inputMessage"
          class="chat-input"
          placeholder="输入你的 Python 问题..."
          @keydown.enter.exact.prevent="handleSend"
          :disabled="store.loading"
        />
        <button
          class="send-btn hm-action-btn primary"
          @click="handleSend"
          :disabled="store.loading || !inputMessage.trim()"
          :class="{ pulsing: inputMessage.trim() && !store.loading }"
        >
          <span v-if="store.loading" class="hm-loading-spinner"></span>
          <span v-else class="send-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
              <path d="M5 12h14M12 5l7 7-7 7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </span>
        </button>
      </div>
      <div class="input-footer">
        <button class="hm-action-btn footer-btn" @click="store.clearChatHistory()">清空对话</button>
        <button class="hm-action-btn footer-btn" @click="store.clearChatHistory()">清空历史</button>
        <span class="mode-hint">
          {{ store.mode === 'rag' ? 'RAG 检索增强模式' : '直接对话模式' }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, watch } from 'vue'
import { useChatStore } from '../../stores/useChatStore.js'
import ChatMessage from './ChatMessage.vue'

const store = useChatStore()
const inputMessage = ref('')
const messagesRef = ref(null)
const inputRef = ref(null)

async function handleSend() {
  if (!inputMessage.value.trim() || store.loading) return

  const message = inputMessage.value
  inputMessage.value = ''

  await store.sendMessage(message)

  await nextTick()
  if (messagesRef.value) {
    messagesRef.value.scrollTop = messagesRef.value.scrollHeight
  }
}

function quickAsk(question) {
  inputMessage.value = question
  handleSend()
}

// 监听消息数量变化
watch(() => store.messages.length, () => {
  nextTick(() => {
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  })
})

// 监听流式输出内容变化
watch(
  () => {
    const msgs = store.messages
    if (msgs.length === 0) return ''
    return msgs[msgs.length - 1].content
  },
  () => {
    nextTick(() => {
      if (messagesRef.value) {
        messagesRef.value.scrollTop = messagesRef.value.scrollHeight
      }
    })
  }
)
</script>

<style scoped>
.chat-view {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--hm-bg-primary);
}

/* ── 顶部栏 ── */
.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 24px;
  border-bottom: 1px solid var(--hm-divider);
  background: var(--hm-bg-primary);
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.chat-header h3 {
  font-size: 16px;
  font-weight: 600;
  color: var(--hm-font-primary);
}

.chat-status {
  display: flex;
  align-items: center;
  gap: 3px;
}

.typing-dot {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--hm-brand);
  animation: hm-pulse-dot 1.4s ease-in-out infinite;
}

.typing-dot:nth-child(2) { animation-delay: 0.2s; }
.typing-dot:nth-child(3) { animation-delay: 0.4s; }

/* ── 消息区域 ── */
.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  scroll-behavior: smooth;
}

/* ── 空状态 ── */
.empty-chat {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;
  padding: 0 40px;
}

.empty-icon-wrap {
  margin-bottom: 20px;
}

.empty-chat h3 {
  font-size: 20px;
  font-weight: 600;
  color: var(--hm-font-primary);
  margin-bottom: 8px;
}

.empty-sub {
  font-size: 14px;
  color: var(--hm-font-secondary);
  margin-bottom: 24px;
}

.empty-suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
}

.suggestion-chip {
  padding: 8px 16px;
  border: 1px solid var(--hm-border);
  border-radius: var(--hm-radius-full);
  background: var(--hm-bg-glass);
  color: var(--hm-font-secondary);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.3s var(--hm-spring);
}

.suggestion-chip:hover {
  border-color: var(--hm-brand);
  color: var(--hm-brand);
  transform: translateY(-2px);
  box-shadow: var(--hm-glow-brand);
}

/* ── 输入区域 ── */
.input-area {
  padding: 16px 24px 20px;
  background: var(--hm-bg-primary);
  border-top: 1px solid var(--hm-divider);
  flex-shrink: 0;
}

.input-wrapper {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 8px 8px 16px;
}

.chat-input {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  font-size: 14px;
  color: var(--hm-font-primary);
  font-family: inherit;
  line-height: 1.5;
}

.chat-input::placeholder {
  color: var(--hm-font-tertiary);
}

.send-btn {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50% !important;
  opacity: 0.5;
  transition: all 0.3s var(--hm-spring);
}

.send-btn:not(:disabled) {
  opacity: 1;
}

.send-btn.pulsing {
  animation: hm-glow-pulse var(--hm-breathe-duration) ease-in-out infinite;
}

.send-icon {
  display: flex;
  align-items: center;
  justify-content: center;
}

.input-footer {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
}

.footer-btn {
  padding: 6px 14px;
  font-size: 12px;
  color: var(--hm-font-tertiary);
}

.mode-hint {
  margin-left: auto;
  font-size: 12px;
  color: var(--hm-font-tertiary);
}
</style>
