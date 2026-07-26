<script setup>
import { ContextMenuItem } from 'radix-vue'
import { cn } from '@/lib/utils'

const props = defineProps({
  class: { type: String, default: '' },
  inset: { type: Boolean, default: false },
  destructive: { type: Boolean, default: false },
})

const emit = defineEmits(['select'])
</script>

<template>
  <ContextMenuItem
    :class="cn(
      'relative flex cursor-pointer select-none items-center gap-2 rounded-sm px-2 py-1.5 text-sm outline-none transition-colors',
      'focus:bg-accent focus:text-accent-foreground',
      'data-[disabled]:pointer-events-none data-[disabled]:opacity-50',
      '[&>svg]:size-4 [&>svg]:shrink-0',
      props.inset && 'pl-8',
      props.destructive && 'text-destructive focus:bg-destructive/10 focus:text-destructive',
      props.class
    )"
    @select="emit('select')"
  >
    <slot />
  </ContextMenuItem>
</template>
