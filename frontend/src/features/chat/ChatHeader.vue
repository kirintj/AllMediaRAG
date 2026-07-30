<template>
  <header class="flex items-center justify-between h-12 lg:h-12 px-3 sm:px-4 border-b border-border bg-background/80 backdrop-blur-sm flex-shrink-0">
    <div class="flex items-center gap-2 min-w-0">
      <button
        class="h-9 w-9 lg:h-7 lg:w-7 flex items-center justify-center rounded-md hover:bg-accent text-muted-foreground hover:text-foreground transition-colors lg:hidden"
        @click="toggleMobileSidebar"
        title="对话列表"
      >
        <PanelLeft class="h-4 w-4" />
      </button>
      <h3 class="text-base font-semibold text-foreground truncate">对话</h3>
      <span v-if="currentModelName" class="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded-full truncate max-w-[12rem]">{{ currentModelName }}</span>
      <span v-if="chatStore.loading" class="flex items-center gap-0.5">
        <span class="w-1 h-1 rounded-full bg-primary animate-bounce" style="animation-delay: 0s" />
        <span class="w-1 h-1 rounded-full bg-primary animate-bounce" style="animation-delay: 0.15s" />
        <span class="w-1 h-1 rounded-full bg-primary animate-bounce" style="animation-delay: 0.3s" />
      </span>
    </div>

    <div class="flex items-center gap-0.5">
      <button
        class="h-9 w-9 lg:h-7 lg:w-7 flex items-center justify-center rounded-md hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
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
import { inject, ref, onMounted, watch } from 'vue'
import { PanelLeft, FolderOpen, BarChart3, Sun, Moon } from 'lucide-vue-next'
import { useChatStore } from '../../stores/useChatStore.js'
import { useModelStore } from '../../stores/useModelStore.js'
import { useTheme } from '../../composables/useTheme.ts'

defineEmits(['open-docs', 'open-eval'])

const chatStore = useChatStore()
const modelStore = useModelStore()
const theme = useTheme()
const toggleMobileSidebar = inject('toggleMobileSidebar', () => {})

const currentModelName = ref('')

async function loadModelName() {
  try {
    if (!modelStore.models.length) await modelStore.fetchModels()
    if (!Object.keys(modelStore.defaults).length) await modelStore.fetchDefaults()
    const chatModelId = modelStore.defaults?.chat
    if (chatModelId) {
      const model = modelStore.models.find(m => m.id === chatModelId)
      if (model) {
        currentModelName.value = model.llm_name
      }
    }
  } catch {}
}

onMounted(loadModelName)
watch(() => modelStore.defaults, loadModelName, { deep: true })
</script>
