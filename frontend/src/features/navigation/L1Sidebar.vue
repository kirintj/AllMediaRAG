<template>
  <aside class="flex flex-col items-center h-full w-[52px] py-3 bg-sidebar border-r border-sidebar-border flex-shrink-0">
    <!-- Logo -->
    <div class="flex-shrink-0 w-8 h-8 rounded-lg bg-primary flex items-center justify-center mb-3">
      <Sparkles class="h-4 w-4 text-primary-foreground" />
    </div>

    <!-- Navigation icons -->
    <nav class="flex flex-col items-center gap-1 flex-1">
      <NavItem
        v-for="item in navItems"
        :key="item.nav"
        :icon="item.icon"
        :label="item.label"
        :active="navigationStore.activeNav === item.nav"
        @click="navigationStore.setActiveNav(item.nav)"
      />
    </nav>

    <!-- Bottom actions -->
    <div class="flex flex-col items-center gap-1 pt-2 border-t border-sidebar-border w-8">
      <NavItem
        :icon="navigationStore.l2Expanded ? PanelLeftClose : PanelLeftOpen"
        :label="navigationStore.l2Expanded ? '收起面板' : '展开面板'"
        @click="navigationStore.toggleL2()"
      />

      <!-- User menu -->
      <DropdownMenuRoot>
        <DropdownMenuTrigger as-child>
          <button
            class="flex items-center justify-center w-9 h-9 rounded-lg text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground transition-colors"
            title="用户菜单"
          >
            <User class="h-4 w-4" />
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent
          side="right"
          :side-offset="8"
          align="end"
          :class="cn(
            'z-50 min-w-[8rem] overflow-hidden rounded-md border bg-popover p-1 text-popover-foreground shadow-md',
            'data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0',
            'data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95',
            'data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2 data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2'
          )"
        >
          <DropdownMenuItem
            class="relative flex cursor-pointer select-none items-center gap-2 rounded-sm px-2 py-1.5 text-sm outline-none transition-colors focus:bg-accent focus:text-accent-foreground"
            @click="$emit('logout')"
          >
            <LogOut class="h-4 w-4" />
            <span>退出登录</span>
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenuRoot>
    </div>
  </aside>
</template>

<script setup>
import { Sparkles, MessageSquare, Database, Users, Settings, PanelLeftClose, PanelLeftOpen, User, LogOut } from 'lucide-vue-next'
import { useNavigationStore } from '../../stores/useNavigationStore.js'
import NavItem from './NavItem.vue'
import { DropdownMenuRoot, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem } from 'radix-vue'
import { cn } from '@/lib/utils'

defineEmits(['logout'])

const navigationStore = useNavigationStore()

const navItems = [
  { nav: 'chat', icon: MessageSquare, label: '对话' },
  { nav: 'kb', icon: Database, label: '知识库' },
  { nav: 'team', icon: Users, label: '团队' },
  { nav: 'settings', icon: Settings, label: '设置' },
]
</script>
