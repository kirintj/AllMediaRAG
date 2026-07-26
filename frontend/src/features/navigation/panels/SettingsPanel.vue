<template>
  <div class="flex flex-col h-full">
    <!-- Header -->
    <div class="flex items-center px-4 h-12 border-b border-border flex-shrink-0">
      <h3 class="text-sm font-semibold text-foreground">设置</h3>
    </div>

    <!-- Settings entries -->
    <div class="flex-1 overflow-y-auto min-h-0 px-2 py-2">
      <div class="flex flex-col gap-0.5">
        <button
          v-for="entry in settingsEntries"
          :key="entry.label"
          class="flex items-center gap-3 px-3 py-2.5 rounded-md text-sm text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
          @click="entry.handler"
        >
          <component :is="entry.icon" class="h-4 w-4 flex-shrink-0" />
          <span>{{ entry.label }}</span>
        </button>
      </div>
    </div>

    <!-- Footer -->
    <div class="flex-shrink-0 border-t border-border px-2 py-2">
      <button
        class="flex items-center gap-3 w-full px-3 py-2.5 rounded-md text-sm text-destructive hover:bg-destructive/10 transition-colors"
        @click="$emit('logout')"
      >
        <LogOut class="h-4 w-4 flex-shrink-0" />
        <span>退出登录</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { FileText, FolderOpen, Cpu, Tags, Settings, Network, Users, BarChart3, LogOut } from 'lucide-vue-next'

const emit = defineEmits([
  'open-docs', 'open-kb', 'open-models', 'open-tag-kb',
  'open-settings', 'open-graph', 'open-team', 'open-eval', 'logout',
])

const settingsEntries = [
  { label: '文档管理', icon: FileText, handler: () => emit('open-docs') },
  { label: '知识库管理', icon: FolderOpen, handler: () => emit('open-kb') },
  { label: '模型管理', icon: Cpu, handler: () => emit('open-models') },
  { label: '标签知识库', icon: Tags, handler: () => emit('open-tag-kb') },
  { label: 'RAG 设置', icon: Settings, handler: () => emit('open-settings') },
  { label: '知识图谱', icon: Network, handler: () => emit('open-graph') },
  { label: '团队管理', icon: Users, handler: () => emit('open-team') },
  { label: '评测看板', icon: BarChart3, handler: () => emit('open-eval') },
]
</script>
