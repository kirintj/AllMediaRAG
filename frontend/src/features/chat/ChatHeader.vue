<template>
  <header class="flex items-center justify-between h-11 px-4 border-b border-border bg-background/80 backdrop-blur-sm flex-shrink-0">
    <div class="flex items-center gap-2 min-w-0">
      <button
        class="h-7 w-7 flex items-center justify-center rounded-md hover:bg-accent text-muted-foreground hover:text-foreground transition-colors lg:hidden"
        @click="toggleMobileSidebar"
      >
        <PanelLeft class="h-4 w-4" />
      </button>
      <h3 class="text-base font-semibold text-foreground truncate">对话</h3>
      <span v-if="chatStore.loading" class="flex items-center gap-0.5">
        <span class="w-1 h-1 rounded-full bg-primary animate-bounce" style="animation-delay: 0s" />
        <span class="w-1 h-1 rounded-full bg-primary animate-bounce" style="animation-delay: 0.15s" />
        <span class="w-1 h-1 rounded-full bg-primary animate-bounce" style="animation-delay: 0.3s" />
      </span>
    </div>

    <div class="flex items-center gap-0.5">
      <button
        class="h-7 w-7 flex items-center justify-center rounded-md hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
        @click="$emit('open-docs')"
        title="文档管理"
      >
        <FolderOpen class="h-4 w-4" />
      </button>
      <button
        class="h-7 w-7 flex items-center justify-center rounded-md hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
        @click="$emit('open-eval')"
        title="评测看板"
      >
        <BarChart3 class="h-4 w-4" />
      </button>
      <button
        class="h-7 w-7 flex items-center justify-center rounded-md hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
        @click="theme.toggle()"
        :title="theme.isDark.value ? '浅色模式' : '深色模式'"
      >
        <Sun v-if="theme.isDark.value" class="h-4 w-4" />
        <Moon v-else class="h-4 w-4" />
      </button>
    </div>
  </header>
</template>

<script setup>
import { inject } from 'vue'
import { PanelLeft, FolderOpen, BarChart3, Sun, Moon } from 'lucide-vue-next'
import { useChatStore } from '../../stores/useChatStore.js'
import { useTheme } from '../../composables/useTheme.ts'

defineEmits(['open-docs', 'open-eval'])

const chatStore = useChatStore()
const theme = useTheme()
const toggleMobileSidebar = inject('toggleMobileSidebar', () => {})
</script>
