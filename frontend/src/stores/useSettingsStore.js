import { ref } from 'vue'
import { defineStore } from 'pinia'

/**
 * Maps between frontend form field names and backend RagSettings model names.
 * Frontend uses short names (e.g. "auto_keywords"), backend uses prefixed names (e.g. "enable_auto_keywords").
 */
const TO_BACKEND = {
  auto_keywords: 'enable_auto_keywords',
  auto_questions: 'enable_auto_questions',
  metadata_extraction: 'enable_metadata_extraction',
  toc_extraction: 'enable_toc_extraction',
  keywords_topn: 'auto_keywords_topn',
  questions_topn: 'auto_questions_topn',
  raptor_enabled: 'enable_raptor',
  raptor_method: 'raptor_clustering_method',
  raptor_max_clusters: 'raptor_max_clusters',
  tagging_enabled: 'enable_content_tagging',
  tagging_topn: 'content_tag_topn',
  tagging_tag_kb_ids: 'content_tag_kb_ids',
  graphrag_enabled: 'graphrag_enabled',
  graphrag_method: 'graphrag_method',
  graphrag_entity_resolution: 'graphrag_enable_resolution',
  graphrag_community_detection: 'graphrag_enable_community',
  graphrag_pagerank: 'graphrag_pagerank_enabled',
}

// Reverse map: backend -> frontend
const TO_FRONTEND = Object.fromEntries(
  Object.entries(TO_BACKEND).map(([k, v]) => [v, k])
)

function mapToBackend(form) {
  const result = {}
  for (const [key, value] of Object.entries(form)) {
    const backendKey = TO_BACKEND[key] || key
    result[backendKey] = value
  }
  return result
}

function mapToFrontend(backendData) {
  const result = {}
  for (const [key, value] of Object.entries(backendData)) {
    const frontendKey = TO_FRONTEND[key] || key
    result[frontendKey] = value
  }
  return result
}

export const useSettingsStore = defineStore('settings', () => {
  const settings = ref(null)
  const loading = ref(false)
  const saving = ref(false)

  async function fetchSettings() {
    loading.value = true
    try {
      const { getRagSettings } = await import('../api/settings.js')
      const raw = await getRagSettings()
      settings.value = mapToFrontend(raw)
    } finally {
      loading.value = false
    }
  }

  async function saveSettings(formPayload) {
    saving.value = true
    try {
      const { updateRagSettings } = await import('../api/settings.js')
      const backendPayload = mapToBackend(formPayload)
      const result = await updateRagSettings(backendPayload)
      settings.value = mapToFrontend(result.settings)
      return result
    } finally {
      saving.value = false
    }
  }

  return { settings, loading, saving, fetchSettings, saveSettings }
})
