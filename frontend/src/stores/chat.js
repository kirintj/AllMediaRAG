import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { chatStream, getDocuments, loadDocuments, getLoadStatus, getStats, deleteDocument, clearAllDocuments, syncDocuments as syncDocumentsApi, getConversations, getConversation, deleteConversation, clearAllConversations } from '../api'

export const useChatStore = defineStore('chat', () => {
  // 状态
  const messages = ref([])
  const mode = ref('rag')
  const loading = ref(false)
  const documents = ref([])
  const stats = ref({ document_count: 0, source_count: 0 })
  const conversations = ref([])
  const activeConversationId = ref(null)

  // 计算属性
  const hasDocuments = computed(() => documents.value.length > 0)

  // 提取最近对话上下文（最多 10 轮 = 20 条消息）
  function getRecentHistory() {
    const MAX_HISTORY = 20
    return messages.value
      .filter(m => m.role === 'user' || m.role === 'assistant')
      .slice(-MAX_HISTORY)
      .map(m => ({ role: m.role, content: m.content }))
  }

  // 发送消息
  async function sendMessage(content) {
    if (!content.trim() || loading.value) return

    // 添加用户消息
    messages.value.push({
      role: 'user',
      content: content
    })

    // 添加助手消息占位
    const assistantIndex = messages.value.length
    messages.value.push({
      role: 'assistant',
      content: '',
      sources: [],
      loading: true
    })

    loading.value = true
    const startTime = Date.now()

    // 提取最近上下文
    const history = getRecentHistory()

    try {
      await chatStream(content, mode.value, (data) => {
        const elapsed = Date.now() - startTime
        // 检查错误
        if (data.error) {
          messages.value.splice(assistantIndex, 1, {
            role: 'assistant',
            content: `错误: ${data.error}`,
            sources: [],
            loading: false,
            elapsed
          })
          return
        }
        // 保存后端返回的 conversation_id
        if (data.conversation_id) {
          activeConversationId.value = data.conversation_id
        }
        // 创建新对象触发响应式
        const newMsg = {
          role: 'assistant',
          content: data.full_answer || '',
          sources: data.sources && data.sources.length > 0 ? data.sources : [],
          verification: data.verification || null,
          loading: false,
          elapsed: Date.now() - startTime
        }
        // 使用 splice 确保响应式更新
        messages.value.splice(assistantIndex, 1, newMsg)
      }, activeConversationId.value, history)
    } catch (error) {
      const elapsed = Date.now() - startTime
      messages.value.splice(assistantIndex, 1, {
        role: 'assistant',
        content: `错误: ${error.message}`,
        sources: [],
        loading: false,
        elapsed
      })
    } finally {
      loading.value = false
      // 刷新对话列表
      fetchConversations()
    }
  }

  // 清空当前对话（纯前端操作）
  function clearChatHistory() {
    messages.value = []
    activeConversationId.value = null
  }

  // 加载文档列表
  async function fetchDocuments() {
    try {
      const data = await getDocuments()
      documents.value = data.documents || []
    } catch (error) {
      console.error('获取文档列表失败:', error)
    }
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

  // 获取统计信息
  async function fetchStats() {
    try {
      const data = await getStats()
      stats.value = data
    } catch (error) {
      console.error('获取统计失败:', error)
    }
  }

  // 删除单个文档
  async function removeDocument(source) {
    try {
      const data = await deleteDocument(source)
      await fetchDocuments()
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
      await fetchStats()
      return data
    } catch (error) {
      console.error('清空文档失败:', error)
      throw error
    }
  }

  // 获取对话列表
  async function fetchConversations() {
    try {
      const data = await getConversations()
      conversations.value = data.conversations || []
    } catch (error) {
      console.error('获取对话列表失败:', error)
    }
  }

  // 加载对话
  async function loadConversation(convId) {
    try {
      const data = await getConversation(convId)
      if (data.error) return
      messages.value = data.messages || []
      activeConversationId.value = data.id
      mode.value = data.mode || 'rag'
    } catch (error) {
      console.error('加载对话失败:', error)
    }
  }

  // 删除对话
  async function removeConversation(convId) {
    try {
      await deleteConversation(convId)
      if (activeConversationId.value === convId) {
        messages.value = []
        activeConversationId.value = null
      }
      await fetchConversations()
    } catch (error) {
      console.error('删除对话失败:', error)
    }
  }

  // 清空所有对话
  async function removeAllConversations() {
    try {
      const data = await clearAllConversations()
      messages.value = []
      activeConversationId.value = null
      conversations.value = []
      return data
    } catch (error) {
      console.error('清空对话失败:', error)
      throw error
    }
  }

  return {
    messages,
    mode,
    loading,
    documents,
    stats,
    hasDocuments,
    conversations,
    activeConversationId,
    sendMessage,
    clearChatHistory,
    fetchDocuments,
    loadAllDocuments,
    syncDocuments,
    fetchStats,
    removeDocument,
    removeAllDocuments,
    fetchConversations,
    loadConversation,
    removeConversation,
    removeAllConversations,
  }
})
