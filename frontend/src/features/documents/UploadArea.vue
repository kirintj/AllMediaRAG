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
          <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12" stroke="hsl(var(--nb-brand))" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
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
import { ref, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { uploadDocument, uploadBatch } from '../../api/documents.js'
import BatchUploadProgress from './BatchUploadProgress.vue'

const emit = defineEmits(['uploaded'])

const status = ref('')
const statusType = ref('') // 'uploading' | 'success' | 'error' | ''
const uploadCount = ref({ done: 0, total: 0, success: 0, fail: 0 })
const batchTaskId = ref(null)
const batchTotal = ref(0)
const pendingFiles = ref([])
let batchTimer = null
let statusTimer = null
const isUploading = ref(false)

function handleChange(file) {
  if (isUploading.value) {
    ElMessage.warning('有文件正在上传中，请稍后再试')
    return
  }

  pendingFiles.value.push(file)

  // Clear any previous timer and set a new one to batch file selections
  if (batchTimer) clearTimeout(batchTimer)

  batchTimer = setTimeout(async () => {
    const filesToUpload = [...pendingFiles.value]
    pendingFiles.value = []
    batchTimer = null

    if (filesToUpload.length === 0) return

    if (filesToUpload.length >= 20) {
      await handleBatchUpload(filesToUpload)
    } else {
      await handleMultipleSingleUploads(filesToUpload)
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

async function handleMultipleSingleUploads(files) {
  const total = files.length
  uploadCount.value = { done: 0, total, success: 0, fail: 0 }
  isUploading.value = true

  try {
    for (let i = 0; i < files.length; i++) {
      statusType.value = 'uploading'
      status.value = `正在上传 (${i + 1}/${total})...`

      try {
        const result = await uploadDocument(files[i].raw)
        if (result.error) {
          uploadCount.value.fail++
          statusType.value = 'error'
          status.value = `「${files[i].name}」: ${result.error}`
        } else {
          uploadCount.value.success++
        }
      } catch (error) {
        uploadCount.value.fail++
        statusType.value = 'error'
        status.value = `「${files[i].name}」上传失败: ${error.message}`
      }

      uploadCount.value.done++
    }

    // Final status after all files processed
    if (uploadCount.value.fail === 0) {
      statusType.value = 'success'
      status.value = `上传成功 · ${uploadCount.value.success} 个文件`
    } else {
      statusType.value = 'error'
      status.value = `上传完成 · ${uploadCount.value.success} 个成功 / ${uploadCount.value.fail} 个失败`
    }

    emit('uploaded')

    statusTimer = setTimeout(() => {
      statusType.value = ''
      status.value = ''
      uploadCount.value = { done: 0, total: 0, success: 0, fail: 0 }
    }, 3000)
  } finally {
    isUploading.value = false
  }
}

function handleBatchComplete({ success, failed }) {
  ElMessage.success(`批量索引完成，成功 ${success} 个`)
  batchTaskId.value = null
  emit('uploaded')
}

onUnmounted(() => {
  if (batchTimer) clearTimeout(batchTimer)
  if (statusTimer) clearTimeout(statusTimer)
})
</script>

<style scoped>
.upload-area {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.upload-area :deep(.el-upload) {
  width: 100%;
}

.upload-area :deep(.el-upload-dragger) {
  width: 100%;
  padding: 3rem;
  border: 2px dashed hsl(var(--border));
  border-radius: var(--radius);
  background: transparent;
  transition: border-color 0.2s ease, background 0.2s ease;
}

.upload-area :deep(.el-upload-dragger:hover) {
  border-color: hsl(var(--nb-brand));
  background: hsl(var(--nb-brand) / 0.1);
}

.upload-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

.upload-text {
  font-size: var(--nb-font-base);
  font-weight: 500;
  color: hsl(var(--foreground));
}

.upload-hint {
  font-size: var(--nb-font-sm);
  color: hsl(var(--muted-foreground) / 0.7);
}

/* ── 状态消息 ── */
.status-msg {
  font-size: var(--nb-font-sm);
  color: hsl(var(--muted-foreground));
  text-align: center;
  padding: 0.75rem 0;
  transition: color 0.3s ease;
}

.status-msg.uploading {
  color: hsl(var(--nb-brand));
  animation: status-pulse 1.4s ease-in-out infinite;
}

.status-msg.success {
  color: hsl(var(--nb-success));
}

.status-msg.error {
  color: hsl(var(--nb-danger));
}

@keyframes status-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
</style>
