import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useConfirmStore = defineStore('confirm', () => {
  const visible = ref(false)
  const title = ref('确认')
  const message = ref('')
  const confirmText = ref('确认')
  const cancelText = ref('取消')
  const destructive = ref(false)
  let resolveFn = null

  function confirm({ message: msg, title: t = '确认', confirmText: ct = '确认', cancelText: xt = '取消', destructive: d = false } = {}) {
    message.value = msg
    title.value = t
    confirmText.value = ct
    cancelText.value = xt
    destructive.value = d
    visible.value = true
    return new Promise(resolve => {
      resolveFn = resolve
    })
  }

  function handleConfirm() {
    visible.value = false
    resolveFn?.(true)
    resolveFn = null
  }

  function handleCancel() {
    visible.value = false
    resolveFn?.(false)
    resolveFn = null
  }

  return {
    visible,
    title,
    message,
    confirmText,
    cancelText,
    destructive,
    confirm,
    handleConfirm,
    handleCancel,
  }
})
