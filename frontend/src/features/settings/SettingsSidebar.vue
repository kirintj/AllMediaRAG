<script setup>
import { useNavigationStore } from '../../stores/useNavigationStore.js'
import { useAuthStore } from '../../stores/useAuthStore.js'
import { LayoutDashboard, FileText, Layers, Tag, Network, ArrowLeft, LogOut, Cpu, BarChart3 } from 'lucide-vue-next'
import { cn } from '../../lib/utils.js'

const navigationStore = useNavigationStore()
const authStore = useAuthStore()

const navItems = [
  { key: 'overview', label: '概览', icon: LayoutDashboard },
  { key: 'doc-parsing', label: '文档解析', icon: FileText },
  { key: 'raptor', label: 'RAPTOR', icon: Layers },
  { key: 'tagging', label: '内容标签', icon: Tag },
  { key: 'graphrag', label: '知识图谱', icon: Network },
  { key: 'models', label: '模型管理', icon: Cpu },
  { key: 'eval', label: '评测看板', icon: BarChart3 },
]

function selectSection(key) {
  navigationStore.setActiveSettingsSection(key)
}

function backToChat() {
  navigationStore.setActiveNav('chat')
}
</script>

<template>
  <div class="flex flex-col h-full w-[272px] border-r border-border/45 bg-background flex-shrink-0">
    <!-- Back button -->
    <div class="px-3 pt-3 pb-1">
      <button
        @click="backToChat"
        class="flex items-center gap-2 w-full px-3 py-2 rounded-[10px] text-sm text-muted-foreground hover:bg-muted/45 transition-colors"
      >
        <ArrowLeft class="h-4 w-4" />
        <span>返回</span>
      </button>
    </div>

    <!-- Title -->
    <div class="px-5 pt-2 pb-3">
      <h1 class="text-lg font-semibold text-foreground">设置</h1>
    </div>

    <!-- Nav items -->
    <nav class="flex-1 overflow-y-auto min-h-0 px-3">
      <div class="flex flex-col gap-0.5">
        <button
          v-for="item in navItems"
          :key="item.key"
          @click="selectSection(item.key)"
          :class="cn(
            'flex items-center gap-3 w-full px-3 py-2.5 rounded-[10px] text-sm transition-colors',
            navigationStore.activeSettingsSection === item.key
              ? 'bg-muted/60 text-foreground font-medium'
              : 'text-muted-foreground hover:bg-muted/45 hover:text-foreground',
          )"
        >
          <component :is="item.icon" class="h-4 w-4 flex-shrink-0" />
          <span>{{ item.label }}</span>
        </button>
      </div>
    </nav>

    <!-- Logout -->
    <div class="flex-shrink-0 px-3 py-3 border-t border-border/45">
      <button
        @click="authStore.logout()"
        class="flex items-center gap-3 w-full px-3 py-2.5 rounded-[10px] text-sm text-destructive hover:bg-destructive/10 transition-colors"
      >
        <LogOut class="h-4 w-4 flex-shrink-0" />
        <span>退出登录</span>
      </button>
    </div>
  </div>
</template>
