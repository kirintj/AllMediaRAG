import api from './index.js'

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
