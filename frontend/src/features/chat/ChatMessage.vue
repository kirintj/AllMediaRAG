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
            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5" stroke="hsl(var(--nb-brand))" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          <span>参考来源</span>
        </div>
        <div class="sources-list">
          <span
            v-for="(source, idx) in message.sources"
            :key="idx"
            class="nb-chip source-chip"
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
  return marked.parse(props.message.content, {
    breaks: true,
    gfm: true,
  })
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
  gap: var(--nb-space-3);
  margin-bottom: var(--nb-space-5);
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
  border-radius: var(--radius);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.15s ease;
}

.avatar:hover {
  transform: scale(1.05);
}

.avatar.user {
  background: hsl(var(--primary));
  color: hsl(var(--primary-foreground));
}

.avatar.assistant {
  background: hsl(var(--muted));
  border: 1px solid hsl(var(--border));
  color: hsl(var(--nb-brand));
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
  padding: var(--nb-space-3) var(--nb-space-4);
  border-radius: var(--radius);
  font-size: var(--nb-font-base);
  line-height: 1.7;
}

.message-bubble.assistant {
  background: hsl(var(--card));
  border: 1px solid hsl(var(--border));
  box-shadow: var(--nb-shadow-sm);
  border-top-left-radius: 2px;
}

.message-bubble.user {
  background: hsl(var(--primary));
  color: hsl(var(--primary-foreground));
  border-top-right-radius: 2px;
}

/* ── 文本内容 ── */
.message-text {
  word-break: break-word;
}

.message-text :deep(pre) {
  background: hsl(var(--muted));
  color: hsl(var(--foreground));
  padding: var(--nb-space-3) var(--nb-space-4);
  border-radius: var(--radius);
  margin: 10px 0 6px;
  overflow-x: auto;
  font-family: "JetBrains Mono", "Fira Code", "Cascadia Code", "Source Code Pro", Menlo, Consolas, monospace;
  font-size: var(--nb-font-sm);
  line-height: 1.6;
  border: 1px solid hsl(var(--border));
}

.message-bubble.user .message-text :deep(pre) {
  background: hsl(var(--primary-foreground) / 0.15);
  border-color: hsl(var(--primary-foreground) / 0.2);
}

.message-text :deep(code) {
  background: hsl(var(--muted));
  padding: 1px 4px;
  border-radius: 4px;
  font-family: "JetBrains Mono", "Fira Code", "Cascadia Code", "Source Code Pro", Menlo, Consolas, monospace;
  font-size: var(--nb-font-sm);
}

.message-bubble.user .message-text :deep(code) {
  background: hsl(var(--primary-foreground) / 0.15);
}

.message-text :deep(strong) {
  font-weight: 600;
}

/* ── Markdown 标题 ── */
.message-text :deep(h1),
.message-text :deep(h2),
.message-text :deep(h3),
.message-text :deep(h4) {
  margin: 12px 0 6px;
  font-weight: 600;
  line-height: 1.4;
}

.message-text :deep(h1) { font-size: var(--nb-font-xl); }
.message-text :deep(h2) { font-size: var(--nb-font-lg); }
.message-text :deep(h3) { font-size: var(--nb-font-base); }
.message-text :deep(h4) { font-size: var(--nb-font-base); }

.message-text :deep(p) { margin: 6px 0; }
.message-text :deep(p:first-child) { margin-top: 0; }
.message-text :deep(p:last-child) { margin-bottom: 0; }

.message-text :deep(ul),
.message-text :deep(ol) {
  margin: 6px 0;
  padding-left: 20px;
}

.message-text :deep(li) { margin: 3px 0; }

.message-text :deep(blockquote) {
  margin: 8px 0;
  padding: var(--nb-space-1) var(--nb-space-3);
  border-left: 3px solid hsl(var(--nb-brand));
  color: hsl(var(--muted-foreground));
  background: hsl(var(--muted));
  border-radius: 0 var(--radius) var(--radius) 0;
}

.message-text :deep(table) {
  border-collapse: collapse;
  margin: 8px 0;
  font-size: var(--nb-font-sm);
  width: 100%;
}

.message-text :deep(th),
.message-text :deep(td) {
  border: 1px solid hsl(var(--border));
  padding: var(--nb-space-1) var(--nb-space-2);
  text-align: left;
}

.message-text :deep(th) {
  background: hsl(var(--muted));
  font-weight: 600;
}

.message-text :deep(hr) {
  border: none;
  border-top: 1px solid hsl(var(--border));
  margin: 12px 0;
}

.message-text :deep(a) {
  color: hsl(var(--nb-brand));
  text-decoration: none;
}

.message-text :deep(a:hover) {
  text-decoration: underline;
}

.message-text :deep(pre code) {
  background: none;
  padding: 0;
  border-radius: 0;
  font-size: inherit;
}

/* ── 参考来源 ── */
.message-sources {
  margin-top: var(--nb-space-2);
  padding: var(--nb-space-2) var(--nb-space-3);
  background: hsl(var(--muted));
  border-radius: var(--radius);
  border: 1px solid hsl(var(--border));
}

.sources-header {
  display: flex;
  align-items: center;
  gap: var(--nb-space-1);
  font-size: var(--nb-font-xs);
  font-weight: 500;
  color: hsl(var(--muted-foreground));
  margin-bottom: var(--nb-space-2);
}

.sources-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--nb-space-1);
}

.source-chip {
  font-size: var(--nb-font-xs);
  cursor: default;
}

/* ── 引用核查 ── */
.verification-block {
  margin-top: var(--nb-space-2);
  padding: var(--nb-space-2) var(--nb-space-3);
  background: hsl(var(--muted));
  border-radius: var(--radius);
  border: 1px solid hsl(var(--border));
}

.verification-header {
  display: flex;
  align-items: center;
  gap: var(--nb-space-1);
  font-size: var(--nb-font-xs);
  font-weight: 500;
  color: hsl(var(--muted-foreground));
  cursor: pointer;
  user-select: none;
}

.verification-header:hover {
  color: hsl(var(--foreground));
}

.verification-badge {
  margin-left: auto;
  padding: 1px var(--nb-space-2);
  border-radius: 9999px;
  font-size: 0.625rem;
  font-weight: 500;
}

.verification-badge.risk-low {
  background: hsl(var(--nb-success-bg));
  color: hsl(var(--nb-success));
}

.verification-badge.risk-medium {
  background: hsl(var(--nb-warning-bg));
  color: hsl(var(--nb-warning));
}

.verification-badge.risk-high {
  background: hsl(var(--nb-danger-bg));
  color: hsl(var(--nb-danger));
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
  border-top: 1px solid hsl(var(--border));
}

.verification-item {
  display: grid;
  grid-template-columns: 80px 1fr 40px;
  align-items: center;
  gap: 6px;
  font-size: var(--nb-font-xs);
  margin-bottom: 6px;
}

.verification-item .label {
  color: hsl(var(--muted-foreground));
  white-space: nowrap;
  text-align: right;
}

.verification-item .value {
  color: hsl(var(--foreground));
  font-weight: 500;
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.verification-item .value.warning {
  color: hsl(var(--nb-warning));
}

.verification-item .value.span-end {
  grid-column: 2 / 4;
}

.verification-disclaimer {
  margin-top: var(--nb-space-2);
  padding: var(--nb-space-2);
  background: hsl(var(--nb-warning-bg));
  border-radius: var(--radius);
  font-size: var(--nb-font-xs);
  color: hsl(var(--muted-foreground));
  line-height: 1.5;
}

/* ── 评估指标 ── */
.metrics-section {
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px solid hsl(var(--border));
}

.metrics-title {
  font-size: var(--nb-font-xs);
  font-weight: 500;
  color: hsl(var(--muted-foreground));
  margin-bottom: 6px;
}

.progress-bar {
  width: 100%;
  height: 6px;
  background: hsl(var(--muted));
  border-radius: 9999px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: hsl(var(--nb-brand));
  border-radius: 9999px;
  transition: width 0.3s ease;
}

/* ── 耗时 ── */
.message-timing {
  display: flex;
  align-items: center;
  gap: var(--nb-space-1);
  margin-top: 6px;
  font-size: var(--nb-font-xs);
  color: hsl(var(--muted-foreground));
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
  background: hsl(var(--nb-brand));
  opacity: 0.6;
  animation: nb-pulse-dot 1.4s ease-in-out infinite;
}

.thinking-dot:nth-child(2) { animation-delay: 0.2s; }
.thinking-dot:nth-child(3) { animation-delay: 0.4s; }
</style>
