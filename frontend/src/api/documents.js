import api from './index.js'

export async function uploadDocument(file) {
  const formData = new FormData()
  formData.append('file', file)

  const response = await api.post('/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })

  return response.data
}

// 批量上传
export async function uploadBatch(files) {
  const formData = new FormData()
  files.forEach(file => {
    formData.append('files', file.raw || file)
  })

  const response = await api.post('/upload/batch', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 300000  // 5 分钟超时
  })
  return response.data
}

// 查询批量上传进度
export async function getBatchStatus(taskId) {
  const response = await api.get(`/upload/batch/status/${taskId}`)
  return response.data
}

export async function getDocuments() {
  const response = await api.get('/documents')
  return response.data
}

export async function getDocumentDetails() {
  const response = await api.get('/documents/detail')
  return response.data
}

export async function loadDocuments() {
  const response = await api.post('/documents/load')
  return response.data
}

export async function getLoadStatus() {
  const response = await api.get('/documents/load/status')
  return response.data
}

export async function getStats() {
  const response = await api.get('/stats')
  return response.data
}

export async function deleteDocument(source) {
  const response = await api.delete(`/documents/${encodeURIComponent(source)}`)
  return response.data
}

export async function clearAllDocuments() {
  const response = await api.delete('/documents')
  return response.data
}

export async function syncDocuments() {
  const response = await api.post('/documents/sync')
  return response.data
}
