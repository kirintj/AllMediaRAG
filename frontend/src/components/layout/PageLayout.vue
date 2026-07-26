<script setup>
import ScrollArea from '../ui/scroll-area.vue'

const props = defineProps({
  sidebarWidth: { type: String, default: 'w-[272px]' },
})
</script>

<template>
  <div class="flex h-full w-full">
    <div :class="`flex flex-col h-full ${props.sidebarWidth} border-r border-border/45 bg-background flex-shrink-0`">
      <slot name="sidebar" />
    </div>
    <main class="flex-1 min-w-0 overflow-hidden">
      <ScrollArea class="h-full">
        <div class="mx-auto max-w-[920px] px-6 py-6 sm:px-8 sm:py-8">
          <slot />
        </div>
      </ScrollArea>
    </main>
  </div>
</template>
