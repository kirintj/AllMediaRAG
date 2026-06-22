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
