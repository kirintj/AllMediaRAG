import { ref } from 'vue'
import { defineStore } from 'pinia'

export const useModelStore = defineStore('model', () => {
  const factories = ref([])
  const models = ref([])
  const modelTypes = ref([])
  const loading = ref(false)
  const error = ref(null)

  async function fetchFactories() {
    try {
      const { getFactories } = await import('../api/models.js')
      const data = await getFactories()
      factories.value = data.factories || []
    } catch (err) {
      console.error('Failed to fetch factories:', err)
    }
  }

  async function fetchModels() {
    loading.value = true
    try {
      const { getModels } = await import('../api/models.js')
      const data = await getModels()
      models.value = data.models || []
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  async function fetchModelTypes() {
    try {
      const { getModelTypes } = await import('../api/models.js')
      const data = await getModelTypes()
      modelTypes.value = data.types || []
    } catch (err) {
      console.error('Failed to fetch model types:', err)
    }
  }

  async function addNewModel(config) {
    const { addModel } = await import('../api/models.js')
    await addModel(config)
    await fetchModels()
  }

  async function removeModel(modelId) {
    const { deleteModel } = await import('../api/models.js')
    await deleteModel(modelId)
    await fetchModels()
  }

  async function setDefault(modelType, modelId) {
    const { setDefaultModel } = await import('../api/models.js')
    await setDefaultModel(modelType, modelId)
  }

  return {
    factories, models, modelTypes, loading, error,
    fetchFactories, fetchModels, fetchModelTypes,
    addNewModel, removeModel, setDefault,
  }
})
