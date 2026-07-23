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

export async function getOverview() {
  const response = await api.get('/documents/overview')
  return response.data
}

export async function loadDocuments() {
  const response = await api.post('/documents/load')
  return response.data
}

// 查询单个任务状态
export async function getTaskStatus(taskId) {
  const res = await api.get(`/tasks/${taskId}`)
  return res.data
}

// 查询批次状态
export async function getBatchStatus(batchId) {
  const res = await api.get(`/batches/${batchId}`)
  return res.data
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
