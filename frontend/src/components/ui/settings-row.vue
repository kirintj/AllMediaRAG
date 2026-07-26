<script setup>
const props = defineProps({
  title: { type: String, required: true },
  description: { type: String, default: '' },
})
</script>

<template>
  <div class="flex min-h-[62px] flex-col gap-3 px-4 py-3.5 sm:flex-row sm:items-center sm:justify-between sm:px-5">
    <div class="min-w-0">
      <div class="text-[14px] font-medium leading-5 text-foreground">{{ title }}</div>
      <div v-if="description" class="mt-0.5 max-w-[28rem] text-[12px] leading-5 text-muted-foreground">
        {{ description }}
      </div>
    </div>
    <div class="min-w-0 sm:ml-6 sm:shrink-0">
      <slot />
    </div>
  </div>
</template>
