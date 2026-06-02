<template>
  <div class="message" :class="message.role">
    <!-- 头像 -->
    <div class="message-avatar">
      <div class="avatar" :class="message.role">
        <template v-if="message.role === 'user'">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
            <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2M12 11a4 4 0 100-8 4 4 0 000 8z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </template>
        <template v-else>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </template>
      </div>
    </div>

    <!-- 消息内容 -->
    <div class="message-body">
      <div class="message-bubble" :class="message.role">
        <div class="message-text" v-html="formattedContent"></div>
      </div>

      <!-- 参考来源 -->
      <div v-if="message.sources && message.sources.length > 0" class="message-sources">
        <div class="sources-header">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5" stroke="var(--hm-brand)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          <span>参考来源</span>
        </div>
        <div class="sources-list">
          <span
            v-for="(source, idx) in message.sources"
            :key="idx"
            class="hm-filter-chip source-chip"
          >
            {{ source.section || source.source }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  message: {
    type: Object,
    required: true
  }
})

const formattedContent = computed(() => {
  if (!props.message.content) return ''

  let text = props.message.content

  // 代码块
  text = text.replace(/```(\w+)?\n([\s\S]*?)```/g, (_, lang, code) => {
    return `<pre><code>${code.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</code></pre>`
  })

  // 行内代码
  text = text.replace(/`([^`]+)`/g, '<code>$1</code>')

  // 粗体
  text = text.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')

  // 换行
  text = text.replace(/\n/g, '<br>')

  return text
})
</script>

<style scoped>
.message {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  max-width: 100%;
}

.message.user {
  flex-direction: row-reverse;
}

/* ── 头像 ── */
.message-avatar {
  flex-shrink: 0;
}

.avatar {
  width: 36px;
  height: 36px;
  border-radius: var(--hm-radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.3s var(--hm-spring);
}

.avatar:hover {
  transform: scale(1.1);
}

.avatar.user {
  background: var(--hm-brand-gradient);
  color: white;
  box-shadow: var(--hm-shadow-brand);
}

.avatar.assistant {
  background: var(--hm-bg-container-secondary);
  border: 1px solid var(--hm-border);
  color: var(--hm-brand);
}

/* ── 消息体 ── */
.message-body {
  max-width: 75%;
  min-width: 60px;
}

.message.user .message-body {
  text-align: right;
}

/* ── 气泡 ── */
.message-bubble {
  padding: 14px 18px;
  border-radius: var(--hm-radius-lg);
  font-size: 14px;
  line-height: 1.7;
  transition: box-shadow 0.3s var(--hm-spring);
}

.message-bubble.assistant {
  background: var(--hm-bg-glass);
  border: 1px solid var(--hm-border-glass);
  box-shadow: var(--hm-shadow-layered);
  border-top-left-radius: var(--hm-radius-sm);
}

.message-bubble.assistant:hover {
  box-shadow: var(--hm-shadow-layered-hover);
}

.message-bubble.user {
  background: var(--hm-brand-gradient);
  color: var(--hm-font-on-brand);
  border-top-right-radius: var(--hm-radius-sm);
  box-shadow: var(--hm-shadow-brand);
}

/* ── 文本内容 ── */
.message-text {
  word-break: break-word;
}

.message-text :deep(pre) {
  background: #1a1b26;
  color: #c0caf5;
  padding: 14px 16px;
  border-radius: var(--hm-radius-md);
  margin: 10px 0 6px;
  overflow-x: auto;
  font-family: 'SFMono-Regular', 'JetBrains Mono', Consolas, monospace;
  font-size: 13px;
  line-height: 1.6;
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.message-bubble.user .message-text :deep(pre) {
  background: rgba(0, 0, 0, 0.2);
  border-color: rgba(255, 255, 255, 0.1);
}

.message-text :deep(code) {
  background: var(--hm-pressed-bg);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'SFMono-Regular', 'JetBrains Mono', Consolas, monospace;
  font-size: 13px;
}

.message-bubble.user .message-text :deep(code) {
  background: rgba(255, 255, 255, 0.15);
}

.message-text :deep(strong) {
  font-weight: 600;
}

/* ── 参考来源 ── */
.message-sources {
  margin-top: 10px;
  padding: 10px 12px;
  background: var(--hm-bg-container-secondary);
  border-radius: var(--hm-radius-md);
  border: 1px solid var(--hm-border);
}

.sources-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: var(--hm-font-secondary);
  margin-bottom: 8px;
}

.sources-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.source-chip {
  font-size: 11px;
  cursor: default;
}

.source-chip:hover {
  transform: none;
}
</style>
