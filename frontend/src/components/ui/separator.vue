<script setup>
import { cn } from '@/lib/utils'

const props = defineProps({
  class: { type: String, default: '' },
})
</script>

<template>
  <div :class="cn('h-px w-full shrink-0 bg-border', props.class)" />
</template>
