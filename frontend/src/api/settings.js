import api from './index.js'

export async function getRagSettings() {
  const res = await api.get('/settings/rag')
  return res.data
}

export async function updateRagSettings(settings) {
  const res = await api.put('/settings/rag', settings)
  return res.data
}
