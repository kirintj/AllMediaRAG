<template>
  <div class="flex flex-col gap-1 py-2">
    <!-- Header -->
    <div class="flex items-center justify-between px-2 mb-1">
      <span class="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">历史对话</span>
      <button
        v-if="conversationStore.conversations.length > 0"
        class="text-[11px] text-muted-foreground hover:text-destructive transition-colors px-1.5 py-0.5 rounded hover:bg-destructive/10"
        @click="handleClearAll"
      >
        清空
      </button>
    </div>

    <!-- Empty state -->
    <div v-if="conversationStore.conversations.length === 0" class="flex flex-col items-center justify-center py-10 px-4 text-center">
      <div class="w-10 h-10 rounded-xl bg-muted flex items-center justify-center mb-3">
        <MessageSquare class="h-5 w-5 text-muted-foreground" />
      </div>
      <p class="text-sm text-muted-foreground">暂无历史对话</p>
      <p class="text-[11px] text-muted-foreground/70 mt-0.5">发送消息开始新对话</p>
    </div>

    <!-- Conversation items -->
    <div v-else class="flex flex-col gap-0.5">
      <div
        v-for="conv in conversationStore.conversations"
        :key="conv.id"
        class="group flex items-center gap-2 px-2 py-1.5 rounded-md cursor-pointer text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground transition-colors"
        :class="{ 'bg-sidebar-accent text-sidebar-accent-foreground': chatStore.activeConversationId === conv.id }"
        @click="conversationStore.loadConversation(conv.id)"
      >
        <MessageSquare class="h-3.5 w-3.5 flex-shrink-0" />
        <span class="flex-1 text-[13px] font-medium truncate min-w-0">{{ conv.title }}</span>
        <span class="text-[11px] text-muted-foreground flex-shrink-0">{{ conv.message_count }}条</span>
        <button
          class="flex-shrink-0 h-5 w-5 flex items-center justify-center rounded opacity-0 group-hover:opacity-100 hover:bg-destructive/10 hover:text-destructive transition-all"
          @click.stop="handleDelete(conv)"
        >
          <X class="h-3 w-3" />
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { MessageSquare, X } from 'lucide-vue-next'
import { useChatStore } from '../../stores/useChatStore.js'
import { useConversationStore } from '../../stores/useConversationStore.js'

const chatStore = useChatStore()
const conversationStore = useConversationStore()

async function handleDelete(conv) {
  if (!confirm(`删除「${conv.title}」？`)) return
  await conversationStore.removeConversation(conv.id)
}

async function handleClearAll() {
  const count = conversationStore.conversations.length
  if (!confirm(`清空全部 ${count} 条对话？`)) return
  await conversationStore.removeAllConversations()
}

onMounted(() => {
  conversationStore.fetchConversations()
})
</script>
