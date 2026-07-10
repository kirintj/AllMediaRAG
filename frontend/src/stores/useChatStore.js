/**
 * 聊天状态管理。
 *
 * 职责划分：
 * - api/chat.js — 负责 SSE 连接建立和流式数据解析
 * - 本 store — 仅负责响应式状态更新（消息追加/替换、loading 标记）
 */
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

  // 发送消息（SSE 解析由 api/chat.js 处理，此处只更新状态）
  async function sendMessage(content) {
    if (!content.trim() || loading.value) return

    // 在添加用户消息之前提取历史（避免当前消息被包含在历史中）
    const history = getRecentHistory()

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
        // 独立 verification 事件：仅更新 verification 字段
        if (data.verification && !data.done) {
          const current = messages.value[assistantIndex]
          if (current) {
            messages.value.splice(assistantIndex, 1, {
              ...current,
              verification: data.verification
            })
          }
          return
        }
        // 每个 chunk 都更新消息（实现流式输出效果）
        const newMsg = {
          role: 'assistant',
          content: data.full_answer || '',
          sources: data.sources && data.sources.length > 0 ? data.sources : [],
          verification: data.verification || null,
          loading: false,
          elapsed
        }
        // 使用 splice 确保响应式更新
        messages.value.splice(assistantIndex, 1, newMsg)
      }, activeConversationId.value, history)
    } catch (error) {
      const elapsed = Date.now() - startTime
      // 如果已有回答内容（超时但回答已流式接收），保留内容而非覆盖为错误
      const currentMsg = messages.value[assistantIndex]
      if (currentMsg && currentMsg.content && currentMsg.content.trim()) {
        messages.value.splice(assistantIndex, 1, {
          ...currentMsg,
          loading: false,
          elapsed
        })
      } else {
        messages.value.splice(assistantIndex, 1, {
          role: 'assistant',
          content: `错误: ${error.message}`,
          sources: [],
          loading: false,
          elapsed
        })
      }
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
