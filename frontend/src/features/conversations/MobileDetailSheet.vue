<template>
  <Sheet v-model="open" side="bottom" class="h-[60vh] p-0">
    <div class="flex flex-col h-full">
      <!-- Drag indicator -->
      <div class="flex justify-center py-3 flex-shrink-0">
        <div class="w-10 h-1 rounded-full bg-muted-foreground/30" />
      </div>

      <!-- Title (editable) -->
      <div class="px-5 pb-3 flex-shrink-0">
        <h3 class="text-lg font-semibold text-foreground">{{ conversation?.title || '对话详情' }}</h3>
      </div>

      <!-- Meta info -->
      <div class="px-5 pb-4 flex flex-col gap-2 flex-shrink-0">
        <div class="flex items-center gap-2 text-sm text-muted-foreground">
          <Calendar class="h-4 w-4" />
          <span>{{ formattedDate }}</span>
        </div>
        <div class="flex items-center gap-2 text-sm text-muted-foreground">
          <MessageSquare class="h-4 w-4" />
          <span>{{ conversation?.message_count || 0 }} 条消息</span>
        </div>
        <div v-if="conversation?.is_favorite" class="flex items-center gap-2 text-sm text-yellow-600">
          <Star class="h-4 w-4" />
          <span>已收藏</span>
        </div>
      </div>

      <!-- Actions grid -->
      <div class="flex-1 overflow-y-auto px-5">
        <div class="grid grid-cols-2 gap-2">
          <button
            v-for="action in actions"
            :key="action.label"
            class="flex items-center gap-2.5 px-3 py-3 rounded-lg border border-border hover:bg-accent transition-colors text-sm"
            :class="action.destructive ? 'text-destructive' : 'text-foreground'"
            @click="action.handler"
          >
            <component :is="action.icon" class="h-4 w-4 flex-shrink-0" />
            <span>{{ action.label }}</span>
          </button>
        </div>
      </div>

      <!-- Cancel button -->
      <div class="flex-shrink-0 px-5 py-4">
        <button
          class="w-full h-10 rounded-lg bg-muted text-muted-foreground text-sm font-medium hover:bg-accent transition-colors"
          @click="open = false"
        >
          取消
        </button>
      </div>
    </div>
  </Sheet>
</template>

<script setup>
import { computed } from 'vue'
import { Calendar, MessageSquare, Star, StarOff, Copy, Archive, Share2, Trash2 } from 'lucide-vue-next'
import Sheet from '../../components/ui/sheet.vue'
import { useConversationStore } from '../../stores/useConversationStore.js'
import { useConfirmStore } from '../../stores/useConfirmStore.js'

const props = defineProps({
  conversation: { type: Object, default: null },
})

const open = defineModel({ type: Boolean, default: false })

const conversationStore = useConversationStore()
const confirmStore = useConfirmStore()

const formattedDate = computed(() => {
  if (!props.conversation?.created_at) return ''
  const d = new Date(props.conversation.created_at * 1000)
  return d.toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric' })
})

const actions = computed(() => [
  {
    label: props.conversation?.is_favorite ? '取消收藏' : '收藏',
    icon: props.conversation?.is_favorite ? StarOff : Star,
    handler: async () => {
      await conversationStore.toggleFav(props.conversation.id)
    },
  },
  {
    label: '复制',
    icon: Copy,
    handler: async () => {
      await conversationStore.duplicateConv(props.conversation.id)
      open.value = false
    },
  },
  {
    label: '归档',
    icon: Archive,
    handler: async () => {
      await conversationStore.archiveConv(props.conversation.id)
      open.value = false
    },
  },
  {
    label: '分享',
    icon: Share2,
    handler: async () => {
      await conversationStore.shareConv(props.conversation.id)
      open.value = false
    },
  },
  {
    label: '删除',
    icon: Trash2,
    destructive: true,
    handler: async () => {
      if (await confirmStore.confirm({ message: `删除「${props.conversation.title}」？`, destructive: true })) {
        await conversationStore.removeConversation(props.conversation.id)
        open.value = false
      }
    },
  },
])
</script>
