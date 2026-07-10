<template>
  <div class="document-list-container">
    <!-- 搜索框 -->
    <div class="search-bar">
      <svg class="search-icon" width="16" height="16" viewBox="0 0 24 24" fill="none">
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

    <!-- 类型筛选 Chips -->
    <div class="filter-chips">
      <button
        v-for="chip in filterChips"
        :key="chip.value"
        class="chip"
        :class="{ 'chip--active': activeFilter === chip.value }"
        @click="toggleFilter(chip.value)"
      >
        {{ chip.label }}
      </button>
    </div>

    <!-- 文档列表 -->
    <div class="doc-list cus-scroll">
      <!-- Skeleton 加载态 -->
      <div v-if="loading" class="skeleton-list">
        <div v-for="i in 3" :key="i" class="skeleton-item">
          <div class="skeleton-icon skeleton-pulse"></div>
          <div class="skeleton-text">
            <div class="skeleton-line skeleton-pulse skeleton-line-70"></div>
            <div class="skeleton-line skeleton-pulse skeleton-line-45"></div>
          </div>
        </div>
      </div>

      <!-- 空状态：无文档 -->
      <div v-else-if="store.documentDetails.length === 0" class="empty-state">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none">
          <path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z" stroke="var(--harmony-font-fourth)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <p class="empty-text">暂无已导入的文档</p>
        <p class="empty-hint">上传文件或加载本地文档以开始</p>
      </div>

      <!-- 空状态：搜索/筛选无结果 -->
      <div v-else-if="filteredDocs.length === 0" class="empty-state">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none">
          <circle cx="11" cy="11" r="8" stroke="var(--harmony-font-fourth)" stroke-width="1.5"/>
          <path d="M21 21l-4.35-4.35" stroke="var(--harmony-font-fourth)" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
        <p class="empty-text">未找到匹配的文档</p>
        <button class="clear-filter-btn" @click="clearFilters">
          清除筛选
        </button>
      </div>

      <!-- 文档列表 -->
      <template v-else>
        <DocumentListItem
          v-for="doc in filteredDocs"
          :key="doc.source"
          :source="doc.source"
          :file-type="doc.file_type"
          :chunks="doc.chunk_count"
          :file-size="doc.file_size"
          @delete="handleDelete"
        />
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessageBox, ElMessage } from 'element-plus'
import { useDocumentStore } from '../../stores/useDocumentStore.js'
import DocumentListItem from './DocumentListItem.vue'

const store = useDocumentStore()

const searchQuery = ref('')
const activeFilter = ref('')
const loading = ref(false)

const IMAGE_EXTENSIONS = ['png', 'jpg', 'jpeg', 'bmp', 'tiff']

const filterChips = [
  { label: '全部', value: '' },
  { label: 'PDF', value: 'pdf' },
  { label: 'DOCX', value: 'docx' },
  { label: 'MD', value: 'md' },
  { label: 'TXT', value: 'txt' },
  { label: '图片', value: 'image' },
]

function toggleFilter(value) {
  activeFilter.value = activeFilter.value === value ? '' : value
}

function clearFilters() {
  searchQuery.value = ''
  activeFilter.value = ''
}

const filteredDocs = computed(() => {
  let docs = store.documentDetails

  // 类型筛选
  if (activeFilter.value) {
    docs = docs.filter((doc) => {
      const ext = (doc.file_type || '').toLowerCase()
      if (activeFilter.value === 'image') {
        return IMAGE_EXTENSIONS.includes(ext)
      }
      return ext === activeFilter.value
    })
  }

  // 搜索筛选
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.trim().toLowerCase()
    docs = docs.filter((doc) =>
      (doc.source || '').toLowerCase().includes(q)
    )
  }

  return docs
})

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

async function loadDetails() {
  loading.value = true
  try {
    await store.fetchDocumentDetails()
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadDetails()
})

defineExpose({ loadDetails })
</script>

<style scoped>
.document-list-container {
  display: flex;
  flex-direction: column;
  gap: var(--harmony-padding-level6);
  height: 100%;
}

/* ── 搜索框 ── */
.search-bar {
  position: relative;
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: 12px;
  color: var(--harmony-font-tertiary);
  pointer-events: none;
  transition: color 0.2s var(--harmony-ease-out);
}

.search-input {
  width: 100%;
  height: var(--harmony-control-height-40);
  padding: 0 36px 0 38px;
  font-size: var(--harmony-font-size-body-m);
  color: var(--harmony-font-primary);
  background: var(--harmony-comp-background-tertiary);
  border: 1.5px solid transparent;
  border-radius: var(--harmony-corner-radius-level10);
  outline: none;
  transition: all 0.2s var(--harmony-ease-out);
}

.search-input::placeholder {
  color: var(--harmony-font-fourth);
}

.search-input:focus {
  background: var(--harmony-comp-background-primary);
  border-color: var(--harmony-brand);
  box-shadow: var(--harmony-focus-ring);
}

.search-input:focus ~ .search-icon,
.search-bar:focus-within .search-icon {
  color: var(--harmony-brand);
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
  border-radius: var(--harmony-corner-radius-level6);
  color: var(--harmony-font-tertiary);
  cursor: pointer;
  transition: all 0.15s var(--harmony-ease-out);
}

.search-clear:hover {
  background: var(--harmony-interactive-hover);
  color: var(--harmony-font-secondary);
}

/* ── 类型筛选 Chips ── */
.filter-chips {
  display: flex;
  gap: var(--harmony-padding-level3);
  flex-wrap: wrap;
}

.chip {
  padding: var(--harmony-padding-level3) var(--harmony-padding-level7);
  font-size: var(--harmony-font-size-body-s);
  font-weight: var(--harmony-font-weight-body-s);
  color: var(--harmony-font-secondary);
  background: var(--harmony-comp-background-tertiary);
  border: none;
  border-radius: var(--harmony-radius-full);
  cursor: pointer;
  transition: all 0.2s var(--harmony-ease-out);
  white-space: nowrap;
}

.chip:hover {
  background: var(--harmony-interactive-hover);
}

.chip:active {
  background: var(--harmony-interactive-pressed);
  transition-duration: 0.08s;
}

.chip--active {
  background: var(--harmony-brand);
  color: var(--harmony-font-on-primary);
}

.chip--active:hover {
  background: var(--harmony-brand-hover);
}

/* ── 文档列表 ── */
.doc-list {
  flex: 1;
  overflow-y: auto;
  background: var(--harmony-comp-background-primary);
  border-radius: var(--harmony-corner-radius-level8);
  padding: var(--harmony-padding-level3);
}

/* ── Skeleton 骨架屏 ── */
.skeleton-list {
  display: flex;
  flex-direction: column;
  gap: var(--harmony-padding-level3);
}

.skeleton-item {
  display: flex;
  align-items: center;
  gap: var(--harmony-padding-level5);
  padding: var(--harmony-padding-level4) var(--harmony-padding-level6);
}

.skeleton-icon {
  width: 48px;
  height: 48px;
  border-radius: var(--harmony-corner-radius-level6);
  flex-shrink: 0;
}

.skeleton-text {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--harmony-padding-level3);
}

.skeleton-line {
  height: 14px;
  border-radius: var(--harmony-corner-radius-level4);
}

.skeleton-line-70 { width: 70%; }
.skeleton-line-45 { width: 45%; }

.skeleton-pulse {
  background: var(--harmony-comp-background-tertiary);
  animation: skeleton-pulse 1.8s ease-in-out infinite;
}

@keyframes skeleton-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

/* ── 空状态 ── */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--harmony-padding-level4);
  padding: var(--harmony-padding-level16) var(--harmony-padding-level8);
  text-align: center;
}

.empty-state svg {
  opacity: 0.45;
  margin-bottom: var(--harmony-padding-level2);
}

.empty-text {
  font-size: var(--harmony-font-size-body-m);
  color: var(--harmony-font-tertiary);
}

.empty-hint {
  font-size: var(--harmony-font-size-body-s);
  color: var(--harmony-font-fourth);
}

.clear-filter-btn {
  margin-top: var(--harmony-padding-level4);
  padding: var(--harmony-padding-level3) var(--harmony-padding-level8);
  font-size: var(--harmony-font-size-body-s);
  color: var(--harmony-brand);
  background: var(--harmony-brand-light);
  border: none;
  border-radius: var(--harmony-radius-full);
  cursor: pointer;
  transition: all 0.2s var(--harmony-ease-out);
}

.clear-filter-btn:hover {
  background: var(--harmony-comp-emphasize-tertiary);
}

.clear-filter-btn:active {
  transition-duration: 0.08s;
}
</style>
