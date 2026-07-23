<script setup>
import { TabsRoot } from 'radix-vue'

const model = defineModel()
const props = defineProps({
  defaultValue: { type: String, default: '' },
})
</script>

<template>
  <TabsRoot v-model="model" :default-value="defaultValue">
    <slot />
  </TabsRoot>
</template>
