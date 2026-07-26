<template>
  <TooltipProvider :delay-duration="300">
    <TooltipRoot>
      <TooltipTrigger as-child>
        <button
          class="flex items-center justify-center w-9 h-9 rounded-lg transition-colors relative"
          :class="active
            ? 'bg-sidebar-accent text-sidebar-accent-foreground'
            : 'text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground'"
          @click="$emit('click')"
        >
          <!-- Active indicator bar -->
          <div
            v-if="active"
            class="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-4 rounded-r-full bg-primary"
          />
          <component :is="icon" class="h-4 w-4" />
        </button>
      </TooltipTrigger>
      <TooltipPortal>
        <TooltipContent
          side="right"
          :side-offset="8"
          class="z-50 px-2.5 py-1.5 text-xs font-medium rounded-md bg-primary text-primary-foreground shadow-md animate-in fade-in-0 zoom-in-95 data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95"
        >
          {{ label }}
          <TooltipArrow class="fill-primary" />
        </TooltipContent>
      </TooltipPortal>
    </TooltipRoot>
  </TooltipProvider>
</template>

<script setup>
import { TooltipProvider, TooltipRoot, TooltipTrigger, TooltipPortal, TooltipContent, TooltipArrow } from 'radix-vue'

defineProps({
  icon: { type: Object, required: true },
  label: { type: String, required: true },
  active: { type: Boolean, default: false },
})

defineEmits(['click'])
</script>
