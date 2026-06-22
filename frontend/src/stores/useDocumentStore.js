import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  getDocuments,
  getDocumentDetails,
  loadDocuments,
  getLoadStatus,
  getStats,
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

  // 加载文档列表
  async function fetchDocuments() {
    try {
      const data = await getDocuments()
      documents.value = data.documents || []
    } catch (error) {
      console.error('获取文档列表失败:', error)
    }
  }

  // 加载文档详情
  async function fetchDocumentDetails() {
    try {
      const data = await getDocumentDetails()
      documentDetails.value = data.documents || []
    } catch (error) {
      console.error('获取文档详情失败:', error)
    }
  }

  // 获取统计信息
  async function fetchStats() {
    try {
      const data = await getStats()
      stats.value = data
    } catch (error) {
      console.error('获取统计失败:', error)
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
          await fetchDocuments()
          await fetchStats()
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
      await fetchDocuments()
      await fetchStats()
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
      await fetchDocuments()
      await fetchDocumentDetails()
      await fetchStats()
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
      await fetchDocuments()
      documentDetails.value = []
      await fetchStats()
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
    fetchDocuments,
    fetchDocumentDetails,
    fetchStats,
    uploadFile,
    uploadBatch,
    loadAllDocuments,
    syncDocuments,
    removeDocument,
    removeAllDocuments,
  }
})
