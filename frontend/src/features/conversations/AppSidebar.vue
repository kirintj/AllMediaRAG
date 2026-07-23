<template>
  <div class="flex flex-col h-full p-3 gap-3" :class="{ 'items-center': collapsed }">
    <!-- Header: logo + collapse toggle -->
    <div
      class="flex items-center w-full"
      :class="collapsed ? 'justify-center' : 'justify-between px-1'"
    >
      <div
        class="flex items-center gap-2.5 min-w-0"
        :class="{ 'cursor-pointer': collapsed }"
        @click="collapsed && $emit('toggle-collapse')"
      >
        <div class="flex-shrink-0 w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
          <Sparkles class="h-4 w-4 text-primary-foreground" />
        </div>
        <div v-if="!collapsed" class="min-w-0">
          <h2 class="text-sm font-semibold text-foreground leading-tight truncate">知识库助手</h2>
          <span class="text-[11px] text-muted-foreground">RAG 智能问答</span>
        </div>
      </div>
      <button
        v-if="!collapsed"
        class="h-7 w-7 flex items-center justify-center rounded-md hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
        @click="$emit('toggle-collapse')"
      >
        <PanelLeftClose class="h-4 w-4" />
      </button>
    </div>

    <!-- New chat button -->
    <button
      class="flex items-center justify-center gap-2 h-8 rounded-full bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors"
      :class="collapsed ? 'w-8' : 'w-full px-3'"
      @click="newChat"
    >
      <Plus class="h-4 w-4 flex-shrink-0" />
      <span v-if="!collapsed">新对话</span>
    </button>

    <!-- Conversation list -->
    <div class="flex-1 overflow-y-auto min-h-0 w-full">
      <ConversationList v-if="!collapsed" />
    </div>

    <!-- Bottom actions -->
    <div class="flex flex-col gap-1 pt-2 border-t border-sidebar-border w-full">
      <button
        v-for="action in bottomActions"
        :key="action.label"
        class="flex items-center gap-2.5 h-8 rounded-md text-sm text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground transition-colors"
        :class="collapsed ? 'justify-center' : 'px-2'"
        @click="action.handler"
        :title="collapsed ? action.label : undefined"
      >
        <component :is="action.icon" class="h-4 w-4 flex-shrink-0" />
        <span v-if="!collapsed">{{ action.label }}</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { Plus, PanelLeftClose, Sparkles, FileText, BarChart3, Cpu, LogOut } from 'lucide-vue-next'
import { useChatStore } from '../../stores/useChatStore.js'
import ConversationList from './ConversationList.vue'

defineProps({
  collapsed: { type: Boolean, default: false },
})

const emit = defineEmits(['toggle-collapse', 'open-docs', 'open-eval', 'open-models', 'logout'])
const chatStore = useChatStore()

function newChat() {
  chatStore.clearChatHistory()
}

const bottomActions = [
  { label: '文档管理', icon: FileText, handler: () => emit('open-docs') },
  { label: '模型管理', icon: Cpu, handler: () => emit('open-models') },
  { label: '评测看板', icon: BarChart3, handler: () => emit('open-eval') },
  { label: '退出登录', icon: LogOut, handler: () => emit('logout') },
]
</script>
