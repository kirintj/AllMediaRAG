import { ref } from 'vue'
import { defineStore } from 'pinia'

export const useSettingsStore = defineStore('settings', () => {
  const settings = ref(null)
  const loading = ref(false)
  const saving = ref(false)

  async function fetchSettings() {
    loading.value = true
    try {
      const { getRagSettings } = await import('../api/settings.js')
      settings.value = await getRagSettings()
    } finally {
      loading.value = false
    }
  }

  async function saveSettings(newSettings) {
    saving.value = true
    try {
      const { updateRagSettings } = await import('../api/settings.js')
      const result = await updateRagSettings(newSettings)
      settings.value = result.settings
      return result
    } finally {
      saving.value = false
    }
  }

  return { settings, loading, saving, fetchSettings, saveSettings }
})
