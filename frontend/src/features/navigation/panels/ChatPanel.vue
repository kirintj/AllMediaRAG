<template>
  <div class="flex flex-col h-full">
    <!-- Header -->
    <div class="flex items-center justify-between pl-4 pr-10 lg:px-4 h-12 border-b border-border flex-shrink-0">
      <h3 class="text-sm font-semibold text-foreground">对话</h3>
      <div class="flex items-center gap-1.5 sm:gap-2">
        <button
          class="h-9 w-9 flex items-center justify-center rounded-md hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
          @click="toggleSearch"
          title="搜索对话"
        >
          <Search class="h-4 w-4" />
        </button>
        <button
          class="h-9 w-9 flex items-center justify-center rounded-md hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
          @click="newChat"
          title="新对话"
        >
          <Plus class="h-4 w-4" />
        </button>
      </div>
    </div>

    <!-- Search bar (collapsible) -->
    <div v-if="searchOpen" class="px-3 pt-2 pb-1 flex-shrink-0">
      <div class="relative">
        <Search class="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
        <input
          ref="searchInput"
          v-model="searchQuery"
          type="text"
          placeholder="搜索对话..."
          class="w-full h-9 pl-8 pr-3 text-base rounded-md bg-muted border-0 outline-none focus:ring-1 focus:ring-ring placeholder:text-muted-foreground"
          @keydown.escape="closeSearch"
        />
      </div>
    </div>

    <!-- Conversation list -->
    <div class="flex-1 overflow-y-auto min-h-0">
      <ConversationList :filter="searchQuery" />
    </div>

    <!-- Footer -->
    <div class="flex-shrink-0 border-t border-border px-3 py-2">
      <div class="flex items-center justify-between">
        <button
          class="flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground transition-colors min-h-[36px] px-1"
          @click="$emit('open-models')"
          title="模型管理"
        >
          <Cpu class="h-3.5 w-3.5" />
          <span class="truncate">模型管理</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'
import { Search, Plus, Cpu } from 'lucide-vue-next'
import { useChatStore } from '../../../stores/useChatStore.js'
import { useTheme } from '../../../composables/useTheme.ts'
import ConversationList from '../../conversations/ConversationList.vue'

defineEmits(['open-models'])

const chatStore = useChatStore()

const searchOpen = ref(false)
const searchQuery = ref('')
const searchInput = ref(null)

function toggleSearch() {
  searchOpen.value = !searchOpen.value
  if (searchOpen.value) {
    nextTick(() => searchInput.value?.focus())
  } else {
    searchQuery.value = ''
  }
}

function closeSearch() {
  searchOpen.value = false
  searchQuery.value = ''
}

function newChat() {
  chatStore.clearChatHistory()
}
</script>
