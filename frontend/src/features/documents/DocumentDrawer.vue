<template>
  <div class="flex flex-col h-full p-4 gap-4 overflow-y-auto">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <h2 class="text-lg font-semibold text-foreground">文档管理</h2>
    </div>

    <!-- Stats -->
    <div class="flex gap-3">
      <div class="flex-1 p-3 bg-muted rounded-lg text-center">
        <div class="text-xl font-bold text-foreground">{{ docStore.stats.document_count || 0 }}</div>
        <div class="text-[11px] text-muted-foreground">文档</div>
      </div>
      <div class="flex-1 p-3 bg-muted rounded-lg text-center">
        <div class="text-xl font-bold text-foreground">{{ docStore.stats.source_count || 0 }}</div>
        <div class="text-[11px] text-muted-foreground">来源</div>
      </div>
    </div>

    <!-- Upload area -->
    <div
      class="border-2 border-dashed border-border rounded-lg p-6 text-center cursor-pointer hover:border-primary/50 hover:bg-accent/50 transition-colors"
      @dragover.prevent
      @drop.prevent="handleDrop"
      @click="triggerFileInput"
    >
      <Upload class="h-8 w-8 mx-auto text-muted-foreground mb-2" />
      <p class="text-sm text-muted-foreground">拖拽文件到此处或点击上传</p>
      <p class="text-[11px] text-muted-foreground/70 mt-1">支持 PDF、Word、TXT 等格式</p>
      <input ref="fileInputRef" type="file" class="hidden" multiple accept=".pdf,.doc,.docx,.txt,.md" @change="handleFileSelect" />
    </div>

    <!-- Upload progress -->
    <div v-if="uploading" class="flex items-center gap-2 px-3 py-2 bg-muted rounded-lg">
      <Loader2 class="h-4 w-4 animate-spin text-primary" />
      <span class="text-sm text-muted-foreground">上传中...</span>
    </div>

    <!-- Task progress indicator -->
    <div v-if="isProcessing && uploadProgress" class="mt-3 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
      <div class="flex items-center gap-2">
        <Loader2 class="h-4 w-4 animate-spin text-blue-500" />
        <span class="text-sm text-blue-700 dark:text-blue-300">
          {{ phaseLabels[uploadProgress.phase] || uploadProgress.phase }}
          <span v-if="uploadProgress.source"> — {{ uploadProgress.source }}</span>
        </span>
      </div>
      <div v-if="uploadProgress.status === 'completed'" class="mt-1 text-sm text-green-600">
        完成，{{ uploadProgress.chunks }} 个文本块
      </div>
      <div v-if="uploadProgress.status === 'failed'" class="mt-1 text-sm text-red-600">
        失败：{{ uploadProgress.error }}
      </div>
    </div>

    <!-- Action buttons -->
    <div class="flex gap-2">
      <button
        class="flex-1 h-8 rounded-md bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-1.5"
        :disabled="loading"
        @click="handleLoadLocal"
      >
        <FolderOpen class="h-3.5 w-3.5" />
        加载本地
      </button>
      <button
        class="flex-1 h-8 rounded-md border border-input bg-background text-foreground text-sm font-medium hover:bg-accent transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-1.5"
        :disabled="loading"
        @click="handleSync"
      >
        <RefreshCw class="h-3.5 w-3.5" />
        增量同步
      </button>
      <button
        class="h-8 w-8 flex items-center justify-center rounded-md border border-destructive/30 text-destructive hover:bg-destructive/10 transition-colors disabled:opacity-40"
        :disabled="loading || !docStore.hasDocuments"
        @click="handleClearAll"
        title="清空全部"
      >
        <Trash2 class="h-3.5 w-3.5" />
      </button>
    </div>

    <!-- Loading status -->
    <div v-if="loadStatus" class="px-3 py-2 bg-muted rounded-lg text-sm text-muted-foreground">
      {{ loadStatus }}
    </div>

    <!-- Separator -->
    <div class="h-px w-full shrink-0 bg-border" />

    <!-- Document list -->
    <div class="flex-1 min-h-0 overflow-y-auto">
      <div class="flex items-center justify-between mb-2">
        <span class="text-xs font-medium text-muted-foreground uppercase tracking-wider">已索引文档</span>
        <button class="text-[11px] text-muted-foreground hover:text-foreground transition-colors" @click="docStore.fetchOverview()">
          刷新
        </button>
      </div>

      <div v-if="!docStore.documents.length" class="text-center py-8 text-sm text-muted-foreground">
        暂无文档
      </div>

      <div v-else class="flex flex-col gap-1">
        <div
          v-for="doc in docStore.documents"
          :key="doc"
          class="group flex items-center gap-2 px-2 py-1.5 rounded-md hover:bg-accent transition-colors"
        >
          <FileText class="h-3.5 w-3.5 text-muted-foreground flex-shrink-0" />
          <span class="flex-1 text-[13px] text-foreground truncate min-w-0">{{ cleanName(doc) }}</span>
          <button
            class="flex-shrink-0 h-5 w-5 flex items-center justify-center rounded opacity-0 group-hover:opacity-100 hover:bg-destructive/10 hover:text-destructive transition-all"
            @click="handleDeleteDoc(doc)"
          >
            <X class="h-3 w-3" />
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Upload, FolderOpen, RefreshCw, Trash2, FileText, X, Loader2 } from 'lucide-vue-next'
import { useDocumentStore } from '../../stores/useDocumentStore.js'

const docStore = useDocumentStore()
const fileInputRef = ref(null)
const uploading = ref(false)
const loading = ref(false)
const loadStatus = ref('')
const uploadProgress = ref(null)  // {status, phase, source, chunks}
const isProcessing = ref(false)

const phaseLabels = {
  queued: '排队中',
  parsing: '解析中',
  chunking: '分块中',
  embedding: '向量化中',
  indexing: '索引中',
  done: '完成',
}

function cleanName(name) {
  if (!name) return ''
  return name.replace(/\.[^.]+$/, '')
}

function triggerFileInput() {
  fileInputRef.value?.click()
}

async function handleFileSelect(e) {
  const files = e.target.files
  if (!files?.length) return
  await uploadFiles(Array.from(files))
}

async function handleDrop(e) {
  const files = e.dataTransfer?.files
  if (!files?.length) return
  await uploadFiles(Array.from(files))
}

async function uploadFiles(files) {
  uploading.value = true
  isProcessing.value = true
  uploadProgress.value = { status: 'pending', phase: 'queued' }
  try {
    if (files.length === 1) {
      const result = await docStore.uploadFile(files[0])
      if (result.task_id) {
        await pollTaskForUI(result.task_id)
      }
    } else {
      const result = await docStore.uploadBatch(files)
      if (result.batch_id) {
        await pollBatchForUI(result.batch_id)
      }
    }
  } catch (err) {
    console.error('上传失败:', err)
  } finally {
    uploading.value = false
    isProcessing.value = false
    uploadProgress.value = null
    if (fileInputRef.value) fileInputRef.value.value = ''
  }
}

async function pollTaskForUI(taskId) {
  const { getTaskStatus } = await import('../../api/documents.js')
  while (true) {
    try {
      const state = await getTaskStatus(taskId)
      uploadProgress.value = state
      if (state.status === 'completed' || state.status === 'failed') {
        break
      }
      await new Promise(r => setTimeout(r, 800))
    } catch {
      break
    }
  }
  docStore.fetchOverview()
}

async function pollBatchForUI(batchId) {
  const { getBatchStatus } = await import('../../api/documents.js')
  while (true) {
    try {
      const state = await getBatchStatus(batchId)
      uploadProgress.value = state
      if (state.status === 'completed' || state.status === 'failed') {
        break
      }
      await new Promise(r => setTimeout(r, 1500))
    } catch {
      break
    }
  }
  docStore.fetchOverview()
}

async function handleLoadLocal() {
  loading.value = true
  loadStatus.value = '正在加载本地文档...'
  try {
    await docStore.loadAllDocuments((status) => {
      loadStatus.value = `已加载 ${status.loaded || 0} 个文件...`
    })
    loadStatus.value = '加载完成'
  } catch (err) {
    loadStatus.value = `加载失败: ${err.message}`
  } finally {
    loading.value = false
    setTimeout(() => { loadStatus.value = '' }, 3000)
  }
}

async function handleSync() {
  loading.value = true
  loadStatus.value = '正在同步...'
  try {
    const result = await docStore.syncDocuments()
    loadStatus.value = `同步完成: 新增 ${result?.added || 0}, 删除 ${result?.removed || 0}`
  } catch (err) {
    loadStatus.value = `同步失败: ${err.message}`
  } finally {
    loading.value = false
    setTimeout(() => { loadStatus.value = '' }, 3000)
  }
}

async function handleDeleteDoc(source) {
  if (!confirm(`删除文档「${cleanName(source)}」？`)) return
  await docStore.removeDocument(source)
}

async function handleClearAll() {
  if (!confirm('清空全部文档？')) return
  await docStore.removeAllDocuments()
}

onMounted(async () => {
  await docStore.fetchOverview()
})
</script>
