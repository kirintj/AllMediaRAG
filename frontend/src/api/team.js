import api from './index.js'

export async function listMembers() {
  const res = await api.get('/team/members')
  return res.data
}

export async function inviteMember(username) {
  const res = await api.post('/team/invite', { username })
  return res.data
}

export async function updateMemberRole(userId, role) {
  const res = await api.put(`/team/members/${userId}`, { role })
  return res.data
}

export async function removeMember(userId) {
  const res = await api.delete(`/team/members/${userId}`)
  return res.data
}
