import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  getOverview,
  loadDocuments,
  deleteDocument,
  clearAllDocuments,
  syncDocuments as syncDocumentsApi,
} from '../api/documents.js'

export const useDocumentStore = defineStore('document', () => {
  // 状态
  const documents = ref([])
  const documentDetails = ref([])
  const stats = ref({ document_count: 0, source_count: 0 })

  // 计算属性
  const hasDocuments = computed(() => documents.value.length > 0)

  // 一次请求加载列表 + 详情 + 统计（替代多次串行请求）
  async function fetchOverview() {
    try {
      const data = await getOverview()
      documents.value = data.documents || []
      documentDetails.value = data.details || []
      stats.value = data.stats || {}
    } catch (error) {
      console.error('获取文档概览失败:', error)
    }
  }

  // 上传单个文件
  async function uploadFile(file) {
    const { uploadDocument } = await import('../api/documents.js')
    const result = await uploadDocument(file)
    // result now has {message, filename, task_id}
    if (result.task_id) {
      await _pollTask(result.task_id)
    }
    await fetchOverview()
    return result
  }

  // 批量上传
  async function uploadBatch(files) {
    const { uploadBatch: apiUploadBatch } = await import('../api/documents.js')
    const result = await apiUploadBatch(files)
    // result now has {message, batch_id, task_ids}
    if (result.batch_id) {
      await _pollBatch(result.batch_id)
    }
    await fetchOverview()
    return result
  }

  // 轮询单个任务状态
  async function _pollTask(taskId, maxWait = 120000) {
    const { getTaskStatus } = await import('../api/documents.js')
    const start = Date.now()
    while (Date.now() - start < maxWait) {
      const state = await getTaskStatus(taskId)
      if (state.status === 'completed' || state.status === 'failed') {
        return state
      }
      await new Promise(r => setTimeout(r, 1000))
    }
    return null
  }

  // 轮询批次状态
  async function _pollBatch(batchId, maxWait = 300000) {
    const { getBatchStatus } = await import('../api/documents.js')
    const start = Date.now()
    while (Date.now() - start < maxWait) {
      const state = await getBatchStatus(batchId)
      if (state.status === 'completed') {
        return state
      }
      await new Promise(r => setTimeout(r, 2000))
    }
    return null
  }

  // 批量加载文档（后台任务 + 轮询进度）
  async function loadAllDocuments(onProgress) {
    try {
      const result = await loadDocuments()  // 启动后台任务，立即返回 {message, batch_id, total}

      if (result.batch_id) {
        // 轮询批次状态
        const finalState = await _pollBatch(result.batch_id)
        if (finalState && onProgress) {
          onProgress({ status: 'done', ...finalState })
        }
      }
      await fetchOverview()
    } catch (error) {
      console.error('加载文档失败:', error)
      throw error
    }
  }

  // 增量同步文档
  async function syncDocuments() {
    try {
      const data = await syncDocumentsApi()
      await fetchOverview()
      return data
    } catch (error) {
      console.error('同步文档失败:', error)
      throw error
    }
  }

  // 删除单个文档
  async function removeDocument(source) {
    try {
      const data = await deleteDocument(source)
      await fetchOverview()
      return data
    } catch (error) {
      console.error('删除文档失败:', error)
      throw error
    }
  }

  // 清空所有文档
  async function removeAllDocuments() {
    try {
      const data = await clearAllDocuments()
      await fetchOverview()
      return data
    } catch (error) {
      console.error('清空文档失败:', error)
      throw error
    }
  }

  return {
    documents,
    documentDetails,
    stats,
    hasDocuments,
    fetchOverview,
    uploadFile,
    uploadBatch,
    loadAllDocuments,
    syncDocuments,
    removeDocument,
    removeAllDocuments,
  }
})
