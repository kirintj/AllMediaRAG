import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 60000
})

// 请求拦截器：自动附加 Authorization header
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截器：401 自动清除 token
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      // 触发页面刷新以显示登录页
      window.dispatchEvent(new Event('auth-expired'))
    }
    return Promise.reject(error)
  }
)

// ========== 认证 API ==========

export async function login(username, password) {
  const response = await api.post('/auth/login', { username, password })
  return response.data
}

export async function register(username, password) {
  const response = await api.post('/auth/register', { username, password })
  return response.data
}

export async function getMe() {
  const response = await api.get('/auth/me')
  return response.data
}

// ========== 获取 auth header（用于 fetch SSE） ==========

function getAuthHeaders() {
  const headers = { 'Content-Type': 'application/json' }
  const token = localStorage.getItem('token')
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  return headers
}

// ========== 流式对话 ==========

export async function chatStream(message, mode, onChunk, conversationId, history = []) {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), 120000)

  try {
    const body = { message, mode, history }
    if (conversationId) body.conversation_id = conversationId

    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(body),
      signal: controller.signal
    })

    if (response.status === 401) {
      localStorage.removeItem('token')
      window.dispatchEvent(new Event('auth-expired'))
      throw new Error('认证已过期，请重新登录')
    }

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let hasReceivedData = false
    let currentEvent = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      hasReceivedData = true
      buffer += decoder.decode(value, { stream: true })

      // 处理完整的 SSE 事件
      const lines = buffer.split('\n')
      buffer = lines.pop() || '' // 保留不完整的行

      for (const line of lines) {
        // 处理 event: 行（如 event: error）
        if (line.startsWith('event: ')) {
          currentEvent = line.slice(7).trim()
          continue
        }
        if (line.startsWith('data: ')) {
          try {
            const jsonStr = line.slice(6).trim()
            if (jsonStr) {
              const data = JSON.parse(jsonStr)
              // 错误消息：先通知调用方，再退出
              if (data.error || currentEvent === 'error') {
                onChunk(data)
                return
              }
              // 收到结束标记（可能包含 verification）
              if (data.done) {
                onChunk(data)
                return
              }
              onChunk(data)
            }
          } catch (e) {
            console.warn('SSE parse error:', e, line)
          } finally {
            currentEvent = ''
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

// ========== 文档管理 ==========

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

export async function getDocuments() {
  const response = await api.get('/documents')
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

// ========== 对话历史 ==========

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

export default api
