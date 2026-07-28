<script setup>
import { ref } from 'vue'
import { Menu, X } from 'lucide-vue-next'
import ScrollArea from '../ui/scroll-area.vue'

const props = defineProps({
  sidebarWidth: { type: String, default: 'w-[272px]' },
  title: { type: String, default: '' },
})

const mobileSidebarOpen = ref(false)
</script>

<template>
  <div class="flex h-full w-full">
    <!-- 桌面端侧栏 -->
    <div :class="`hidden lg:flex flex-col h-full ${props.sidebarWidth} border-r border-border/45 bg-background flex-shrink-0`">
      <slot name="sidebar" />
    </div>

    <!-- 主内容区 -->
    <main class="flex-1 min-w-0 overflow-hidden">
      <!-- 移动端顶部栏 -->
      <div class="lg:hidden flex items-center gap-2 px-3 h-12 border-b border-border bg-background flex-shrink-0">
        <button
          class="h-9 w-9 flex items-center justify-center rounded-md hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
          @click="mobileSidebarOpen = true"
          title="打开菜单"
        >
          <Menu class="h-4 w-4" />
        </button>
        <h1 v-if="title" class="text-base font-semibold text-foreground truncate">{{ title }}</h1>
        <slot name="mobile-header" />
      </div>

      <ScrollArea class="h-full">
        <div class="mx-auto max-w-[920px] px-4 py-4 sm:px-6 sm:py-6 lg:px-8 lg:py-8">
          <slot />
        </div>
      </ScrollArea>
    </main>

    <!-- 移动端侧栏 Sheet -->
    <Teleport to="body">
      <Transition name="mobile-sidebar">
        <div v-if="mobileSidebarOpen" class="fixed inset-0 z-50 lg:hidden">
          <!-- 遮罩 -->
          <div
            class="absolute inset-0 bg-black/40 backdrop-blur-sm"
            @click="mobileSidebarOpen = false"
          />
          <!-- 侧栏面板 -->
          <div class="absolute left-0 top-0 h-full w-[min(280px,calc(100vw-12px))] bg-background border-r border-border flex flex-col">
            <!-- 关闭按钮 -->
            <div class="flex items-center justify-between px-3 h-12 border-b border-border flex-shrink-0">
              <span class="text-sm font-semibold text-foreground">{{ title || '菜单' }}</span>
              <button
                class="h-9 w-9 flex items-center justify-center rounded-md hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
                @click="mobileSidebarOpen = false"
                title="关闭"
              >
                <X class="h-4 w-4" />
              </button>
            </div>
            <!-- 侧栏内容 -->
            <div class="flex-1 overflow-y-auto min-h-0">
              <div @click="mobileSidebarOpen = false">
                <slot name="sidebar" />
              </div>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
.mobile-sidebar-enter-active,
.mobile-sidebar-leave-active {
  transition: opacity 0.25s ease;
}
.mobile-sidebar-enter-active > div:last-child,
.mobile-sidebar-leave-active > div:last-child {
  transition: transform 0.25s ease;
}
.mobile-sidebar-enter-from,
.mobile-sidebar-leave-to {
  opacity: 0;
}
.mobile-sidebar-enter-from > div:last-child,
.mobile-sidebar-leave-to > div:last-child {
  transform: translateX(-100%);
}
</style>
