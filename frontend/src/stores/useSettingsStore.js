import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getSettings, updateSettings } from '../api/settings.js'

export const useSettingsStore = defineStore('settings', () => {
  const groups = ref({})
  const loading = ref(false)
  const saving = ref(false)

  async function fetchSettings() {
    loading.value = true
    try {
      const data = await getSettings()
      groups.value = data.groups || {}
    } catch (error) {
      console.error('获取配置失败:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  async function saveSettings(group, settings) {
    saving.value = true
    try {
      const data = await updateSettings(group, settings)
      await fetchSettings()
      return data
    } catch (error) {
      console.error('保存配置失败:', error)
      throw error
    } finally {
      saving.value = false
    }
  }

  return {
    groups,
    loading,
    saving,
    fetchSettings,
    saveSettings,
  }
})
