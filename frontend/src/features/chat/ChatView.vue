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
      
      <!-- 系统按钮组 -->
      <div class="system-btns">
      <button
        class="harmony-icon-btn--sm docs-btn"
        @click="$emit('open-docs')"
        title="文档管理"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
          <path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </button>
        <button class="harmony-icon-btn--sm" @click="$emit('toggle-dashboard')" title="评测与性能">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
            <path d="M18 20V10M12 20V4M6 20v-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </button>
        <button class="harmony-icon-btn--sm" @click="$emit('toggle-dark')" :title="isDark ? '切换浅色模式' : '切换深色模式'">
          <svg v-if="isDark" width="18" height="18" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="5" stroke="currentColor" stroke-width="2"/>
            <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
          </svg>
          <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="none">
            <path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </button>
        <button class="harmony-icon-btn--sm logout-btn" @click="$emit('logout')" title="退出登录">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
            <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </button>
      </div>
    </div>

    <!-- 消息列表 -->
    <div class="messages-container cus-scroll" ref="messagesRef">
      <!-- 空状态 -->
      <div v-if="store.messages.length === 0" class="empty-chat harmony-animate-in-scale">
        
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
        class="harmony-animate-in"
      />
    </div>

    <!-- 输入框区域 -->
    <div class="input-area">
      <div class="input-wrapper harmony-input-box">
        <input
          ref="inputRef"
          v-model="inputMessage"
          class="chat-input"
          placeholder="输入你的问题..."
          @keydown.enter.exact.prevent="handleSend"
          :disabled="store.loading"
        />
        <button
          class="send-btn harmony-action-btn primary"
          @click="handleSend"
          :disabled="store.loading || !inputMessage.trim()"
          :class="{ pulsing: inputMessage.trim() && !store.loading }"
        >
          <span v-if="store.loading" class="harmony-loading-spinner"></span>
          <span v-else class="send-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
              <path d="M5 12h14M12 5l7 7-7 7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </span>
        </button>
      </div>
      <div class="input-footer">
        <!-- 模式切换 -->
        <div class="harmony-tab-bar">
          <button
            class="harmony-tab-item"
            :class="{ active: store.mode === 'rag' }"
            @click="store.mode = 'rag'"
          >
            RAG 模式
          </button>
          <button
            class="harmony-tab-item"
            :class="{ active: store.mode === 'direct' }"
            @click="store.mode = 'direct'"
          >
            直接对话
          </button>
        </div>
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
const props = defineProps({
  isDark: { type: Boolean, default: false }
})
defineEmits(['open-docs', 'toggle-dashboard', 'toggle-dark', 'logout'])
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
  background: var(--harmony-background-secondary);
}

/* ── 顶部栏 ── */
.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: var(--harmony-titlebar-height);
  padding: 0 var(--harmony-padding-level12);
  background: var(--harmony-titlebar-bg);
  backdrop-filter: var(--harmony-titlebar-blur);
  -webkit-backdrop-filter: var(--harmony-titlebar-blur);
  border-bottom: var(--harmony-titlebar-border);
  position: sticky;
  top: 0;
  z-index: 10;
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--harmony-padding-level5);
}

.docs-btn {
  margin-right: var(--harmony-padding-level4);
}

.system-btns {
  display: flex;
  align-items: center;
  gap: var(--harmony-padding-level3);
  margin-right: var(--harmony-padding-level4);
}

.system-btns .harmony-icon-btn--sm {
  background: var(--harmony-comp-background-primary);
  border: 1px solid var(--harmony-comp-divider);
}

.system-btns .harmony-icon-btn--sm:hover {
  background: var(--harmony-interactive-hover);
}

.system-btns .logout-btn {
  color: var(--harmony-font-secondary);
}

.system-btns .logout-btn:hover {
  color: var(--harmony-warning);
}

.chat-header h3 {
  font-size: var(--harmony-font-size-subtitle-l);
  font-weight: var(--harmony-font-weight-title-s);
  color: var(--harmony-font-primary);
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
  background: var(--harmony-brand);
  animation: harmony-pulse-dot 1.4s ease-in-out infinite;
}

.typing-dot:nth-child(2) { animation-delay: 0.2s; }
.typing-dot:nth-child(3) { animation-delay: 0.4s; }

/* ── 消息区域 ── */
.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: var(--harmony-padding-level12);
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
  font-size: var(--harmony-font-size-title-s);
  font-weight: var(--harmony-font-weight-title-s);
  color: var(--harmony-font-primary);
  margin-bottom: var(--harmony-padding-level4);
}

.empty-sub {
  font-size: var(--harmony-font-size-body-m);
  color: var(--harmony-font-secondary);
  margin-bottom: 24px;
}

.empty-suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--harmony-padding-level3);
  justify-content: center;
}

.suggestion-chip {
  padding: var(--harmony-padding-level4) var(--harmony-padding-level8);
  height: 36px;
  line-height: 20px;
  border: 1px solid var(--harmony-comp-divider);
  border-radius: var(--harmony-corner-radius-level10);
  background: var(--harmony-comp-background-primary);
  color: var(--harmony-font-secondary);
  font-size: var(--harmony-font-size-subtitle-s);
  font-weight: var(--harmony-font-weight-subtitle-s);
  cursor: pointer;
  transition: all 0.2s var(--harmony-ease-out);
}

.suggestion-chip:hover {
  background: var(--harmony-interactive-hover);
  color: var(--harmony-font-primary);
}

/* ── 输入区域 ── */
.input-area {
  padding: var(--harmony-padding-level8) var(--harmony-padding-level12) var(--harmony-padding-level10);
  background: var(--harmony-background-secondary);
  border-top: none;
  flex-shrink: 0;
}

.input-wrapper {
  display: flex;
  align-items: center;
  gap: var(--harmony-padding-level5);
  padding: var(--harmony-padding-level4) var(--harmony-padding-level6);
  height: 40px;
  background: var(--harmony-input-glass-bg);
  backdrop-filter: blur(8px);
  border: none;
  border-radius: var(--harmony-corner-radius-level12);
  box-shadow: var(--harmony-input-glass-shadow);
}

.input-wrapper:focus-within {
  box-shadow: var(--harmony-input-glass-shadow), 0 0 0 2px var(--harmony-brand);
}

.chat-input {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  font-size: var(--harmony-font-size-body-l);
  color: var(--harmony-font-primary);
  font-family: inherit;
  line-height: 1.5;
}

.chat-input::placeholder {
  color: var(--harmony-font-secondary);
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
  opacity: 0.4;
  transition: opacity 0.2s var(--harmony-ease-out);
}

.send-btn:not(:disabled) {
  opacity: 1;
}

.send-btn:not(:disabled):hover {
  background: var(--harmony-brand-hover);
}

.send-icon {
  display: flex;
  align-items: center;
  justify-content: center;
}

.input-footer {
  display: flex;
  align-items: center;
  gap: var(--harmony-padding-level4);
  margin-top: var(--harmony-padding-level5);
}

.footer-btn {
  padding: var(--harmony-padding-level3) var(--harmony-padding-level7);
  font-size: var(--harmony-font-size-body-s);
  color: var(--harmony-font-tertiary);
}

.mode-hint {
  margin-left: auto;
  font-size: var(--harmony-font-size-body-s);
  color: var(--harmony-font-tertiary);
}
</style>
