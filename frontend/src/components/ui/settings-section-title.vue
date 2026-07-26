<script setup>
const props = defineProps({
  class: { type: String, default: '' },
})
</script>

<template>
  <h2 :class="`mb-2 px-1 text-[13px] font-semibold tracking-[-0.01em] text-foreground/85 ${props.class}`">
    <slot />
  </h2>
</template>
