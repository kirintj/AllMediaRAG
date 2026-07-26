<script setup>
import { cn } from '@/lib/utils'

const props = defineProps({
  checked: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  label: { type: String, default: '' },
})

const emit = defineEmits(['update:checked'])

function toggle() {
  if (!props.disabled) {
    emit('update:checked', !props.checked)
  }
}
</script>

<template>
  <button
    type="button"
    role="switch"
    :aria-checked="checked"
    :aria-label="label"
    :disabled="disabled"
    @click="toggle"
    :class="cn(
      'relative inline-flex h-[22px] w-[38px] shrink-0 items-center rounded-full p-[2px]',
      'transition-colors duration-200 ease-out focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
      checked
        ? 'bg-[#2997FF] shadow-[inset_0_0_0_1px_rgba(0,0,0,0.035)]'
        : 'bg-muted shadow-[inset_0_0_0_1px_rgba(0,0,0,0.035)] hover:bg-muted/80',
      disabled && 'cursor-default opacity-60',
    )"
  >
    <span
      aria-hidden
      :class="cn(
        'h-[18px] w-[18px] rounded-full bg-background shadow-[0_1px_2px_rgba(0,0,0,0.18),0_2px_7px_rgba(0,0,0,0.11)]',
        'transition-transform duration-200 ease-out',
        checked ? 'translate-x-[16px]' : 'translate-x-0',
      )"
    />
    <span class="sr-only">{{ label }}</span>
  </button>
</template>
