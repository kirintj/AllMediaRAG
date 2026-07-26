<script setup>
import { ContextMenuTrigger } from 'radix-vue'
</script>

<template>
  <ContextMenuTrigger as-child>
    <slot />
  </ContextMenuTrigger>
</template>
