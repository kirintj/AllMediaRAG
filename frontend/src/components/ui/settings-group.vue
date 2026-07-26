<script setup>
import { cn } from '@/lib/utils'

const props = defineProps({
  class: { type: String, default: '' },
})
</script>

<template>
  <div :class="cn(
    'overflow-hidden rounded-[22px] border border-border/45 bg-card/86',
    'shadow-[0_18px_65px_rgba(15,23,42,0.075)] backdrop-blur-xl',
    'dark:border-white/10 dark:shadow-[0_18px_65px_rgba(0,0,0,0.24)]',
    props.class
  )">
    <div class="divide-y divide-border/45">
      <slot />
    </div>
  </div>
</template>
