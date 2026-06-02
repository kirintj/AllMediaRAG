import axios from 'axios'

const api = axios.create({
  baseURL: 'http://localhost:8000/api',
  timeout: 30000
})

// 流式对话
export async function chatStream(message, mode, onChunk, conversationId) {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), 120000)

  try {
    const body = { message, mode }
    if (conversationId) body.conversation_id = conversationId

    const response = await fetch('http://localhost:8000/api/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(body),
      signal: controller.signal
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let hasReceivedData = false

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      hasReceivedData = true
      buffer += decoder.decode(value, { stream: true })

      // 处理完整的 SSE 事件
      const lines = buffer.split('\n')
      buffer = lines.pop() || '' // 保留不完整的行

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const jsonStr = line.slice(6).trim()
            if (jsonStr) {
              const data = JSON.parse(jsonStr)
              // 收到结束标记直接返回
              if (data.done) return
              onChunk(data)
            }
          } catch (e) {
            console.warn('SSE parse error:', e, line)
          }
        }
      }
    }

    // 处理缓冲区中剩余的数据
    if (buffer.startsWith('data: ')) {
      try {
        const jsonStr = buffer.slice(6).trim()
        if (jsonStr) {
          const data = JSON.parse(jsonStr)
          if (!data.done) onChunk(data)
        }
      } catch (e) {
        console.warn('SSE parse error:', e, buffer)
      }
    }

    if (!hasReceivedData) {
      throw new Error('服务器未返回任何数据')
    }
  } finally {
    clearTimeout(timeoutId)
  }
}

// 上传文档
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

// 获取文档列表
export async function getDocuments() {
  const response = await api.get('/documents')
  return response.data
}

// 批量加载文档
export async function loadDocuments() {
  const response = await api.post('/documents/load')
  return response.data
}

// 获取统计信息
export async function getStats() {
  const response = await api.get('/stats')
  return response.data
}

// 清空历史
export async function clearHistory() {
  const response = await api.delete('/history')
  return response.data
}

// 删除单个文档
export async function deleteDocument(source) {
  const response = await api.delete(`/documents/${encodeURIComponent(source)}`)
  return response.data
}

// 清空所有文档
export async function clearAllDocuments() {
  const response = await api.delete('/documents')
  return response.data
}

// 对话历史
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

export default api
