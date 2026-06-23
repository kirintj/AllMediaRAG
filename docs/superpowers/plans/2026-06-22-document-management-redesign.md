# 文档管理布局重构实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将文档管理模块从右侧侧边栏重构为遵循 HarmonyOS Design 规范的独立抽屉页面

**Architecture:** 新建 DocumentDrawer 抽屉容器，拆分为 StatsHeaderCard、UploadArea、DocumentList、DocumentListItem 四个子组件。移除 App.vue 中的右侧固定栏，在 ChatView 工具栏添加入口按钮。所有样式对齐 HMOS mobile-list 布局规范。

**Tech Stack:** Vue 3 Composition API + Pinia + Element Plus + HarmonyOS Design Tokens

---

## 文件结构

### 新建文件
| 文件 | 职责 |
|------|------|
| `frontend/src/features/documents/DocumentDrawer.vue` | 抽屉容器，包含 titlebar、布局、状态管理 |
| `frontend/src/features/documents/StatsHeaderCard.vue` | 统计卡片区域（文档块/文档数/总大小） |
| `frontend/src/features/documents/UploadArea.vue` | 上传区域（拖拽上传 + 批量上传进度） |
| `frontend/src/features/documents/DocumentList.vue` | 文档列表（搜索 + 筛选 + 列表渲染） |
| `frontend/src/features/documents/DocumentListItem.vue` | 单个文档列表项（icon2lines 变体） |

### 修改文件
| 文件 | 变更 |
|------|------|
| `frontend/src/App.vue` | 移除右侧 `<el-aside>`，新增 `<DocumentDrawer>` |
| `frontend/src/features/chat/ChatView.vue` | 工具栏添加文档管理入口按钮 |

### 废弃文件
| 文件 | 说明 |
|------|------|
| `frontend/src/features/documents/DocumentPanel.vue` | 旧侧边栏组件，功能被 DocumentDrawer 替代 |
| `frontend/src/features/documents/DocumentDetailDialog.vue` | 详情弹窗，功能内联到 DocumentListItem |

---

## Task 1: 创建 DocumentListItem 组件

**Files:**
- Create: `frontend/src/features/documents/DocumentListItem.vue`

- [ ] **Step 1: 创建 DocumentListItem.vue 基础结构**

```vue
<template>
  <div
    class="doc-list-item"
    :class="{ 'doc-list-item--hover': isHovered }"
    @mouseenter="isHovered = true"
    @mouseleave="isHovered = false"
  >
    <!-- 左侧：文件类型图标 -->
    <div class="doc-item-icon" :style="typeStyle">
      <span class="type-label">{{ fileTypeLabel }}</span>
    </div>

    <!-- 中间：文本组 -->
    <div class="doc-item-text">
      <span class="doc-item-name" :title="source">{{ source }}</span>
      <span class="doc-item-meta">
        <span class="meta-type" :style="typeStyle">{{ fileTypeLabel }}</span>
        <span class="meta-separator">·</span>
        <span class="meta-chunks">{{ chunks }} 块</span>
        <span class="meta-separator">·</span>
        <span class="meta-size">{{ formattedSize }}</span>
      </span>
    </div>

    <!-- 右侧：删除按钮 -->
    <button
      class="doc-item-delete"
      :class="{ 'doc-item-delete--visible': isHovered }"
      @click.stop="$emit('delete', source)"
      title="删除文档"
    >
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
        <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    </button>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  source: { type: String, required: true },
  fileType: { type: String, default: '' },
  chunks: { type: Number, default: 0 },
  fileSize: { type: Number, default: 0 },
})

defineEmits(['delete'])

const isHovered = ref(false)

// 文件类型配置
const TYPE_CONFIG = {
  pdf:  { bg: 'rgba(232, 64, 38, 0.1)',  color: 'var(--harmony-warning)', label: 'PDF' },
  docx: { bg: 'rgba(10, 89, 247, 0.1)',  color: 'var(--harmony-brand)', label: 'DOC' },
  doc:  { bg: 'rgba(10, 89, 247, 0.1)',  color: 'var(--harmony-brand)', label: 'DOC' },
  txt:  { bg: 'rgba(144, 147, 153, 0.1)', color: 'var(--harmony-font-secondary)', label: 'TXT' },
  md:   { bg: 'rgba(0, 0, 0, 0.06)',     color: 'var(--harmony-font-secondary)', label: 'MD' },
  html: { bg: 'rgba(237, 111, 33, 0.1)', color: 'var(--harmony-alert)', label: 'HTML' },
  htm:  { bg: 'rgba(237, 111, 33, 0.1)', color: 'var(--harmony-alert)', label: 'HTML' },
  png:  { bg: 'rgba(100, 187, 92, 0.1)', color: 'var(--harmony-confirm)', label: 'IMG' },
  jpg:  { bg: 'rgba(100, 187, 92, 0.1)', color: 'var(--harmony-confirm)', label: 'IMG' },
  jpeg: { bg: 'rgba(100, 187, 92, 0.1)', color: 'var(--harmony-confirm)', label: 'IMG' },
  bmp:  { bg: 'rgba(100, 187, 92, 0.1)', color: 'var(--harmony-confirm)', label: 'IMG' },
  tiff: { bg: 'rgba(100, 187, 92, 0.1)', color: 'var(--harmony-confirm)', label: 'IMG' },
}

const defaultConfig = { bg: 'rgba(144,147,153,0.1)', color: 'var(--harmony-font-tertiary)', label: '?' }

const typeConfig = computed(() => TYPE_CONFIG[props.fileType] || defaultConfig)

const fileTypeLabel = computed(() => typeConfig.value.label)

const typeStyle = computed(() => ({
  background: typeConfig.value.bg,
  color: typeConfig.value.color,
}))

// 格式化文件大小
const formattedSize = computed(() => {
  if (!props.fileSize || props.fileSize === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let i = 0
  let size = props.fileSize
  while (size >= 1024 && i < units.length - 1) {
    size /= 1024
    i++
  }
  return `${size.toFixed(i === 0 ? 0 : 1)} ${units[i]}`
})
</script>

<style scoped>
.doc-list-item {
  display: flex;
  align-items: center;
  gap: var(--harmony-padding-level6);
  padding: var(--harmony-padding-level4) var(--harmony-padding-level6);
  min-height: 72px;
  border-radius: var(--harmony-corner-radius-level4);
  transition: background 0.2s var(--harmony-ease-out);
  cursor: default;
}

.doc-list-item:hover {
  background: var(--harmony-interactive-hover);
}

.doc-list-item:active {
  background: var(--harmony-interactive-pressed);
}

/* 左侧图标 */
.doc-item-icon {
  width: 48px;
  height: 48px;
  border-radius: var(--harmony-corner-radius-level6);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: transform 0.2s var(--harmony-ease-out);
}

.doc-list-item:hover .doc-item-icon {
  transform: scale(1.05);
}

.type-label {
  font-size: var(--harmony-font-size-caption-l);
  font-weight: var(--harmony-font-weight-caption-l);
  letter-spacing: 0.5px;
}

/* 中间文本组 */
.doc-item-text {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.doc-item-name {
  font-size: var(--harmony-font-size-body-l);
  font-weight: var(--harmony-font-weight-subtitle-m);
  color: var(--harmony-font-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.doc-item-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: var(--harmony-font-size-body-s);
  color: var(--harmony-font-tertiary);
}

.meta-type {
  padding: 1px 6px;
  border-radius: var(--harmony-corner-radius-level4);
  font-size: var(--harmony-font-size-caption-m);
  font-weight: var(--harmony-font-weight-caption-l);
}

.meta-separator {
  color: var(--harmony-font-fourth);
}

/* 右侧删除按钮 */
.doc-item-delete {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  border-radius: var(--harmony-corner-radius-level4);
  color: var(--harmony-font-tertiary);
  cursor: pointer;
  opacity: 0;
  transition: all 0.2s var(--harmony-ease-out);
}

.doc-item-delete--visible {
  opacity: 1;
}

.doc-item-delete:hover {
  background: var(--harmony-danger-hover-bg);
  color: var(--harmony-warning);
}
</style>
```

- [ ] **Step 2: 验证组件渲染**

在浏览器中临时引入组件测试渲染效果：
- 48×48 图标正确显示
- 文件名单行截断
- 元数据行显示类型标签 + 块数 + 大小
- hover 时删除按钮淡入

- [ ] **Step 3: 提交**

```bash
git add frontend/src/features/documents/DocumentListItem.vue
git commit -m "feat(documents): add DocumentListItem component with icon2lines layout"
```

---

## Task 2: 创建 StatsHeaderCard 组件

**Files:**
- Create: `frontend/src/features/documents/StatsHeaderCard.vue`

- [ ] **Step 1: 创建 StatsHeaderCard.vue**

```vue
<template>
  <div class="stats-header-card">
    <div class="stat-item">
      <span class="stat-value">{{ stats.document_count }}</span>
      <span class="stat-label">文档块</span>
    </div>
    <div class="stat-divider"></div>
    <div class="stat-item">
      <span class="stat-value">{{ stats.source_count }}</span>
      <span class="stat-label">文档数</span>
    </div>
    <div class="stat-divider"></div>
    <div class="stat-item">
      <span class="stat-value">{{ formattedSize }}</span>
      <span class="stat-label">总大小</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  stats: {
    type: Object,
    default: () => ({ document_count: 0, source_count: 0, total_size: 0 })
  }
})

const formattedSize = computed(() => {
  const bytes = props.stats.total_size || 0
  if (bytes === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let i = 0
  let size = bytes
  while (size >= 1024 && i < units.length - 1) {
    size /= 1024
    i++
  }
  return `${size.toFixed(i === 0 ? 0 : 1)} ${units[i]}`
})
</script>

<style scoped>
.stats-header-card {
  display: flex;
  align-items: center;
  background: var(--harmony-comp-background-primary);
  border-radius: var(--harmony-corner-radius-level8);
  padding: var(--harmony-padding-level6);
  box-shadow: var(--harmony-shadow-sm);
}

.stat-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.stat-value {
  font-size: var(--harmony-font-size-title-m);
  font-weight: var(--harmony-font-weight-title-m);
  color: var(--harmony-font-primary);
  line-height: 1.2;
}

.stat-label {
  font-size: var(--harmony-font-size-body-s);
  color: var(--harmony-font-tertiary);
}

.stat-divider {
  width: 1px;
  height: 32px;
  background: var(--harmony-comp-divider);
}
</style>
```

- [ ] **Step 2: 验证组件渲染**

确认：
- 3 列统计数字居中显示
- 分割线正确分隔
- 使用 HMOS token 变量

- [ ] **Step 3: 提交**

```bash
git add frontend/src/features/documents/StatsHeaderCard.vue
git commit -m "feat(documents): add StatsHeaderCard component"
```

---

## Task 3: 创建 UploadArea 组件

**Files:**
- Create: `frontend/src/features/documents/UploadArea.vue`

- [ ] **Step 1: 创建 UploadArea.vue**

```vue
<template>
  <div class="upload-area">
    <el-upload
      action="#"
      :auto-upload="false"
      :on-change="handleChange"
      accept=".html,.htm,.txt,.md,.pdf,.docx,.png,.jpg,.jpeg,.bmp,.tiff"
      :show-file-list="false"
      multiple
      drag
    >
      <div class="upload-inner">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none">
          <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12" stroke="var(--harmony-brand)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <p class="upload-text">拖拽或点击上传</p>
        <p class="upload-hint">支持多选 · HTML / TXT / MD / PDF / DOCX / 图片</p>
      </div>
    </el-upload>

    <!-- 状态消息 -->
    <div v-if="status" class="status-msg" :class="statusType">
      {{ status }}
    </div>

    <!-- 批量上传进度 -->
    <BatchUploadProgress
      v-if="batchTaskId"
      :task-id="batchTaskId"
      :total="batchTotal"
      @close="batchTaskId = null"
      @complete="handleBatchComplete"
    />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { uploadDocument, uploadBatch } from '../../api/documents.js'
import BatchUploadProgress from './BatchUploadProgress.vue'

const emit = defineEmits(['uploaded'])

const status = ref('')
const statusType = ref('')
const batchTaskId = ref(null)
const batchTotal = ref(0)
const pendingFiles = ref([])
let batchTimer = null
const isUploading = ref(false)

function handleChange(file) {
  if (isUploading.value) {
    ElMessage.warning('有文件正在上传中，请稍后再试')
    return
  }

  pendingFiles.value.push(file)

  if (batchTimer) clearTimeout(batchTimer)

  batchTimer = setTimeout(async () => {
    const filesToUpload = [...pendingFiles.value]
    pendingFiles.value = []
    batchTimer = null

    if (filesToUpload.length === 0) return

    if (filesToUpload.length >= 20) {
      await handleBatchUpload(filesToUpload)
    } else {
      await handleMultipleUploads(filesToUpload)
    }
  }, 100)
}

async function handleBatchUpload(files) {
  isUploading.value = true
  try {
    statusType.value = 'uploading'
    status.value = `正在批量上传 ${files.length} 个文件...`

    const result = await uploadBatch(files)

    if (result.mode === 'sync') {
      statusType.value = 'success'
      status.value = `上传成功 · ${result.success} 个成功 / ${result.failed} 个失败`
      emit('uploaded')
    } else {
      status.value = ''
      batchTaskId.value = result.task_id
      batchTotal.value = result.total
    }
  } catch (error) {
    statusType.value = 'error'
    status.value = `批量上传失败: ${error.message}`
  } finally {
    isUploading.value = false
  }
}

async function handleMultipleUploads(files) {
  const total = files.length
  let done = 0
  let success = 0
  let fail = 0
  isUploading.value = true

  try {
    for (let i = 0; i < files.length; i++) {
      statusType.value = 'uploading'
      status.value = `正在上传 (${i + 1}/${total})...`

      try {
        const result = await uploadDocument(files[i].raw)
        if (result.error) {
          fail++
          statusType.value = 'error'
          status.value = `「${files[i].name}」: ${result.error}`
        } else {
          success++
        }
      } catch (error) {
        fail++
        statusType.value = 'error'
        status.value = `「${files[i].name}」上传失败: ${error.message}`
      }

      done++
    }

    if (fail === 0) {
      statusType.value = 'success'
      status.value = `上传成功 · ${success} 个文件`
    } else {
      statusType.value = 'error'
      status.value = `上传完成 · ${success} 个成功 / ${fail} 个失败`
    }

    emit('uploaded')

    setTimeout(() => {
      statusType.value = ''
      status.value = ''
    }, 3000)
  } finally {
    isUploading.value = false
  }
}

async function handleBatchComplete({ success }) {
  ElMessage.success(`批量索引完成，成功 ${success} 个`)
  batchTaskId.value = null
  emit('uploaded')
}
</script>

<style scoped>
.upload-area :deep(.el-upload) {
  width: 100%;
}

.upload-area :deep(.el-upload-dragger) {
  width: 100%;
  padding: var(--harmony-padding-level8);
  border: 2px dashed var(--harmony-comp-divider);
  border-radius: var(--harmony-corner-radius-level8);
  background: var(--harmony-comp-background-primary);
  transition: all 0.2s var(--harmony-ease-out);
}

.upload-area :deep(.el-upload-dragger:hover) {
  border-color: var(--harmony-brand);
  background: var(--harmony-brand-light);
}

.upload-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.upload-text {
  font-size: var(--harmony-font-size-body-m);
  font-weight: var(--harmony-font-weight-subtitle-s);
  color: var(--harmony-font-primary);
}

.upload-hint {
  font-size: var(--harmony-font-size-body-s);
  color: var(--harmony-font-tertiary);
}

.status-msg {
  font-size: var(--harmony-font-size-body-s);
  text-align: center;
  padding: 8px 0;
  transition: color 0.3s var(--harmony-ease-out);
}

.status-msg.uploading {
  color: var(--harmony-alert);
  animation: status-pulse 1.4s ease-in-out infinite;
}

.status-msg.success {
  color: var(--harmony-confirm);
}

.status-msg.error {
  color: var(--harmony-warning);
}

@keyframes status-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
</style>
```

- [ ] **Step 2: 验证上传功能**

测试场景：
- 拖拽单个文件上传
- 拖拽多个文件批量上传
- 上传进度显示
- 错误状态显示

- [ ] **Step 3: 提交**

```bash
git add frontend/src/features/documents/UploadArea.vue
git commit -m "feat(documents): add UploadArea component with batch upload support"
```

---

## Task 4: 创建 DocumentList 组件

**Files:**
- Create: `frontend/src/features/documents/DocumentList.vue`

- [ ] **Step 1: 创建 DocumentList.vue**

```vue
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
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
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
      <!-- 加载状态 -->
      <div v-if="loading" class="skeleton-list">
        <div v-for="i in 3" :key="i" class="skeleton-item">
          <div class="skeleton-icon"></div>
          <div class="skeleton-text">
            <div class="skeleton-line" style="width: 60%"></div>
            <div class="skeleton-line" style="width: 40%"></div>
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-else-if="filteredDocs.length === 0" class="empty-state">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none">
          <path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z" stroke="var(--harmony-font-fourth)" stroke-width="1.5"/>
        </svg>
        <p v-if="searchQuery || activeFilter">未找到匹配的文档</p>
        <p v-else>暂无已导入的文档</p>
        <button v-if="searchQuery || activeFilter" class="clear-filter-btn" @click="clearFilters">
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
          :chunks="doc.chunks"
          :file-size="doc.file_size"
          @delete="handleDelete"
        />
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessageBox, ElMessage } from 'element-plus'
import { useDocumentStore } from '../../stores/useDocumentStore.js'
import DocumentListItem from './DocumentListItem.vue'

const store = useDocumentStore()

const searchQuery = ref('')
const activeFilter = ref('')
const loading = ref(false)

// 筛选 Chips 配置
const filterChips = [
  { label: '全部', value: '' },
  { label: 'PDF', value: 'pdf' },
  { label: 'DOCX', value: 'docx' },
  { label: 'MD', value: 'md' },
  { label: 'TXT', value: 'txt' },
  { label: '图片', value: 'image' },
]

// 切换筛选
function toggleFilter(value) {
  activeFilter.value = activeFilter.value === value ? '' : value
}

// 清除所有筛选
function clearFilters() {
  searchQuery.value = ''
  activeFilter.value = ''
}

// 过滤后的文档列表
const filteredDocs = computed(() => {
  let docs = store.documentDetails

  // 按搜索词过滤
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    docs = docs.filter(d => d.source.toLowerCase().includes(query))
  }

  // 按类型过滤
  if (activeFilter.value) {
    if (activeFilter.value === 'image') {
      docs = docs.filter(d => ['png', 'jpg', 'jpeg', 'bmp', 'tiff'].includes(d.file_type))
    } else {
      docs = docs.filter(d => d.file_type === activeFilter.value)
    }
  }

  return docs
})

// 删除文档
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

// 加载文档详情
async function loadDetails() {
  loading.value = true
  try {
    await store.fetchDocumentDetails()
  } finally {
    loading.value = false
  }
}

defineExpose({ loadDetails })

onMounted(() => {
  loadDetails()
})
</script>

<style scoped>
.document-list-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* 搜索框 */
.search-bar {
  position: relative;
  margin-bottom: var(--harmony-padding-level4);
}

.search-icon {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--harmony-font-tertiary);
  pointer-events: none;
}

.search-input {
  width: 100%;
  padding: 10px 36px 10px 36px;
  border: 1px solid var(--harmony-comp-divider);
  border-radius: var(--harmony-corner-radius-level10);
  background: var(--harmony-comp-background-primary);
  font-size: var(--harmony-font-size-body-m);
  color: var(--harmony-font-primary);
  outline: none;
  transition: all 0.2s var(--harmony-ease-out);
}

.search-input:focus {
  border-color: var(--harmony-brand);
  box-shadow: var(--harmony-focus-ring);
}

.search-input::placeholder {
  color: var(--harmony-font-tertiary);
}

.search-clear {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  color: var(--harmony-font-tertiary);
  cursor: pointer;
  border-radius: 50%;
  transition: all 0.2s;
}

.search-clear:hover {
  background: var(--harmony-interactive-hover);
  color: var(--harmony-font-primary);
}

/* 筛选 Chips */
.filter-chips {
  display: flex;
  gap: 8px;
  margin-bottom: var(--harmony-padding-level6);
  overflow-x: auto;
  scrollbar-width: none;
}

.filter-chips::-webkit-scrollbar {
  display: none;
}

.chip {
  padding: 6px 14px;
  border: 1px solid var(--harmony-comp-divider);
  border-radius: var(--harmony-radius-full);
  background: var(--harmony-comp-background-primary);
  font-size: var(--harmony-font-size-body-s);
  color: var(--harmony-font-secondary);
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s var(--harmony-ease-out);
}

.chip:hover {
  border-color: var(--harmony-brand);
  color: var(--harmony-brand);
}

.chip--active {
  background: var(--harmony-brand);
  border-color: var(--harmony-brand);
  color: white;
}

.chip--active:hover {
  background: var(--harmony-brand-hover);
  border-color: var(--harmony-brand-hover);
  color: white;
}

/* 文档列表 */
.doc-list {
  flex: 1;
  overflow-y: auto;
  background: var(--harmony-comp-background-primary);
  border-radius: var(--harmony-corner-radius-level8);
  padding: var(--harmony-padding-level4) 0;
}

/* Skeleton 加载状态 */
.skeleton-list {
  padding: 0 var(--harmony-padding-level6);
}

.skeleton-item {
  display: flex;
  align-items: center;
  gap: var(--harmony-padding-level6);
  padding: var(--harmony-padding-level4) 0;
}

.skeleton-icon {
  width: 48px;
  height: 48px;
  border-radius: var(--harmony-corner-radius-level6);
  background: var(--harmony-comp-background-tertiary);
  animation: skeleton-pulse 1.5s ease-in-out infinite;
}

.skeleton-text {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.skeleton-line {
  height: 14px;
  border-radius: 4px;
  background: var(--harmony-comp-background-tertiary);
  animation: skeleton-pulse 1.5s ease-in-out infinite;
}

@keyframes skeleton-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* 空状态 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 48px 16px;
  color: var(--harmony-font-tertiary);
  font-size: var(--harmony-font-size-body-m);
}

.clear-filter-btn {
  padding: 8px 16px;
  border: 1px solid var(--harmony-brand);
  border-radius: var(--harmony-corner-radius-level10);
  background: transparent;
  color: var(--harmony-brand);
  font-size: var(--harmony-font-size-body-s);
  cursor: pointer;
  transition: all 0.2s var(--harmony-ease-out);
}

.clear-filter-btn:hover {
  background: var(--harmony-brand-light);
}
</style>
```

- [ ] **Step 2: 验证功能**

测试场景：
- 搜索框实时过滤
- Chips 筛选切换
- 搜索 + 筛选交集
- 空状态显示
- Skeleton 加载状态

- [ ] **Step 3: 提交**

```bash
git add frontend/src/features/documents/DocumentList.vue
git commit -m "feat(documents): add DocumentList component with search and filter"
```

---

## Task 5: 创建 DocumentDrawer 主容器

**Files:**
- Create: `frontend/src/features/documents/DocumentDrawer.vue`

- [ ] **Step 1: 创建 DocumentDrawer.vue**

```vue
<template>
  <Teleport to="body">
    <Transition name="drawer">
      <div v-if="modelValue" class="drawer-overlay" @click.self="close">
        <div class="drawer-container" :class="drawerClass">
          <!-- Titlebar -->
          <header class="drawer-titlebar">
            <div class="titlebar-content">
              <div class="titlebar-left">
                <h2 class="titlebar-title">文档管理</h2>
                <span class="titlebar-subtitle">
                  {{ store.stats.source_count }} 个文档 · {{ store.stats.document_count }} 块向量
                </span>
              </div>
              <button class="titlebar-close" @click="close" title="关闭">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                  <path d="M18 6L6 18M6 6l12 12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                </svg>
              </button>
            </div>
          </header>

          <!-- 内容区 -->
          <div class="drawer-content">
            <!-- 统计卡片 -->
            <StatsHeaderCard :stats="store.stats" />

            <!-- 上传区域 -->
            <UploadArea @uploaded="handleUploaded" />

            <!-- 文档列表 -->
            <DocumentList ref="docListRef" />
          </div>

          <!-- 底部操作栏 -->
          <footer class="drawer-footer">
            <button
              class="footer-btn primary"
              @click="handleLoadAll"
              :disabled="loading"
            >
              <span v-if="loading" class="harmony-loading-spinner"></span>
              <template v-else>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                  <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </template>
              {{ loading ? '加载中...' : '加载本地文档' }}
            </button>
            <button
              class="footer-btn"
              @click="handleSync"
              :disabled="syncing"
            >
              <span v-if="syncing" class="harmony-loading-spinner"></span>
              <template v-else>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                  <path d="M23 4v6h-6M1 20v-6h6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                  <path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </template>
              {{ syncing ? '同步中...' : '增量同步' }}
            </button>
            <button
              class="footer-btn danger"
              @click="handleClearAll"
              :disabled="!store.hasDocuments"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
              清空
            </button>
          </footer>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { ElMessageBox, ElMessage } from 'element-plus'
import { useDocumentStore } from '../../stores/useDocumentStore.js'
import StatsHeaderCard from './StatsHeaderCard.vue'
import UploadArea from './UploadArea.vue'
import DocumentList from './DocumentList.vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false }
})

const emit = defineEmits(['update:modelValue'])

const store = useDocumentStore()
const docListRef = ref(null)
const loading = ref(false)
const syncing = ref(false)

// 响应式抽屉宽度
const drawerClass = computed(() => {
  if (typeof window === 'undefined') return ''
  const width = window.innerWidth
  if (width < 768) return 'drawer-full'
  if (width < 1024) return 'drawer-medium'
  return 'drawer-large'
})

// 关闭抽屉
function close() {
  emit('update:modelValue', false)
}

// 打开时加载数据
watch(() => props.modelValue, async (val) => {
  if (val) {
    await Promise.all([
      store.fetchStats(),
      docListRef.value?.loadDetails()
    ])
  }
})

// 上传完成回调
function handleUploaded() {
  Promise.all([
    store.fetchDocuments(),
    store.fetchStats(),
    docListRef.value?.loadDetails()
  ])
}

// 加载本地文档
async function handleLoadAll() {
  loading.value = true
  try {
    const result = await store.loadAllDocuments()
    ElMessage.success(result.message || '加载完成')
    handleUploaded()
  } catch (error) {
    ElMessage.error(`加载失败: ${error.message}`)
  } finally {
    loading.value = false
  }
}

// 增量同步
async function handleSync() {
  syncing.value = true
  try {
    const result = await store.syncDocuments()
    const { added, modified, deleted, unchanged } = result.result
    ElMessage.success(`同步完成: 新增 ${added}, 修改 ${modified}, 删除 ${deleted}, 未变 ${unchanged}`)
    handleUploaded()
  } catch (error) {
    ElMessage.error(`同步失败: ${error.message}`)
  } finally {
    syncing.value = false
  }
}

// 清空全部
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
    handleUploaded()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('清空失败')
    }
  }
}

// Esc 键关闭
function handleKeydown(e) {
  if (e.key === 'Escape' && props.modelValue) {
    close()
  }
}

onMounted(() => {
  document.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown)
})
</script>

<style scoped>
/* 遮罩层 */
.drawer-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.4);
  z-index: 1000;
  display: flex;
  justify-content: flex-end;
}

/* 抽屉容器 */
.drawer-container {
  height: 100%;
  background: var(--harmony-background-secondary);
  display: flex;
  flex-direction: column;
  box-shadow: -4px 0 48px rgba(0, 0, 0, 0.15);
}

.drawer-large {
  width: 480px;
}

.drawer-medium {
  width: 400px;
}

.drawer-full {
  width: 100vw;
}

/* Titlebar */
.drawer-titlebar {
  position: sticky;
  top: 0;
  z-index: 10;
  background: var(--harmony-comp-background-primary);
  border-bottom: 1px solid var(--harmony-comp-divider);
}

.titlebar-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
}

.titlebar-left {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.titlebar-title {
  font-size: var(--harmony-font-size-title-m);
  font-weight: var(--harmony-font-weight-title-m);
  color: var(--harmony-font-primary);
}

.titlebar-subtitle {
  font-size: var(--harmony-font-size-body-s);
  color: var(--harmony-font-tertiary);
}

.titlebar-close {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  border-radius: var(--harmony-corner-radius-level8);
  color: var(--harmony-font-secondary);
  cursor: pointer;
  transition: all 0.2s var(--harmony-ease-out);
}

.titlebar-close:hover {
  background: var(--harmony-interactive-hover);
  color: var(--harmony-font-primary);
}

/* 内容区 */
.drawer-content {
  flex: 1;
  overflow-y: auto;
  padding: var(--harmony-padding-level6);
  display: flex;
  flex-direction: column;
  gap: var(--harmony-padding-level6);
}

/* 底部操作栏 */
.drawer-footer {
  position: sticky;
  bottom: 0;
  display: flex;
  gap: 8px;
  padding: 12px 20px;
  background: var(--harmony-comp-background-primary);
  border-top: 1px solid var(--harmony-comp-divider);
}

.footer-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px 16px;
  border: 1px solid var(--harmony-comp-divider);
  border-radius: var(--harmony-corner-radius-level10);
  background: var(--harmony-comp-background-primary);
  font-size: var(--harmony-font-size-body-s);
  font-weight: var(--harmony-font-weight-subtitle-s);
  color: var(--harmony-font-primary);
  cursor: pointer;
  transition: all 0.2s var(--harmony-ease-out);
}

.footer-btn:hover:not(:disabled) {
  background: var(--harmony-interactive-hover);
}

.footer-btn:active:not(:disabled) {
  background: var(--harmony-interactive-pressed);
}

.footer-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.footer-btn.primary {
  background: var(--harmony-brand);
  border-color: var(--harmony-brand);
  color: white;
}

.footer-btn.primary:hover:not(:disabled) {
  background: var(--harmony-brand-hover);
  border-color: var(--harmony-brand-hover);
}

.footer-btn.danger {
  color: var(--harmony-warning);
  border-color: rgba(232, 64, 38, 0.3);
}

.footer-btn.danger:hover:not(:disabled) {
  background: var(--harmony-danger-hover-bg);
  border-color: var(--harmony-warning);
}

/* 抽屉动画 */
.drawer-enter-active,
.drawer-leave-active {
  transition: all 0.3s var(--harmony-ease-out);
}

.drawer-enter-from,
.drawer-leave-to {
  opacity: 0;
}

.drawer-enter-from .drawer-container,
.drawer-leave-to .drawer-container {
  transform: translateX(100%);
}
</style>
```

- [ ] **Step 2: 验证抽屉功能**

测试场景：
- 从右侧滑入动画
- 点击遮罩关闭
- Esc 键关闭
- 响应式宽度
- Titlebar 显示摘要信息
- 底部操作栏功能

- [ ] **Step 3: 提交**

```bash
git add frontend/src/features/documents/DocumentDrawer.vue
git commit -m "feat(documents): add DocumentDrawer container with titlebar and footer actions"
```

---

## Task 6: 修改 App.vue 移除右侧栏

**Files:**
- Modify: `frontend/src/App.vue`

- [ ] **Step 1: 移除右侧 el-aside**

找到并删除以下代码块（约第 19-21 行）：

```vue
<!-- 删除这部分 -->
<el-aside width="280px" class="docs-panel harmony-animate-in" style="animation-delay: 0.1s">
  <DocumentPanel />
</el-aside>
```

- [ ] **Step 2: 添加 DocumentDrawer**

在 `<template>` 中添加：

```vue
<!-- 在 </div> 之前添加 -->
<DocumentDrawer v-model="showDocs" />
```

在 `<script setup>` 中添加：

```vue
import DocumentDrawer from './features/documents/DocumentDrawer.vue'

const showDocs = ref(false)
```

- [ ] **Step 3: 删除旧样式**

删除 `<style scoped>` 中的 `.docs-panel` 样式：

```css
/* 删除这段 */
.docs-panel {
  background: var(--harmony-comp-background-primary);
  border-left: 1px solid var(--harmony-comp-divider);
  overflow-y: auto;
}
```

- [ ] **Step 4: 验证布局变化**

确认：
- 右侧栏已移除
- 主内容区占满剩余空间
- 无控制台错误

- [ ] **Step 5: 提交**

```bash
git add frontend/src/App.vue
git commit -m "refactor(app): remove right sidebar and add DocumentDrawer"
```

---

## Task 7: 修改 ChatView 添加入口按钮

**Files:**
- Modify: `frontend/src/features/chat/ChatView.vue`

- [ ] **Step 1: 添加文档管理入口按钮**

在 `<template>` 的 `.chat-header` 中添加按钮：

```vue
<!-- 在 .header-left 之后，.harmony-tab-bar 之前添加 -->
<button
  class="harmony-icon-btn docs-btn"
  @click="$emit('open-docs')"
  title="文档管理"
>
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
    <path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
  </svg>
</button>
```

- [ ] **Step 2: 添加 emit 声明**

在 `<script setup>` 中添加：

```vue
defineEmits(['open-docs'])
```

- [ ] **Step 3: 添加按钮样式**

在 `<style scoped>` 中添加：

```css
.docs-btn {
  margin-left: auto;
  margin-right: 8px;
}
```

- [ ] **Step 4: 验证按钮**

确认：
- 按钮在标题栏右侧显示
- hover 有交互反馈
- 点击触发 emit 事件

- [ ] **Step 5: 提交**

```bash
git add frontend/src/features/chat/ChatView.vue
git commit -m "feat(chat): add document management entry button to header"
```

---

## Task 8: 连接 App.vue 和 ChatView 事件

**Files:**
- Modify: `frontend/src/App.vue`

- [ ] **Step 1: 绑定 open-docs 事件**

修改 ChatView 组件使用：

```vue
<!-- 修改前 -->
<ChatView />

<!-- 修改后 -->
<ChatView @open-docs="showDocs = true" />
```

- [ ] **Step 2: 验证完整流程**

测试场景：
1. 点击 ChatView 的文档管理按钮
2. DocumentDrawer 从右侧滑入
3. 文档列表正确加载
4. 所有操作功能正常（上传、删除、同步等）
5. 关闭抽屉后主界面正常

- [ ] **Step 3: 提交**

```bash
git add frontend/src/App.vue
git commit -m "feat(app): wire up document management button to drawer"
```

---

## Task 9: 清理废弃文件

**Files:**
- Delete: `frontend/src/features/documents/DocumentPanel.vue`
- Delete: `frontend/src/features/documents/DocumentDetailDialog.vue`

- [ ] **Step 1: 确认无引用**

运行搜索确认这两个文件没有被其他地方引用：

```bash
grep -r "DocumentPanel" frontend/src/ --include="*.vue" --include="*.js"
grep -r "DocumentDetailDialog" frontend/src/ --include="*.vue" --include="*.js"
```

- [ ] **Step 2: 删除文件**

```bash
rm frontend/src/features/documents/DocumentPanel.vue
rm frontend/src/features/documents/DocumentDetailDialog.vue
```

- [ ] **Step 3: 验证应用正常**

确认：
- 应用正常启动
- 文档管理功能完整
- 无控制台错误

- [ ] **Step 4: 提交**

```bash
git add -A frontend/src/features/documents/
git commit -m "refactor(documents): remove deprecated DocumentPanel and DocumentDetailDialog"
```

---

## Task 10: 最终验证与样式微调

**Files:**
- Modify: 根据需要微调各组件样式

- [ ] **Step 1: 完整功能测试**

测试清单：
- [ ] 打开文档管理抽屉
- [ ] 查看统计卡片
- [ ] 上传单个文件
- [ ] 上传多个文件（批量）
- [ ] 搜索文档
- [ ] 按类型筛选
- [ ] 删除单个文档
- [ ] 清空全部文档
- [ ] 加载本地文档
- [ ] 增量同步
- [ ] 响应式布局（调整窗口大小）
- [ ] 深色模式切换
- [ ] Esc 键关闭抽屉

- [ ] **Step 2: 视觉对比 HMOS 规范**

对照 `layout-list.md` 检查：
- [ ] Titlebar 间距正确
- [ ] 统计卡片圆角和内边距
- [ ] 列表项高度 72px
- [ ] 分割线 inset 对齐
- [ ] 按钮样式符合规范
- [ ] Token 变量使用正确

- [ ] **Step 3: 最终提交**

```bash
git add -A
git commit -m "feat: complete document management redesign with HMOS layout"
```
