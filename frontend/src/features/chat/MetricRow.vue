<template>
  <div class="grid grid-cols-[80px_1fr_40px] items-center gap-1.5 text-[11px]">
    <span class="text-muted-foreground text-right">{{ label }}:</span>
    <div class="w-full h-1.5 bg-border rounded-full overflow-hidden">
      <div class="h-full bg-primary rounded-full transition-all duration-300" :style="{ width: (value * 100) + '%' }" />
    </div>
    <span class="text-right font-medium">{{ (value * 100).toFixed(0) }}%</span>
  </div>
</template>

<script setup>
defineProps({
  label: { type: String, required: true },
  value: { type: Number, required: true },
})
</script>
