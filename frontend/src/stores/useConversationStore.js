import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  getConversations,
  getConversation,
  deleteConversation,
  clearAllConversations,
} from '../api/conversations.js'
import { useChatStore } from './useChatStore.js'

export const useConversationStore = defineStore('conversation', () => {
  // 状态
  const conversations = ref([])

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
      const chatStore = useChatStore()
      chatStore.messages = data.messages || []
      chatStore.activeConversationId = data.id
      chatStore.mode = data.mode || 'rag'
    } catch (error) {
      console.error('加载对话失败:', error)
    }
  }

  // 删除对话
  async function removeConversation(convId) {
    try {
      await deleteConversation(convId)
      const chatStore = useChatStore()
      if (chatStore.activeConversationId === convId) {
        chatStore.messages = []
        chatStore.activeConversationId = null
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
      const chatStore = useChatStore()
      chatStore.messages = []
      chatStore.activeConversationId = null
      conversations.value = []
      return data
    } catch (error) {
      console.error('清空对话失败:', error)
      throw error
    }
  }

  return {
    conversations,
    fetchConversations,
    loadConversation,
    removeConversation,
    removeAllConversations,
  }
})
