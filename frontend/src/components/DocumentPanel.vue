<template>
  <div class="document-panel cus-scroll">
    <!-- 标题 -->
    <div class="panel-header">
      <h3>文档管理</h3>
      <button class="hm-icon-btn" @click="refresh" title="刷新">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
          <path d="M1 4v6h6M23 20v-6h-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          <path d="M20.49 9A9 9 0 005.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 013.51 15" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </button>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-grid">
      <div class="hm-stat-card">
        <div class="stat-icon" style="background: var(--hm-brand-light); color: var(--hm-brand);">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
            <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M14 2v6h6M16 13H8M16 17H8M10 9H8" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </div>
        <div class="stat-info">
          <span class="stat-value">{{ store.stats.document_count }}</span>
          <span class="stat-label">文档块</span>
        </div>
      </div>
      <div class="hm-stat-card">
        <div class="stat-icon" style="background: rgba(100, 187, 92, 0.1); color: var(--hm-success);">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
            <path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </div>
        <div class="stat-info">
          <span class="stat-value">{{ store.stats.source_count }}</span>
          <span class="stat-label">文档数</span>
        </div>
      </div>
    </div>

    <!-- 上传区域 -->
    <div class="upload-area">
      <el-upload
        action="#"
        :auto-upload="false"
        :on-change="handleUpload"
        accept=".html,.htm,.txt,.md,.pdf,.docx"
        :show-file-list="false"
        multiple
        drag
      >
        <div class="upload-inner">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none">
            <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12" stroke="var(--hm-brand)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          <p class="upload-text">拖拽或点击上传</p>
          <p class="upload-hint">支持多选 · HTML / TXT / MD / PDF / DOCX</p>
        </div>
      </el-upload>
      <div v-if="uploadStatus" class="status-msg" :class="uploadStatusType">
        {{ uploadStatus }}
      </div>
    </div>

    <!-- 批量加载 -->
    <button
      class="hm-action-btn load-btn"
      @click="handleLoadAll"
      :disabled="loading"
    >
      <span v-if="loading" class="hm-loading-spinner"></span>
      <template v-else>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
          <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </template>
      {{ loading ? '加载中...' : '加载本地文档' }}
    </button>
    <div v-if="loadStatus" class="status-msg" :class="loadStatusType">
      {{ loadStatus }}
    </div>

    <!-- 分割线 -->
    <div class="hm-divider"></div>

    <!-- 已加载文档列表 -->
    <div class="documents-section">
      <div class="section-title">
        <span>已加载文档</span>
        <span class="doc-count" v-if="store.documents.length > 0">{{ store.documents.length }}</span>
      </div>
      <div class="doc-list cus-scroll">
        <div v-if="store.documents.length === 0" class="doc-empty">
          <p>暂无已加载的文档</p>
        </div>
        <div
          v-else
          v-for="doc in store.documents"
          :key="doc"
          class="doc-item"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" flex-shrink="0">
            <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" stroke="var(--hm-font-tertiary)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M14 2v6h6" stroke="var(--hm-font-tertiary)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          <span class="doc-name" :title="doc">{{ doc }}</span>
          <button
            class="doc-delete-btn"
            @click="handleDelete(doc)"
            title="删除文档"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
              <path d="M18 6L6 18M6 6l12 12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </button>
        </div>
      </div>

      <!-- 清空全部 -->
      <button
        v-if="store.documents.length > 0"
        class="hm-action-btn clear-all-btn"
        @click="handleClearAll"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
          <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        清空全部文档
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessageBox, ElMessage } from 'element-plus'
import { useChatStore } from '../stores/chat'
import { uploadDocument } from '../api'

const store = useChatStore()
const loading = ref(false)
const uploadStatus = ref('')
const uploadStatusType = ref('') // 'uploading' | 'success' | 'error' | ''
const loadStatus = ref('')
const loadStatusType = ref('') // 'success' | 'error' | ''

const uploadCount = ref({ done: 0, total: 0, success: 0, fail: 0 })

async function handleUpload(file) {
  uploadCount.value.total++
  const idx = uploadCount.value.total
  uploadStatusType.value = 'uploading'
  uploadStatus.value = `正在上传 (${idx}/${idx})...`

  try {
    const result = await uploadDocument(file.raw)
    if (result.error) {
      uploadCount.value.fail++
      uploadStatusType.value = 'error'
      uploadStatus.value = `「${file.name}」: ${result.error}`
    } else {
      uploadCount.value.success++
      uploadStatusType.value = 'success'
      uploadStatus.value = `上传成功 · ${uploadCount.value.success} 个成功 / ${uploadCount.value.fail} 个失败`
      await refresh()
    }
  } catch (error) {
    uploadCount.value.fail++
    uploadStatusType.value = 'error'
    uploadStatus.value = `「${file.name}」上传失败: ${error.message}`
  }

  uploadCount.value.done++
  // 全部完成后重置计数
  if (uploadCount.value.done >= uploadCount.value.total) {
    setTimeout(() => {
      uploadCount.value = { done: 0, total: 0, success: 0, fail: 0 }
      uploadStatusType.value = ''
    }, 3000)
  }
}

async function handleLoadAll() {
  loading.value = true
  loadStatusType.value = 'uploading'
  loadStatus.value = '加载中...'

  try {
    const result = await store.loadAllDocuments()
    loadStatusType.value = 'success'
    loadStatus.value = result.message
  } catch (error) {
    loadStatusType.value = 'error'
    loadStatus.value = `加载失败: ${error.message}`
  } finally {
    loading.value = false
  }
}

async function handleDelete(source) {
  try {
    await ElMessageBox.confirm(
      `确定要删除文档「${source}」吗？相关的向量数据将被永久删除。`,
      '确认删除',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )
    const result = await store.removeDocument(source)
    ElMessage.success(result.message || '删除成功')
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

async function handleClearAll() {
  try {
    await ElMessageBox.confirm(
      '确定要清空所有文档和向量数据吗？此操作不可恢复。',
      '确认清空',
      {
        confirmButtonText: '清空全部',
        cancelButtonText: '取消',
        type: 'error',
      }
    )
    const result = await store.removeAllDocuments()
    ElMessage.success(result.message || '已清空')
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('清空失败')
    }
  }
}

async function refresh() {
  await store.fetchDocuments()
  await store.fetchStats()
}

onMounted(() => {
  refresh()
})
</script>

<style scoped>
.document-panel {
  padding: 20px 16px;
  height: 100%;
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

/* ── 统计卡片 ── */
.stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.stat-icon {
  width: 40px;
  height: 40px;
  border-radius: var(--hm-radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: transform 0.35s var(--hm-spring);
}

.hm-stat-card:hover .stat-icon {
  transform: scale(1.1) rotate(-3deg);
}

.stat-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.stat-value {
  font-size: 20px;
  font-weight: 700;
  color: var(--hm-font-primary);
  line-height: 1.2;
}

.stat-label {
  font-size: 12px;
  color: var(--hm-font-tertiary);
}

/* ── 上传区域 ── */
.upload-area :deep(.el-upload) {
  width: 100%;
}

.upload-area :deep(.el-upload-dragger) {
  width: 100%;
  padding: 20px;
  border: 2px dashed var(--hm-border);
  border-radius: var(--hm-radius-lg);
  background: var(--hm-bg-container-tertiary);
  transition: all 0.3s var(--hm-spring);
}

.upload-area :deep(.el-upload-dragger:hover) {
  border-color: var(--hm-brand);
  background: var(--hm-brand-bg-light);
}

.upload-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

.upload-text {
  font-size: 14px;
  font-weight: 500;
  color: var(--hm-font-primary);
}

.upload-hint {
  font-size: 12px;
  color: var(--hm-font-tertiary);
}

/* ── 按钮 ── */
.load-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px 16px;
  font-size: 13px;
}

/* ── 状态消息 ── */
.status-msg {
  font-size: 12px;
  color: var(--hm-font-secondary);
  text-align: center;
  padding: 6px 0;
  transition: color 0.3s ease;
}

.status-msg.uploading {
  color: #e89a3c;
  animation: status-pulse 1.4s ease-in-out infinite;
}

.status-msg.success {
  color: #64bb5c;
}

.status-msg.error {
  color: var(--hm-error);
}

@keyframes status-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* ── 分割线 ── */
.hm-divider {
  height: 1px;
  background: var(--hm-divider);
  margin: 4px 0;
}

/* ── 文档列表 ── */
.documents-section {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  font-weight: 600;
  color: var(--hm-font-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 10px;
}

.doc-count {
  background: var(--hm-brand-light);
  color: var(--hm-brand);
  padding: 1px 8px;
  border-radius: var(--hm-radius-full);
  font-size: 11px;
  font-weight: 600;
}

.doc-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.doc-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: var(--hm-radius-sm);
  transition: all 0.2s var(--hm-spring);
}

.doc-item:hover {
  background: var(--hm-hover-bg);
}

.doc-name {
  flex: 1;
  font-size: 13px;
  color: var(--hm-font-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
}

.doc-delete-btn {
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  border-radius: var(--hm-radius-sm);
  color: var(--hm-font-tertiary);
  cursor: pointer;
  opacity: 0;
  transition: all 0.2s var(--hm-spring);
}

.doc-item:hover .doc-delete-btn {
  opacity: 1;
}

.doc-delete-btn:hover {
  background: rgba(232, 64, 38, 0.1);
  color: var(--hm-error);
}

.doc-empty {
  text-align: center;
  padding: 24px 16px;
}

.doc-empty p {
  font-size: 13px;
  color: var(--hm-font-tertiary);
}

/* ── 清空全部按钮 ── */
.clear-all-btn {
  flex-shrink: 0;
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  margin-top: 8px;
  padding: 8px 16px;
  font-size: 12px;
  color: var(--hm-error);
  border-color: rgba(232, 64, 38, 0.2);
}

.clear-all-btn:hover {
  background: rgba(232, 64, 38, 0.06);
  border-color: var(--hm-error);
  color: var(--hm-error);
  box-shadow: var(--hm-glow-danger);
}
</style>
