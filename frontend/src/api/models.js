import api from './index.js'

export async function getModelTypes() {
  const res = await api.get('/models/types')
  return res.data
}

export async function getFactories() {
  const res = await api.get('/models/factories')
  return res.data
}

export async function getModels() {
  const res = await api.get('/models')
  return res.data
}

export async function addModel({ llm_factory, model_type, llm_name, api_key, api_base = '' }) {
  const body = { model_type, llm_name, api_key, api_base }
  if (llm_factory) body.llm_factory = llm_factory
  const res = await api.post('/models', body)
  return res.data
}

export async function deleteModel(modelId) {
  const res = await api.delete(`/models/${modelId}`)
  return res.data
}

export async function setDefaultModel(model_type, model_id) {
  const res = await api.post('/models/default', { model_type, model_id })
  return res.data
}

export async function getDefaults() {
  const res = await api.get('/models/defaults')
  return res.data
}

export async function getModel(modelId) {
  const res = await api.get(`/models/${modelId}`)
  return res.data
}

export async function updateModel(modelId, payload) {
  const res = await api.put(`/models/${modelId}`, payload)
  return res.data
}
