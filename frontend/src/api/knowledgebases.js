import api from './index.js'

export async function listKnowledgebases() {
  const res = await api.get('/knowledgebases')
  return res.data
}

export async function createKnowledgebase({ name, permission = 'me', language = 'zh', description = '' }) {
  const res = await api.post('/knowledgebases', { name, permission, language, description })
  return res.data
}

export async function getKnowledgebase(kbId) {
  const res = await api.get(`/knowledgebases/${kbId}`)
  return res.data
}

export async function updateKnowledgebase(kbId, data) {
  const res = await api.put(`/knowledgebases/${kbId}`, data)
  return res.data
}

export async function deleteKnowledgebase(kbId) {
  const res = await api.delete(`/knowledgebases/${kbId}`)
  return res.data
}

export async function listKBDocuments(kbId) {
  const res = await api.get(`/knowledgebases/${kbId}/documents`)
  return res.data
}

export async function uploadToKB(kbId, file) {
  const formData = new FormData()
  formData.append('file', file)
  const res = await api.post(`/knowledgebases/${kbId}/upload`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data
}

export async function deleteKBDocument(kbId, docId) {
  const res = await api.delete(`/knowledgebases/${kbId}/documents/${docId}`)
  return res.data
}
