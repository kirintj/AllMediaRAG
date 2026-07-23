import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  getOverview,
  loadDocuments,
  getLoadStatus,
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
    return uploadDocument(file)
  }

  // 批量上传
  async function uploadBatch(files) {
    const { uploadBatch: apiUploadBatch } = await import('../api/documents.js')
    return apiUploadBatch(files)
  }

  // 批量加载文档（后台任务 + 轮询进度）
  async function loadAllDocuments(onProgress) {
    try {
      await loadDocuments()  // 启动后台任务，立即返回

      // 轮询进度
      while (true) {
        await new Promise(r => setTimeout(r, 1000))
        const status = await getLoadStatus()

        if (onProgress) onProgress(status)

        if (status.status === 'done') {
          await fetchOverview()
          return status.result
        }
        if (status.status === 'error') {
          throw new Error(status.error || '文档加载失败')
        }
      }
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
