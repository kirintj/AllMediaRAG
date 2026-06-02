import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { chatStream, getDocuments, loadDocuments, getStats, clearHistory, deleteDocument, clearAllDocuments, getConversations, getConversation, deleteConversation } from '../api'

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
      sources: []
    })

    loading.value = true

    try {
      await chatStream(content, mode.value, (data) => {
        // 检查错误
        if (data.error) {
          messages.value.splice(assistantIndex, 1, {
            role: 'assistant',
            content: `错误: ${data.error}`,
            sources: []
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
          sources: data.sources && data.sources.length > 0 ? data.sources : []
        }
        // 使用 splice 确保响应式更新
        messages.value.splice(assistantIndex, 1, newMsg)
      }, activeConversationId.value)
    } catch (error) {
      messages.value.splice(assistantIndex, 1, {
        role: 'assistant',
        content: `错误: ${error.message}`,
        sources: []
      })
    } finally {
      loading.value = false
      // 刷新对话列表
      fetchConversations()
    }
  }

  // 清空对话
  function clearMessages() {
    messages.value = []
    activeConversationId.value = null
  }

  // 清空历史
  async function clearChatHistory() {
    try {
      await clearHistory()
      messages.value = []
      activeConversationId.value = null
    } catch (error) {
      console.error('清空历史失败:', error)
    }
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

  // 批量加载文档
  async function loadAllDocuments() {
    try {
      const data = await loadDocuments()
      await fetchDocuments()
      await fetchStats()
      return data
    } catch (error) {
      console.error('加载文档失败:', error)
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
    clearMessages,
    clearChatHistory,
    fetchDocuments,
    loadAllDocuments,
    fetchStats,
    removeDocument,
    removeAllDocuments,
    fetchConversations,
    loadConversation,
    removeConversation,
  }
})
