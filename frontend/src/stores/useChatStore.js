import { defineStore } from 'pinia'
import { ref } from 'vue'
import { chatStream } from '../api/chat.js'
import { useConversationStore } from './useConversationStore.js'

export const useChatStore = defineStore('chat', () => {
  // 状态
  const messages = ref([])
  const mode = ref('rag')
  const loading = ref(false)
  const activeConversationId = ref(null)

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
        console.log('SSE done data:', data)
        const newMsg = {
          role: 'assistant',
          content: data.full_answer || '',
          sources: data.sources && data.sources.length > 0 ? data.sources : [],
          verification: data.verification || null,
          loading: false,
          elapsed: Date.now() - startTime
        }
        console.log('New message:', newMsg)
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
      const conversationStore = useConversationStore()
      conversationStore.fetchConversations()
    }
  }

  // 清空当前对话（纯前端操作）
  function clearChatHistory() {
    messages.value = []
    activeConversationId.value = null
  }

  return {
    messages,
    mode,
    loading,
    activeConversationId,
    getRecentHistory,
    sendMessage,
    clearChatHistory,
  }
})
