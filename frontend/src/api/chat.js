import { getAuthHeaders } from './index.js'

export async function chatStream(message, mode, onChunk, conversationId, history = [], modelId = null) {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), 120000)

  try {
    const body = { message, mode, history }
    if (conversationId) body.conversation_id = conversationId
    if (modelId) body.model_id = modelId

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
        // 处理 event: 行（如 event: error / event: verification）
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
              // verification 独立事件：推送后关闭连接
              if (currentEvent === 'verification') {
                onChunk({ verification: data.verification, conversation_id: data.conversation_id })
                return
              }
              // 收到结束标记（可能包含 verification）
              if (data.done) {
                onChunk(data)
                // 不 return，继续读取后续 verification 事件
                currentEvent = ''
                continue
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
          onChunk(data)
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
