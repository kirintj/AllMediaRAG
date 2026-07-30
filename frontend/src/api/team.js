import api from './index.js'

export async function listTeams() {
  const res = await api.get('/team/list')
  return res.data
}

export async function createTeam(name) {
  const res = await api.post('/team/create', { name })
  return res.data
}

export async function listMembers(tenantId) {
  const res = await api.get('/team/members', { params: { tenant_id: tenantId } })
  return res.data
}

export async function inviteMember(tenantId, username) {
  const res = await api.post('/team/invite', { username }, { params: { tenant_id: tenantId } })
  return res.data
}

export async function listInvitations() {
  const res = await api.get('/team/invitations')
  return res.data
}

export async function acceptInvitation(invitationId) {
  const res = await api.post(`/team/invitations/${invitationId}/accept`)
  return res.data
}

export async function rejectInvitation(invitationId) {
  const res = await api.post(`/team/invitations/${invitationId}/reject`)
  return res.data
}

export async function updateMemberRole(tenantId, userId, role) {
  const res = await api.put(`/team/members/${userId}`, { role }, { params: { tenant_id: tenantId } })
  return res.data
}

export async function removeMember(tenantId, userId) {
  const res = await api.delete(`/team/members/${userId}`, { params: { tenant_id: tenantId } })
  return res.data
}
