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
    <div v-if="filteredConversations.length === 0" class="flex flex-col items-center justify-center py-10 px-4 text-center">
      <div class="w-10 h-10 rounded-xl bg-muted flex items-center justify-center mb-3">
        <MessageSquare class="h-5 w-5 text-muted-foreground" />
      </div>
      <p class="text-sm text-muted-foreground">{{ filter ? '无匹配对话' : '暂无历史对话' }}</p>
      <p class="text-[11px] text-muted-foreground/70 mt-0.5">{{ filter ? '尝试其他关键词' : '发送消息开始新对话' }}</p>
    </div>

    <!-- Conversation items -->
    <div v-else class="flex flex-col gap-0.5">
      <ContextMenu v-for="conv in filteredConversations" :key="conv.id">
        <ContextMenuTrigger>
          <div
            class="group flex items-center gap-2 px-2 py-1.5 rounded-md cursor-pointer text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground transition-colors w-full text-left"
            :class="{ 'bg-sidebar-accent text-sidebar-accent-foreground': chatStore.activeConversationId === conv.id }"
            @click="handleClick(conv)"
          >
            <MessageSquare class="h-3.5 w-3.5 flex-shrink-0" />
            <!-- Normal display -->
            <span v-if="renamingId !== conv.id" class="flex-1 text-[13px] font-medium truncate min-w-0">
              {{ conv.title }}
            </span>
            <!-- Inline rename input -->
            <input
              v-else
              ref="renameInput"
              v-model="renameValue"
              class="flex-1 text-[13px] font-medium bg-transparent border border-ring rounded px-1 py-0.5 outline-none min-w-0"
              @keydown.enter="confirmRename(conv)"
              @keydown.escape="cancelRename"
              @blur="confirmRename(conv)"
              @click.stop
            />
            <Star v-if="conv.is_favorite" class="h-3 w-3 text-yellow-500 flex-shrink-0" />
            <span class="text-[11px] text-muted-foreground flex-shrink-0">{{ conv.message_count }}条</span>
            <button
              class="flex-shrink-0 h-5 w-5 flex items-center justify-center rounded opacity-0 group-hover:opacity-100 hover:bg-destructive/10 hover:text-destructive transition-all"
              @click.stop="handleDelete(conv)"
            >
              <X class="h-3 w-3" />
            </button>
          </div>
        </ContextMenuTrigger>

        <ContextMenuContent>
          <ContextMenuItem @select="startRename(conv)">
            <Pencil class="h-4 w-4" />
            <span>重命名</span>
          </ContextMenuItem>
          <ContextMenuItem @select="conversationStore.toggleFav(conv.id)">
            <Star class="h-4 w-4" />
            <span>{{ conv.is_favorite ? '取消收藏' : '收藏' }}</span>
          </ContextMenuItem>
          <ContextMenuItem @select="conversationStore.duplicateConv(conv.id)">
            <Copy class="h-4 w-4" />
            <span>复制</span>
          </ContextMenuItem>
          <ContextMenuItem @select="conversationStore.archiveConv(conv.id)">
            <Archive class="h-4 w-4" />
            <span>归档</span>
          </ContextMenuItem>
          <ContextMenuItem @select="conversationStore.shareConv(conv.id)">
            <Share2 class="h-4 w-4" />
            <span>分享</span>
          </ContextMenuItem>
          <ContextMenuSeparator />
          <ContextMenuItem destructive @select="handleDelete(conv)">
            <Trash2 class="h-4 w-4" />
            <span>删除</span>
          </ContextMenuItem>
        </ContextMenuContent>
      </ContextMenu>
    </div>

    <!-- Mobile detail sheet -->
    <MobileDetailSheet
      v-model="showMobileDetail"
      :conversation="selectedConv"
    />
  </div>
</template>

<script setup>
import { ref, nextTick, computed, onMounted } from 'vue'
import { MessageSquare, X, Pencil, Star, Copy, Archive, Share2, Trash2 } from 'lucide-vue-next'
import { useChatStore } from '../../stores/useChatStore.js'
import { useConversationStore } from '../../stores/useConversationStore.js'
import ContextMenu from '../../components/ui/context-menu.vue'
import ContextMenuTrigger from '../../components/ui/context-menu-trigger.vue'
import ContextMenuContent from '../../components/ui/context-menu-content.vue'
import ContextMenuItem from '../../components/ui/context-menu-item.vue'
import ContextMenuSeparator from '../../components/ui/context-menu-separator.vue'
import MobileDetailSheet from './MobileDetailSheet.vue'

const props = defineProps({
  filter: { type: String, default: '' },
})

const chatStore = useChatStore()
const conversationStore = useConversationStore()

// Inline rename state
const renamingId = ref(null)
const renameValue = ref('')
const renameInput = ref(null)

// Mobile detail sheet state
const showMobileDetail = ref(false)
const selectedConv = ref(null)

const filteredConversations = computed(() => {
  if (!props.filter) return conversationStore.conversations
  const q = props.filter.toLowerCase()
  return conversationStore.conversations.filter(c =>
    c.title?.toLowerCase().includes(q)
  )
})

function handleClick(conv) {
  if (renamingId.value === conv.id) return
  // On mobile (<768px), open detail sheet instead of loading directly
  if (window.innerWidth < 768) {
    selectedConv.value = conv
    showMobileDetail.value = true
    return
  }
  conversationStore.loadConversation(conv.id)
}

function startRename(conv) {
  renamingId.value = conv.id
  renameValue.value = conv.title || ''
  nextTick(() => renameInput.value?.[0]?.focus())
}

function cancelRename() {
  renamingId.value = null
  renameValue.value = ''
}

async function confirmRename(conv) {
  const newTitle = renameValue.value.trim()
  if (newTitle && newTitle !== conv.title) {
    await conversationStore.renameConv(conv.id, newTitle)
  }
  cancelRename()
}

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
