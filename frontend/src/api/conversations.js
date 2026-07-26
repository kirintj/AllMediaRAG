import api from './index.js'

export async function getConversations() {
  const response = await api.get('/conversations')
  return response.data
}

export async function getConversation(id) {
  const response = await api.get(`/conversations/${id}`)
  return response.data
}

export async function deleteConversation(id) {
  const response = await api.delete(`/conversations/${id}`)
  return response.data
}

export async function clearAllConversations() {
  const response = await api.delete('/conversations')
  return response.data
}

export async function renameConversation(id, title) {
  const response = await api.patch(`/conversations/${id}`, { title })
  return response.data
}

export async function toggleFavorite(id, isFavorite) {
  const response = await api.patch(`/conversations/${id}`, { is_favorite: isFavorite })
  return response.data
}

export async function duplicateConversation(id) {
  const response = await api.post(`/conversations/${id}/duplicate`)
  return response.data
}

export async function archiveConversation(id) {
  const response = await api.patch(`/conversations/${id}`, { status: 'archived' })
  return response.data
}

export async function shareConversation(id) {
  const response = await api.post(`/conversations/${id}/share`)
  return response.data
}
