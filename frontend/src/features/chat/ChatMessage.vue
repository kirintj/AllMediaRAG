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
        <div v-if="message.role === 'assistant' && message.loading && !message.content" class="thinking-indicator">
          <span class="thinking-dot"></span>
          <span class="thinking-dot"></span>
          <span class="thinking-dot"></span>
        </div>
        <div v-else class="message-text" v-html="formattedContent"></div>
      </div>

      <!-- 参考来源 -->
      <div v-if="message.sources && message.sources.length > 0" class="message-sources">
        <div class="sources-header">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5" stroke="var(--harmony-brand)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          <span>参考来源</span>
        </div>
        <div class="sources-list">
          <span
            v-for="(source, idx) in message.sources"
            :key="idx"
            class="harmony-filter-chip source-chip"
          >
            {{ (source.section && source.section !== '概述') ? source.section : cleanSourceName(source.source) }}
          </span>
        </div>
      </div>

      <!-- 引用核查 -->
      <div v-if="message.verification" class="verification-block">
        <div class="verification-header" @click="toggleVerification">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          <span>引用核查</span>
          <span class="verification-badge" :class="verificationRiskClass">
            {{ verificationRiskText }}
          </span>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" class="chevron" :class="{ expanded: showVerification }">
            <path d="M6 9l6 6 6-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </div>
        <div v-if="showVerification" class="verification-details">
          <div class="verification-item">
            <span class="label">置信度:</span>
            <span class="value span-end">{{ (message.verification.confidence * 100).toFixed(0) }}%</span>
          </div>

          <!-- 检索质量指标 -->
          <div v-if="message.verification.retrieval_metrics" class="metrics-section">
            <div class="metrics-title">检索质量</div>
            <div class="verification-item">
              <span class="label">文档数量:</span>
              <span class="value span-end">{{ message.verification.retrieval_metrics.doc_count }}</span>
            </div>
            <div v-if="message.verification.retrieval_metrics.max_similarity != null" class="verification-item">
              <span class="label">最高相似度:</span>
              <div class="progress-bar">
                <div class="progress-fill" :style="{ width: (message.verification.retrieval_metrics.max_similarity * 100) + '%' }"></div>
              </div>
              <span class="value">{{ (message.verification.retrieval_metrics.max_similarity * 100).toFixed(0) }}%</span>
            </div>
            <div v-if="message.verification.retrieval_metrics.avg_similarity != null" class="verification-item">
              <span class="label">平均相似度:</span>
              <div class="progress-bar">
                <div class="progress-fill" :style="{ width: (message.verification.retrieval_metrics.avg_similarity * 100) + '%' }"></div>
              </div>
              <span class="value">{{ (message.verification.retrieval_metrics.avg_similarity * 100).toFixed(0) }}%</span>
            </div>
            <div v-if="message.verification.retrieval_metrics.stability != null" class="verification-item">
              <span class="label">稳定性:</span>
              <div class="progress-bar">
                <div class="progress-fill" :style="{ width: (message.verification.retrieval_metrics.stability * 100) + '%' }"></div>
              </div>
              <span class="value">{{ (message.verification.retrieval_metrics.stability * 100).toFixed(0) }}%</span>
            </div>
          </div>

          <!-- 忠实度指标 -->
          <div v-if="message.verification.faithfulness_metrics" class="metrics-section">
            <div class="metrics-title">忠实度</div>
            <div v-if="message.verification.faithfulness_metrics.support_ratio != null" class="verification-item">
              <span class="label">支撑比例:</span>
              <div class="progress-bar">
                <div class="progress-fill" :style="{ width: (message.verification.faithfulness_metrics.support_ratio * 100) + '%' }"></div>
              </div>
              <span class="value">{{ (message.verification.faithfulness_metrics.support_ratio * 100).toFixed(0) }}%</span>
            </div>
            <div v-if="message.verification.faithfulness_metrics.claim_count != null" class="verification-item">
              <span class="label">有支撑断言:</span>
              <span class="value span-end">{{ message.verification.faithfulness_metrics.supported_count }}/{{ message.verification.faithfulness_metrics.claim_count }}</span>
            </div>
          </div>

          <!-- 上下文覆盖率 -->
          <div v-if="message.verification.context_coverage != null" class="metrics-section">
            <div class="metrics-title">上下文覆盖</div>
            <div class="verification-item">
              <span class="label">覆盖率:</span>
              <div class="progress-bar">
                <div class="progress-fill" :style="{ width: (message.verification.context_coverage * 100) + '%' }"></div>
              </div>
              <span class="value">{{ (message.verification.context_coverage * 100).toFixed(0) }}%</span>
            </div>
          </div>

          <div v-if="message.verification.unsupported_claims && message.verification.unsupported_claims.length > 0" class="verification-item">
            <span class="label">无支撑断言:</span>
            <span class="value warning span-end">{{ message.verification.unsupported_claims.length }} 条</span>
          </div>
          <div v-if="message.verification.suggested_disclaimer" class="verification-disclaimer">
            {{ message.verification.suggested_disclaimer }}
          </div>
        </div>
      </div>

      <!-- 耗时 -->
      <div v-if="message.role === 'assistant' && message.elapsed != null" class="message-timing">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/>
          <path d="M12 6v6l4 2" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <span>{{ formattedElapsed }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { marked } from 'marked'

const props = defineProps({
  message: {
    type: Object,
    required: true
  }
})

const showVerification = ref(false)

function toggleVerification() {
  showVerification.value = !showVerification.value
}

function cleanSourceName(name) {
  if (!name) return ''
  return name.replace(/\.[^.]+$/, '')
}

const verificationRiskClass = computed(() => {
  if (!props.message.verification) return ''
  const risk = props.message.verification.hallucination_risk
  if (risk === 'high') return 'risk-high'
  if (risk === 'medium') return 'risk-medium'
  return 'risk-low'
})

const verificationRiskText = computed(() => {
  if (!props.message.verification) return ''
  const risk = props.message.verification.hallucination_risk
  if (risk === 'high') return '高风险'
  if (risk === 'medium') return '中风险'
  return '低风险'
})

const formattedContent = computed(() => {
  if (!props.message.content) return ''

  // 使用 marked 渲染 Markdown
  const html = marked.parse(props.message.content, {
    breaks: true, // 将换行符转换为 <br>
    gfm: true,    // 启用 GitHub Flavored Markdown
  })

  return html
})

const formattedElapsed = computed(() => {
  const ms = props.message.elapsed
  if (ms == null) return ''
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(1)}s`
})
</script>

<style scoped>
.message {
  display: flex;
  gap: var(--harmony-padding-level6);
  margin-bottom: var(--harmony-padding-level10);
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
  border-radius: var(--harmony-corner-radius-level8);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.2s var(--harmony-ease-out);
}

.avatar:hover {
  transform: scale(1.05);
}

.avatar.user {
  background: var(--harmony-comp-background-emphasize);
  color: var(--harmony-font-on-primary);
}

.avatar.assistant {
  background: var(--harmony-comp-background-secondary);
  border: 1px solid var(--harmony-comp-divider);
  color: var(--harmony-brand);
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
  padding: var(--harmony-padding-level7) var(--harmony-padding-level9);
  border-radius: var(--harmony-corner-radius-level16);
  font-size: var(--harmony-font-size-body-m);
  line-height: 1.7;
}

.message-bubble.assistant {
  background: var(--harmony-comp-background-primary);
  border: 1px solid var(--harmony-comp-divider);
  box-shadow: var(--harmony-shadow-sm);
  border-top-left-radius: var(--harmony-corner-radius-level4);
}

.message-bubble.user {
  background: var(--harmony-comp-background-emphasize);
  color: var(--harmony-font-on-primary);
  border-top-right-radius: var(--harmony-corner-radius-level4);
}

/* ── 文本内容 ── */
.message-text {
  word-break: break-word;
}

.message-text :deep(pre) {
  background: var(--harmony-background-tertiary);
  color: var(--harmony-font-primary);
  padding: var(--harmony-padding-level7) var(--harmony-padding-level8);
  border-radius: var(--harmony-corner-radius-level8);
  margin: 10px 0 6px;
  overflow-x: auto;
  font-family: 'SFMono-Regular', 'JetBrains Mono', Consolas, monospace;
  font-size: var(--harmony-font-size-body-s);
  line-height: 1.6;
  border: 1px solid var(--harmony-comp-divider);
}

.message-bubble.user .message-text :deep(pre) {
  background: var(--harmony-comp-background-secondary);
  border-color: var(--harmony-comp-divider);
}

.message-text :deep(code) {
  background: var(--harmony-interactive-pressed);
  padding: var(--harmony-padding-level1) var(--harmony-padding-level3);
  border-radius: var(--harmony-corner-radius-level2);
  font-family: 'SFMono-Regular', 'JetBrains Mono', Consolas, monospace;
  font-size: var(--harmony-font-size-body-s);
}

.message-bubble.user .message-text :deep(code) {
  background: var(--harmony-comp-background-secondary);
}

.message-text :deep(strong) {
  font-weight: var(--harmony-font-weight-subtitle-m);
}

/* ── Markdown 标题 ── */
.message-text :deep(h1),
.message-text :deep(h2),
.message-text :deep(h3),
.message-text :deep(h4) {
  margin: 12px 0 6px;
  font-weight: var(--harmony-font-weight-title-s);
  line-height: 1.4;
}

.message-text :deep(h1) { font-size: var(--harmony-font-size-subtitle-l); }
.message-text :deep(h2) { font-size: var(--harmony-font-size-subtitle-m); }
.message-text :deep(h3) { font-size: var(--harmony-font-size-subtitle-s); }
.message-text :deep(h4) { font-size: var(--harmony-font-size-body-l); }

/* ── Markdown 段落 ── */
.message-text :deep(p) {
  margin: 6px 0;
}

.message-text :deep(p:first-child) {
  margin-top: 0;
}

.message-text :deep(p:last-child) {
  margin-bottom: 0;
}

/* ── Markdown 列表 ── */
.message-text :deep(ul),
.message-text :deep(ol) {
  margin: 6px 0;
  padding-left: 20px;
}

.message-text :deep(li) {
  margin: 3px 0;
}

/* ── Markdown 引用块 ── */
.message-text :deep(blockquote) {
  margin: 8px 0;
  padding: var(--harmony-padding-level2) var(--harmony-padding-level6);
  border-left: 3px solid var(--harmony-brand);
  color: var(--harmony-font-secondary);
  background: var(--harmony-comp-background-secondary);
  border-radius: 0 var(--harmony-corner-radius-level4) var(--harmony-corner-radius-level4) 0;
}

/* ── Markdown 表格 ── */
.message-text :deep(table) {
  border-collapse: collapse;
  margin: 8px 0;
  font-size: var(--harmony-font-size-body-s);
  width: 100%;
}

.message-text :deep(th),
.message-text :deep(td) {
  border: 1px solid var(--harmony-comp-divider);
  padding: var(--harmony-padding-level3) var(--harmony-padding-level5);
  text-align: left;
}

.message-text :deep(th) {
  background: var(--harmony-comp-background-secondary);
  font-weight: var(--harmony-font-weight-subtitle-s);
}

/* ── Markdown 分割线 ── */
.message-text :deep(hr) {
  border: none;
  border-top: 1px solid var(--harmony-comp-divider);
  margin: 12px 0;
}

/* ── Markdown 链接 ── */
.message-text :deep(a) {
  color: var(--harmony-brand);
  text-decoration: none;
}

.message-text :deep(a:hover) {
  text-decoration: underline;
}

/* ── Markdown 行内代码需要在 pre 内取消背景 ── */
.message-text :deep(pre code) {
  background: none;
  padding: 0;
  border-radius: 0;
  font-size: inherit;
}

/* ── 参考来源 ── */
.message-sources {
  margin-top: var(--harmony-padding-level5);
  padding: var(--harmony-padding-level5) var(--harmony-padding-level6);
  background: var(--harmony-comp-background-secondary);
  border-radius: var(--harmony-corner-radius-level8);
  border: 1px solid var(--harmony-comp-divider);
}

.sources-header {
  display: flex;
  align-items: center;
  gap: var(--harmony-padding-level3);
  font-size: var(--harmony-font-size-caption-l);
  font-weight: var(--harmony-font-weight-caption-l);
  color: var(--harmony-font-secondary);
  margin-bottom: var(--harmony-padding-level4);
}

.sources-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--harmony-padding-level3);
}

.source-chip {
  font-size: var(--harmony-font-size-caption-l);
  cursor: default;
}

.source-chip:hover {
  transform: none;
}

/* ── 引用核查 ── */
.verification-block {
  margin-top: var(--harmony-padding-level5);
  padding: var(--harmony-padding-level5) var(--harmony-padding-level6);
  background: var(--harmony-comp-background-secondary);
  border-radius: var(--harmony-corner-radius-level8);
  border: 1px solid var(--harmony-comp-divider);
}

.verification-header {
  display: flex;
  align-items: center;
  gap: var(--harmony-padding-level3);
  font-size: var(--harmony-font-size-caption-l);
  font-weight: var(--harmony-font-weight-caption-l);
  color: var(--harmony-font-secondary);
  cursor: pointer;
  user-select: none;
}

.verification-header:hover {
  color: var(--harmony-font-primary);
}

.verification-badge {
  margin-left: auto;
  padding: var(--harmony-padding-level1) var(--harmony-padding-level4);
  border-radius: var(--harmony-corner-radius-level5);
  font-size: var(--harmony-font-size-caption-m);
  font-weight: var(--harmony-font-weight-caption-l);
}

.verification-badge.risk-low {
  background: var(--harmony-confirm-light);
  color: var(--harmony-confirm);
}

.verification-badge.risk-medium {
  background: var(--harmony-alert-light);
  color: var(--harmony-alert);
}

.verification-badge.risk-high {
  background: var(--harmony-warning-light);
  color: var(--harmony-warning);
}

.chevron {
  transition: transform 0.2s;
}

.chevron.expanded {
  transform: rotate(180deg);
}

.verification-details {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid var(--harmony-comp-divider);
}

.verification-item {
  display: grid;
  grid-template-columns: 80px 1fr 40px;
  align-items: center;
  gap: 6px;
  font-size: var(--harmony-font-size-body-s);
  margin-bottom: 6px;
}

.verification-item .label {
  color: var(--harmony-font-tertiary);
  white-space: nowrap;
  text-align: right;
}

.verification-item .value {
  color: var(--harmony-font-primary);
  font-weight: var(--harmony-font-weight-subtitle-s);
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.verification-item .value.warning {
  color: var(--harmony-alert);
}

.verification-item .value.span-end {
  grid-column: 2 / 4;
}

.verification-disclaimer {
  margin-top: var(--harmony-padding-level4);
  padding: var(--harmony-padding-level4);
  background: var(--harmony-alert-subtle);
  border-radius: var(--harmony-corner-radius-level4);
  font-size: var(--harmony-font-size-caption-l);
  color: var(--harmony-font-secondary);
  line-height: 1.5;
}

/* ── 评估指标 ── */
.metrics-section {
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px solid var(--harmony-comp-divider);
}

.metrics-title {
  font-size: var(--harmony-font-size-caption-l);
  font-weight: var(--harmony-font-weight-caption-l);
  color: var(--harmony-font-secondary);
  margin-bottom: 6px;
}

.progress-bar {
  width: 100%;
  height: 6px;
  background: var(--harmony-comp-background-secondary);
  border-radius: var(--harmony-corner-radius-level3);
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--harmony-brand);
  border-radius: var(--harmony-corner-radius-level3);
  transition: width 0.3s var(--harmony-ease-out);
}

/* ── 耗时 ── */
.message-timing {
  display: flex;
  align-items: center;
  gap: var(--harmony-padding-level2);
  margin-top: 6px;
  font-size: var(--harmony-font-size-caption-l);
  color: var(--harmony-font-tertiary);
  opacity: 0.7;
}

.message.user .message-timing {
  justify-content: flex-end;
}

/* ── 思考动画 ── */
.thinking-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 0;
}

.thinking-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--harmony-brand);
  opacity: 0.6;
  animation: harmony-pulse-dot 1.4s ease-in-out infinite;
}

.thinking-dot:nth-child(2) { animation-delay: 0.2s; }
.thinking-dot:nth-child(3) { animation-delay: 0.4s; }
</style>
