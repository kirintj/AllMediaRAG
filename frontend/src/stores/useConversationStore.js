import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  getConversations,
  getConversation,
  deleteConversation,
  clearAllConversations,
  renameConversation,
  toggleFavorite,
  duplicateConversation,
  archiveConversation,
  shareConversation,
} from '../api/conversations.js'
import { useChatStore } from './useChatStore.js'
import { useToastStore } from './useToastStore.js'

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

  // 重命名对话
  async function renameConv(convId, newTitle) {
    const toastStore = useToastStore()
    try {
      await renameConversation(convId, newTitle)
      const conv = conversations.value.find(c => c.id === convId)
      if (conv) conv.title = newTitle
      toastStore.success('重命名成功')
    } catch (error) {
      console.error('重命名失败:', error)
      toastStore.error('重命名失败')
    }
  }

  // 收藏/取消收藏
  async function toggleFav(convId) {
    try {
      const conv = conversations.value.find(c => c.id === convId)
      if (!conv) return
      const newValue = !conv.is_favorite
      await toggleFavorite(convId, newValue)
      conv.is_favorite = newValue
    } catch (error) {
      console.error('收藏操作失败:', error)
    }
  }

  // 复制对话
  async function duplicateConv(convId) {
    const toastStore = useToastStore()
    try {
      await duplicateConversation(convId)
      await fetchConversations()
      toastStore.success('对话已复制')
    } catch (error) {
      console.error('复制对话失败:', error)
      toastStore.error('复制失败')
    }
  }

  // 归档对话
  async function archiveConv(convId) {
    const toastStore = useToastStore()
    try {
      await archiveConversation(convId)
      const chatStore = useChatStore()
      if (chatStore.activeConversationId === convId) {
        chatStore.messages = []
        chatStore.activeConversationId = null
      }
      await fetchConversations()
      toastStore.success('对话已归档')
    } catch (error) {
      console.error('归档失败:', error)
      toastStore.error('归档失败')
    }
  }

  // 分享对话
  async function shareConv(convId) {
    const toastStore = useToastStore()
    try {
      const data = await shareConversation(convId)
      if (data.share_url) {
        await navigator.clipboard.writeText(data.share_url)
        toastStore.success('分享链接已复制到剪贴板')
      }
    } catch (error) {
      console.error('分享失败:', error)
      toastStore.error('分享失败')
    }
  }

  return {
    conversations,
    fetchConversations,
    loadConversation,
    removeConversation,
    removeAllConversations,
    renameConv,
    toggleFav,
    duplicateConv,
    archiveConv,
    shareConv,
  }
})
