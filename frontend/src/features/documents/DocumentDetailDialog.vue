<template>
  <el-dialog
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
    title=""
    :width="dialogWidth"
    :close-on-click-modal="true"
    class="doc-detail-dialog"
    :append-to-body="true"
    destroy-on-close
  >
    <template #header>
      <div class="dialog-header">
        <div class="dialog-title">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
            <path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z" stroke="var(--hm-brand)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          <span>已导入文档</span>
          <span class="total-badge" v-if="store.documentDetails.length">{{ store.documentDetails.length }}</span>
        </div>
        <div class="dialog-search">
          <svg class="search-icon" width="14" height="14" viewBox="0 0 24 24" fill="none">
            <circle cx="11" cy="11" r="8" stroke="currentColor" stroke-width="2"/>
            <path d="M21 21l-4.35-4.35" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
          </svg>
          <input
            v-model="searchQuery"
            type="text"
            placeholder="搜索文件名..."
            class="search-input"
          />
          <button v-if="searchQuery" class="search-clear" @click="searchQuery = ''">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
              <path d="M18 6L6 18M6 6l12 12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>
          </button>
        </div>
      </div>
    </template>

    <div class="dialog-body cus-scroll">
      <!-- 加载中 -->
      <div v-if="loading" class="loading-state">
        <div class="hm-loading-spinner"></div>
        <span>加载中...</span>
      </div>

      <!-- 空状态 -->
      <div v-else-if="filteredDocs.length === 0 && !searchQuery" class="empty-state">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none">
          <path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z" stroke="var(--hm-font-fourth)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <p>暂无已导入的文档</p>
      </div>

      <!-- 搜索无结果 -->
      <div v-else-if="filteredDocs.length === 0 && searchQuery" class="empty-state">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none">
          <circle cx="11" cy="11" r="8" stroke="var(--hm-font-fourth)" stroke-width="1.5"/>
          <path d="M21 21l-4.35-4.35" stroke="var(--hm-font-fourth)" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
        <p>未找到匹配的文件</p>
      </div>

      <!-- 文档列表 -->
      <div v-else class="doc-grid">
        <div
          v-for="doc in filteredDocs"
          :key="doc.source"
          class="doc-card"
        >
          <div class="doc-card-icon" :style="getTypeStyle(doc.file_type)">
            <span class="type-ext">{{ doc.file_type?.toUpperCase() || '?' }}</span>
          </div>
          <div class="doc-card-info">
            <div class="doc-card-name" :title="doc.source">{{ doc.source }}</div>
            <div class="doc-card-meta">
              <span class="meta-chip" :style="getTypeStyle(doc.file_type)">
                {{ doc.file_type?.toUpperCase() || '未知' }}
              </span>
              <span class="meta-item">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
                  <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                  <path d="M14 2v6h6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                {{ doc.chunks }} 块
              </span>
              <span class="meta-item">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
                  <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                {{ formatSize(doc.file_size) }}
              </span>
            </div>
          </div>
          <button
            class="doc-card-delete"
            @click="handleDelete(doc.source)"
            title="删除文档"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
              <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </button>
        </div>
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <span class="footer-stats" v-if="store.documentDetails.length > 0">
          共 {{ store.documentDetails.length }} 个文件 · {{ totalChunks }} 个向量块 · {{ formatSize(totalSize) }}
        </span>
        <button class="footer-close-btn" @click="$emit('update:modelValue', false)">关闭</button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ElMessageBox, ElMessage } from 'element-plus'
import { useDocumentStore } from '../../stores/useDocumentStore.js'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue', 'deleted'])

const store = useDocumentStore()
const searchQuery = ref('')
const loading = ref(false)

// 响应式弹窗宽度
const dialogWidth = computed(() => {
  if (typeof window !== 'undefined' && window.innerWidth < 640) return '95%'
  return '640px'
})

// 打开时加载详情
watch(() => props.modelValue, async (val) => {
  if (val) {
    loading.value = true
    searchQuery.value = ''
    await store.fetchDocumentDetails()
    loading.value = false
  }
})

// 过滤后的文档列表
const filteredDocs = computed(() => {
  if (!searchQuery.value) return store.documentDetails
  const q = searchQuery.value.toLowerCase()
  return store.documentDetails.filter(d => d.source.toLowerCase().includes(q))
})

const totalChunks = computed(() =>
  store.documentDetails.reduce((sum, d) => sum + (d.chunks || 0), 0)
)
const totalSize = computed(() =>
  store.documentDetails.reduce((sum, d) => sum + (d.file_size || 0), 0)
)

// 文件类型颜色映射
const TYPE_COLORS = {
  pdf:  { bg: 'rgba(232, 64, 38, 0.1)',  color: '#E84026', border: 'rgba(232, 64, 38, 0.2)' },
  docx: { bg: 'rgba(10, 89, 247, 0.1)',  color: '#0A59F7', border: 'rgba(10, 89, 247, 0.2)' },
  doc:  { bg: 'rgba(10, 89, 247, 0.1)',  color: '#0A59F7', border: 'rgba(10, 89, 247, 0.2)' },
  txt:  { bg: 'rgba(144, 147, 153, 0.1)', color: '#909399', border: 'rgba(144, 147, 153, 0.2)' },
  md:   { bg: 'rgba(0, 0, 0, 0.06)',     color: '#606266', border: 'rgba(0, 0, 0, 0.1)' },
  html: { bg: 'rgba(237, 111, 33, 0.1)', color: '#ED6F21', border: 'rgba(237, 111, 33, 0.2)' },
  htm:  { bg: 'rgba(237, 111, 33, 0.1)', color: '#ED6F21', border: 'rgba(237, 111, 33, 0.2)' },
  png:  { bg: 'rgba(100, 187, 92, 0.1)', color: '#64BB5C', border: 'rgba(100, 187, 92, 0.2)' },
  jpg:  { bg: 'rgba(100, 187, 92, 0.1)', color: '#64BB5C', border: 'rgba(100, 187, 92, 0.2)' },
  jpeg: { bg: 'rgba(100, 187, 92, 0.1)', color: '#64BB5C', border: 'rgba(100, 187, 92, 0.2)' },
  bmp:  { bg: 'rgba(100, 187, 92, 0.1)', color: '#64BB5C', border: 'rgba(100, 187, 92, 0.2)' },
  tiff: { bg: 'rgba(100, 187, 92, 0.1)', color: '#64BB5C', border: 'rgba(100, 187, 92, 0.2)' },
}

function getTypeStyle(type) {
  const c = TYPE_COLORS[type] || { bg: 'rgba(144,147,153,0.1)', color: '#909399', border: 'rgba(144,147,153,0.2)' }
  return {
    background: c.bg,
    color: c.color,
    borderColor: c.border,
  }
}

function formatSize(bytes) {
  if (!bytes || bytes === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let i = 0
  let size = bytes
  while (size >= 1024 && i < units.length - 1) {
    size /= 1024
    i++
  }
  return `${size.toFixed(i === 0 ? 0 : 1)} ${units[i]}`
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
        customClass: 'delete-confirm-box',
      }
    )
    const result = await store.removeDocument(source)
    ElMessage.success(result.message || '删除成功')
    emit('deleted', source)
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}
</script>

<style scoped>
/* ── 弹窗头部 ── */
.dialog-header {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.dialog-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: var(--hm-font-primary);
}

.total-badge {
  background: var(--hm-brand-light);
  color: var(--hm-brand);
  padding: 1px 10px;
  border-radius: var(--hm-radius-full);
  font-size: 12px;
  font-weight: 600;
}

.dialog-search {
  position: relative;
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: 12px;
  color: var(--hm-font-tertiary);
  pointer-events: none;
}

.search-input {
  width: 100%;
  padding: 8px 34px 8px 34px;
  border: 1px solid var(--hm-border);
  border-radius: var(--hm-radius-full);
  background: var(--hm-bg-container-tertiary);
  font-size: 13px;
  color: var(--hm-font-primary);
  outline: none;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.search-input:focus {
  border-color: var(--hm-brand);
  box-shadow: var(--hm-focus-ring);
}

.search-input::placeholder {
  color: var(--hm-font-tertiary);
}

.search-clear {
  position: absolute;
  right: 8px;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  color: var(--hm-font-tertiary);
  cursor: pointer;
  border-radius: 50%;
  transition: all 0.2s;
}

.search-clear:hover {
  background: var(--hm-hover-bg);
  color: var(--hm-font-primary);
}

/* ── 弹窗内容 ── */
.dialog-body {
  max-height: 50vh;
  overflow-y: auto;
  padding: 4px 0;
}

/* ── 加载 & 空状态 ── */
.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 48px 16px;
  color: var(--hm-font-tertiary);
  font-size: 13px;
}

/* ── 文档卡片网格 ── */
.doc-grid {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.doc-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border-radius: var(--hm-radius-md);
  border: 1px solid transparent;
  transition: all 0.25s var(--hm-spring);
  cursor: default;
}

.doc-card:hover {
  background: var(--hm-hover-bg);
  border-color: var(--hm-border);
}

.doc-card-icon {
  width: 44px;
  height: 44px;
  border-radius: var(--hm-radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border: 1px solid;
  transition: transform 0.3s var(--hm-spring);
}

.doc-card:hover .doc-card-icon {
  transform: scale(1.05) rotate(-2deg);
}

.type-ext {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.5px;
}

.doc-card-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.doc-card-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--hm-font-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.doc-card-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.meta-chip {
  display: inline-flex;
  align-items: center;
  padding: 1px 8px;
  border-radius: var(--hm-radius-full);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.5px;
  border: 1px solid;
}

.meta-item {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 12px;
  color: var(--hm-font-tertiary);
}

.doc-card-delete {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
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

.doc-card:hover .doc-card-delete {
  opacity: 1;
}

.doc-card-delete:hover {
  background: rgba(232, 64, 38, 0.08);
  color: var(--hm-error);
}

/* ── 底部 ── */
.dialog-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.footer-stats {
  font-size: 12px;
  color: var(--hm-font-tertiary);
}

.footer-close-btn {
  padding: 7px 24px;
  border: 1px solid var(--hm-border);
  border-radius: var(--hm-radius-sm);
  background: var(--hm-bg-secondary);
  font-size: 13px;
  font-weight: 500;
  color: var(--hm-font-primary);
  cursor: pointer;
  transition: all 0.2s var(--hm-spring);
}

.footer-close-btn:hover {
  border-color: var(--hm-brand);
  color: var(--hm-brand);
  box-shadow: var(--hm-glow-brand);
}

/* ── 深色模式 ── */
:deep(.el-dialog) {
  border-radius: var(--hm-radius-lg) !important;
  border: 1px solid var(--hm-border-glass) !important;
  box-shadow: var(--hm-shadow-xl) !important;
  background: var(--hm-bg-primary) !important;
}

:deep(.el-dialog__header) {
  padding: 20px 24px 16px !important;
  margin-right: 0 !important;
  border-bottom: 1px solid var(--hm-divider);
}

:deep(.el-dialog__body) {
  padding: 16px 24px !important;
}

:deep(.el-dialog__footer) {
  padding: 12px 24px 16px !important;
  border-top: 1px solid var(--hm-divider);
}

:deep(.el-dialog__headerbtn) {
  top: 20px !important;
  right: 20px !important;
}
</style>
