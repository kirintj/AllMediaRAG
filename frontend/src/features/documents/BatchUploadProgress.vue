<template>
  <div class="batch-progress-panel">
    <!-- 标题 -->
    <div class="panel-header">
      <h3>批量上传进度</h3>
      <span class="task-id">{{ taskId }}</span>
    </div>

    <!-- 阶段 1：上传文件 -->
    <div class="phase-section">
      <div class="phase-header">
        <div class="phase-label">
          <span class="phase-icon" :class="uploadPhaseClass">
            <svg v-if="uploadPhaseClass === 'done'" width="14" height="14" viewBox="0 0 24 24" fill="none">
              <path d="M20 6L9 17l-5-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <span v-else-if="uploadPhaseClass === 'running'" class="phase-dot"></span>
            <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/>
            </svg>
          </span>
          <span class="phase-name">上传文件</span>
        </div>
        <span class="phase-count" v-if="status">
          {{ status.upload.current }} / {{ status.upload.total }}
        </span>
      </div>
      <el-progress
        :percentage="uploadPercent"
        :status="uploadProgressStatus"
        :stroke-width="8"
        :show-text="true"
      />
      <div class="phase-fail-hint" v-if="status && status.upload.failed && status.upload.failed.length > 0">
        <span class="fail-count">{{ status.upload.failed.length }} 个文件上传失败</span>
      </div>
    </div>

    <!-- 阶段 2：建立索引 -->
    <div class="phase-section" :class="{ disabled: !indexingActive }">
      <div class="phase-header">
        <div class="phase-label">
          <span class="phase-icon" :class="indexPhaseClass">
            <svg v-if="indexPhaseClass === 'done'" width="14" height="14" viewBox="0 0 24 24" fill="none">
              <path d="M20 6L9 17l-5-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <span v-else-if="indexPhaseClass === 'running'" class="phase-dot"></span>
            <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/>
            </svg>
          </span>
          <span class="phase-name">建立索引</span>
        </div>
        <span class="phase-count" v-if="status && indexingActive">
          {{ status.index.current }} / {{ status.index.total }}
        </span>
      </div>
      <el-progress
        :percentage="indexPercent"
        :status="indexProgressStatus"
        :stroke-width="8"
        :show-text="true"
      />
      <div class="phase-detail" v-if="status && indexingActive">
        <span class="detail-item success">成功 {{ status.index.success }}</span>
        <span class="detail-item failed" v-if="status.index.failed && status.index.failed.length > 0">
          失败 {{ status.index.failed.length }}
        </span>
      </div>
    </div>

    <!-- 时间信息 -->
    <div class="time-info" v-if="status && (status.status === 'running' || status.status === 'completed')">
      <div class="time-item">
        <span class="time-label">已用时间</span>
        <span class="time-value">{{ formatTime(status.elapsed_seconds) }}</span>
      </div>
      <div class="time-item" v-if="status.status === 'running' && status.estimated_remaining">
        <span class="time-label">预计剩余</span>
        <span class="time-value">{{ formatTime(status.estimated_remaining) }}</span>
      </div>
    </div>

    <!-- 错误状态 -->
    <div class="error-banner" v-if="status && status.status === 'failed'">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
        <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/>
        <line x1="15" y1="9" x2="9" y2="15" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        <line x1="9" y1="9" x2="15" y2="15" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
      </svg>
      <span>任务执行失败</span>
    </div>

    <!-- 失败文件折叠列表 -->
    <div class="failed-section" v-if="allFailedFiles.length > 0">
      <button class="failed-toggle" @click="failedExpanded = !failedExpanded">
        <svg
          width="12" height="12" viewBox="0 0 24 24" fill="none"
          :style="{ transform: failedExpanded ? 'rotate(90deg)' : 'rotate(0deg)' }"
        >
          <path d="M9 18l6-6-6-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <span>失败文件 ({{ allFailedFiles.length }})</span>
      </button>
      <div class="failed-list" v-show="failedExpanded">
        <div class="failed-item" v-for="(file, idx) in allFailedFiles" :key="idx">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" flex-shrink="0">
            <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" stroke="var(--hm-font-tertiary)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M14 2v6h6" stroke="var(--hm-font-tertiary)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          <span class="failed-name" :title="typeof file === 'string' ? file : file.name">
            {{ typeof file === 'string' ? file : file.name }}
          </span>
          <span class="failed-reason" v-if="typeof file === 'object' && file.reason">
            {{ file.reason }}
          </span>
        </div>
      </div>
    </div>

    <!-- 总结信息（完成时） -->
    <div class="summary-section" v-if="status && status.status === 'completed'">
      <div class="hm-divider"></div>
      <div class="summary-grid">
        <div class="summary-item">
          <span class="summary-value success">{{ completedSuccess }}</span>
          <span class="summary-label">索引成功</span>
        </div>
        <div class="summary-item">
          <span class="summary-value" :class="completedFailed > 0 ? 'failed' : 'neutral'">{{ completedFailed }}</span>
          <span class="summary-label">失败</span>
        </div>
        <div class="summary-item">
          <span class="summary-value neutral">{{ formatTime(status.elapsed_seconds) }}</span>
          <span class="summary-label">总耗时</span>
        </div>
      </div>
    </div>

    <!-- 关闭按钮 -->
    <button
      v-if="status && (status.status === 'completed' || status.status === 'failed')"
      class="hm-action-btn close-btn"
      @click="handleClose"
    >
      关闭
    </button>

    <!-- 加载中 -->
    <div class="loading-state" v-if="!status && !fetchError">
      <span class="hm-loading-spinner"></span>
      <span>正在获取任务状态...</span>
    </div>

    <!-- 获取状态失败 -->
    <div class="error-banner" v-if="fetchError">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
        <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/>
        <line x1="15" y1="9" x2="9" y2="15" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        <line x1="9" y1="9" x2="15" y2="15" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
      </svg>
      <span>{{ fetchError }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { getBatchStatus } from '../../api/documents.js'

const props = defineProps({
  taskId: {
    type: String,
    required: true
  },
  total: {
    type: Number,
    required: true
  }
})

const emit = defineEmits(['close', 'complete'])

const status = ref(null)
const fetchError = ref('')
const failedExpanded = ref(false)
let pollTimer = null

// ── 计算属性 ──

const uploadPercent = computed(() => {
  if (!status.value) return 0
  const { current, total } = status.value.upload
  if (total === 0) return 0
  return Math.round((current / total) * 100)
})

const uploadProgressStatus = computed(() => {
  if (!status.value) return ''
  if (status.value.upload.failed && status.value.upload.failed.length > 0) return 'exception'
  if (uploadPercent.value >= 100) return 'success'
  return ''
})

const uploadPhaseClass = computed(() => {
  if (!status.value) return 'pending'
  if (status.value.phase === 'uploading' && status.value.status === 'running') return 'running'
  if (uploadPercent.value >= 100) return 'done'
  return 'pending'
})

const indexingActive = computed(() => {
  if (!status.value) return false
  return status.value.phase === 'indexing' || status.value.index.current > 0
})

const indexPercent = computed(() => {
  if (!status.value || !indexingActive.value) return 0
  const { current, total } = status.value.index
  if (total === 0) return 0
  return Math.round((current / total) * 100)
})

const indexProgressStatus = computed(() => {
  if (!status.value || !indexingActive.value) return ''
  if (status.value.index.failed && status.value.index.failed.length > 0) return 'exception'
  if (indexPercent.value >= 100) return 'success'
  return ''
})

const indexPhaseClass = computed(() => {
  if (!status.value || !indexingActive.value) return 'pending'
  if (status.value.phase === 'indexing' && status.value.status === 'running') return 'running'
  if (status.value.index.current >= status.value.index.total) return 'done'
  return 'pending'
})

const allFailedFiles = computed(() => {
  if (!status.value) return []
  const files = []
  if (status.value.upload.failed) {
    files.push(...status.value.upload.failed)
  }
  if (status.value.index.failed) {
    files.push(...status.value.index.failed)
  }
  return files
})

const completedSuccess = computed(() => {
  if (!status.value) return 0
  return status.value.index.success || 0
})

const completedFailed = computed(() => {
  if (!status.value) return 0
  return allFailedFiles.value.length
})

// ── 方法 ──

function formatTime(seconds) {
  if (!seconds && seconds !== 0) return '--'
  const s = Math.round(seconds)
  if (s < 60) return `${s} 秒`
  const m = Math.floor(s / 60)
  const rem = s % 60
  if (m < 60) return rem > 0 ? `${m} 分 ${rem} 秒` : `${m} 分钟`
  const h = Math.floor(m / 60)
  const remM = m % 60
  return remM > 0 ? `${h} 时 ${remM} 分` : `${h} 小时`
}

async function fetchStatus() {
  try {
    const data = await getBatchStatus(props.taskId)
    status.value = data
    fetchError.value = ''

    // 任务完成或失败时停止轮询并发出事件
    if (data.status === 'completed' || data.status === 'failed') {
      stopPolling()
      emit('complete', {
        success: data.status === 'completed',
        failed: allFailedFiles.value.length
      })
    }
  } catch (err) {
    fetchError.value = `获取状态失败: ${err.message || '未知错误'}`
    // 不停止轮询，允许重试
  }
}

function startPolling() {
  stopPolling()
  fetchStatus()
  pollTimer = setInterval(fetchStatus, 2000)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

function handleClose() {
  stopPolling()
  emit('close')
}

// ── 生命周期 ──

watch(() => props.taskId, (newId) => {
  if (newId) {
    status.value = null
    fetchError.value = ''
    startPolling()
  }
})

onMounted(() => {
  if (props.taskId) {
    startPolling()
  }
})

onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped>
.batch-progress-panel {
  padding: 20px 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* ── 标题 ── */
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.panel-header h3 {
  font-size: 15px;
  font-weight: 600;
  color: var(--hm-font-primary);
}

.task-id {
  font-size: 11px;
  color: var(--hm-font-tertiary);
  font-family: monospace;
  padding: 2px 8px;
  background: var(--hm-bg-container-tertiary);
  border-radius: var(--hm-radius-sm);
}

/* ── 阶段区块 ── */
.phase-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.phase-section.disabled {
  opacity: 0.4;
}

.phase-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.phase-label {
  display: flex;
  align-items: center;
  gap: 8px;
}

.phase-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: var(--hm-radius-full);
  transition: all 0.3s var(--hm-spring);
}

.phase-icon.pending {
  color: var(--hm-font-tertiary);
}

.phase-icon.running {
  color: var(--hm-brand);
}

.phase-icon.done {
  color: var(--hm-success);
}

.phase-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--hm-brand);
  animation: dot-pulse 1.2s ease-in-out infinite;
}

@keyframes dot-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.4; transform: scale(0.7); }
}

.phase-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--hm-font-primary);
}

.phase-count {
  font-size: 12px;
  color: var(--hm-font-secondary);
  font-variant-numeric: tabular-nums;
}

.phase-detail {
  display: flex;
  gap: 12px;
  font-size: 12px;
}

.detail-item.success {
  color: var(--hm-success);
}

.detail-item.failed {
  color: var(--hm-error);
}

.phase-fail-hint {
  font-size: 12px;
}

.fail-count {
  color: var(--hm-error);
}

/* ── Element Plus 进度条覆写 ── */
.batch-progress-panel :deep(.el-progress__text) {
  font-size: 12px !important;
  color: var(--hm-font-secondary);
}

.batch-progress-panel :deep(.el-progress-bar__outer) {
  background: var(--hm-bg-container-tertiary);
  border-radius: var(--hm-radius-full);
}

.batch-progress-panel :deep(.el-progress-bar__inner) {
  border-radius: var(--hm-radius-full);
}

/* ── 时间信息 ── */
.time-info {
  display: flex;
  gap: 24px;
  padding: 10px 14px;
  background: var(--hm-bg-container-tertiary);
  border-radius: var(--hm-radius-md);
}

.time-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.time-label {
  font-size: 11px;
  color: var(--hm-font-tertiary);
}

.time-value {
  font-size: 13px;
  font-weight: 500;
  color: var(--hm-font-primary);
  font-variant-numeric: tabular-nums;
}

/* ── 错误横幅 ── */
.error-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: rgba(232, 64, 38, 0.06);
  border: 1px solid rgba(232, 64, 38, 0.15);
  border-radius: var(--hm-radius-md);
  color: var(--hm-error);
  font-size: 13px;
}

/* ── 失败文件列表 ── */
.failed-section {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.failed-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 0;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 12px;
  font-weight: 500;
  color: var(--hm-error);
  transition: opacity 0.2s ease;
}

.failed-toggle:hover {
  opacity: 0.8;
}

.failed-toggle svg {
  transition: transform 0.2s var(--hm-spring);
  flex-shrink: 0;
}

.failed-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
  max-height: 160px;
  overflow-y: auto;
  padding: 4px 0 4px 18px;
}

.failed-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 8px;
  border-radius: var(--hm-radius-sm);
  font-size: 12px;
}

.failed-item:hover {
  background: var(--hm-hover-bg);
}

.failed-name {
  flex: 1;
  color: var(--hm-font-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
}

.failed-reason {
  flex-shrink: 0;
  font-size: 11px;
  color: var(--hm-font-tertiary);
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ── 总结信息 ── */
.summary-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.hm-divider {
  height: 1px;
  background: var(--hm-divider);
  margin: 4px 0;
}

.summary-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 10px;
}

.summary-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 10px 8px;
  background: var(--hm-bg-container-tertiary);
  border-radius: var(--hm-radius-md);
}

.summary-value {
  font-size: 18px;
  font-weight: 700;
  line-height: 1.2;
}

.summary-value.success {
  color: var(--hm-success);
}

.summary-value.failed {
  color: var(--hm-error);
}

.summary-value.neutral {
  color: var(--hm-font-primary);
}

.summary-label {
  font-size: 11px;
  color: var(--hm-font-tertiary);
}

/* ── 关闭按钮 ── */
.close-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px 16px;
  font-size: 13px;
}

/* ── 加载状态 ── */
.loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 24px 0;
  font-size: 13px;
  color: var(--hm-font-tertiary);
}
</style>
