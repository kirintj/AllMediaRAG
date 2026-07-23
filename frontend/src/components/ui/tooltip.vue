<script setup>
import { TooltipProvider, TooltipRoot } from 'radix-vue'
</script>

<template>
  <TooltipProvider>
    <TooltipRoot>
      <slot />
    </TooltipRoot>
  </TooltipProvider>
</template>
