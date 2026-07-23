import api from './index.js'

export async function getGraphData(limit = 200) {
  const res = await api.get('/graph/data', { params: { limit } })
  return res.data
}

export async function searchGraph(q, limit = 20) {
  const res = await api.get('/graph/search', { params: { q, limit } })
  return res.data
}

export async function getGraphStats() {
  const res = await api.get('/graph/stats')
  return res.data
}
