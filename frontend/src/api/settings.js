import api from './index.js'

export async function getSettings() {
  const response = await api.get('/settings')
  return response.data
}

export async function updateSettings(group, settings) {
  const response = await api.put('/settings', { group, settings })
  return response.data
}
