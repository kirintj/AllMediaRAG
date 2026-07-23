import api from './index.js'

export async function uploadTagFile(file) {
  const formData = new FormData()
  formData.append('file', file)
  const res = await api.post('/tag-kb/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data
}

export async function listTagKbs() {
  const res = await api.get('/tag-kb')
  return res.data
}

export async function deleteTagKb(tagKbId) {
  const res = await api.delete(`/tag-kb/${tagKbId}`)
  return res.data
}

export async function getTagKbTags(tagKbId) {
  const res = await api.get(`/tag-kb/${tagKbId}/tags`)
  return res.data
}
