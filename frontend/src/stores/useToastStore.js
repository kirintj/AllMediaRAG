import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useToastStore = defineStore('toast', () => {
  const toasts = ref([])
  let nextId = 0

  function show(msg, type = 'info', duration = 3000) {
    const id = nextId++
    toasts.value.push({ id, msg, type })
    if (duration > 0) {
      setTimeout(() => {
        remove(id)
      }, duration)
    }
  }

  function remove(id) {
    const idx = toasts.value.findIndex(t => t.id === id)
    if (idx !== -1) {
      toasts.value.splice(idx, 1)
    }
  }

  function success(msg, duration) {
    show(msg, 'success', duration)
  }

  function error(msg, duration) {
    show(msg, 'error', duration)
  }

  function warning(msg, duration) {
    show(msg, 'warning', duration)
  }

  return {
    toasts,
    show,
    success,
    error,
    warning,
    remove,
  }
})
