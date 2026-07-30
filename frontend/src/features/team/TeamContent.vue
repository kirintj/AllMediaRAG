<script setup>
import { ref, onMounted, computed } from 'vue'
import { useToastStore } from '../../stores/useToastStore.js'
import { useConfirmStore } from '../../stores/useConfirmStore.js'
import {
  X, UserPlus, Trash2, Users, Shield, Plus,
  Check, XCircle, Mail, ChevronDown, ChevronUp,
} from 'lucide-vue-next'
import {
  listMembers, listTeams, createTeam, inviteMember,
  listInvitations, acceptInvitation, rejectInvitation,
  removeMember, updateMemberRole,
} from '../../api/team.js'

const toast = useToastStore()
const confirmStore = useConfirmStore()

// --- State ---
const members = ref([])
const teams = ref([])
const invitations = ref([])
const inviteUsername = ref('')
const newTeamName = ref('')
const loading = ref(false)
const showCreateTeam = ref(false)
const showInvitations = ref(false)
const pendingCount = computed(() => invitations.value.length)

const ROLE_LABELS = { owner: '管理员', normal: '成员' }
const STATUS_LABELS = { active: '已加入', pending: '待确认' }

// --- Fetch data ---
async function fetchAll() {
  loading.value = true
  try {
    const [membersData, teamsData, invitationsData] = await Promise.all([
      listMembers(),
      listTeams(),
      listInvitations(),
    ])
    members.value = membersData.members || []
    teams.value = teamsData.teams || []
    invitations.value = invitationsData.invitations || []
  } finally {
    loading.value = false
  }
}

// --- Create team ---
async function handleCreateTeam() {
  if (!newTeamName.value.trim()) return
  try {
    const res = await createTeam(newTeamName.value.trim())
    toast.success(res.message)
    newTeamName.value = ''
    showCreateTeam.value = false
    await fetchAll()
  } catch (err) {
    toast.error('创建团队失败: ' + (err.response?.data?.detail || err.message))
  }
}

// --- Invite ---
async function handleInvite() {
  if (!inviteUsername.value.trim()) return
  try {
    const res = await inviteMember(inviteUsername.value.trim())
    toast.success(res.message)
    inviteUsername.value = ''
    await fetchAll()
  } catch (err) {
    toast.error('邀请失败: ' + (err.response?.data?.detail || err.message))
  }
}

// --- Accept / Reject invitation ---
async function handleAccept(invitationId) {
  try {
    const res = await acceptInvitation(invitationId)
    toast.success(res.message)
    await fetchAll()
  } catch (err) {
    toast.error('接受邀请失败: ' + (err.response?.data?.detail || err.message))
  }
}

async function handleReject(invitationId) {
  if (!await confirmStore.confirm({ message: '确定拒绝此邀请？', destructive: true })) return
  try {
    const res = await rejectInvitation(invitationId)
    toast.success(res.message)
    await fetchAll()
  } catch (err) {
    toast.error('拒绝邀请失败: ' + (err.response?.data?.detail || err.message))
  }
}

// --- Remove member ---
async function handleRemove(userId, username, status) {
  const label = status === 'pending' ? '撤销邀请' : '移除成员'
  if (!await confirmStore.confirm({ message: `确定${label} ${username}？`, destructive: true })) return
  try {
    await removeMember(userId)
    toast.success(`${label}成功`)
    await fetchAll()
  } catch (err) {
    toast.error('操作失败: ' + (err.response?.data?.detail || err.message))
  }
}

// --- Update role ---
async function handleRoleChange(userId, newRole) {
  try {
    await updateMemberRole(userId, newRole)
    toast.success('角色已更新')
    await fetchAll()
  } catch (err) {
    toast.error('更新角色失败: ' + (err.response?.data?.detail || err.message))
  }
}

onMounted(() => fetchAll())
</script>

<template>
  <div class="space-y-5">
    <!-- Pending invitations notification -->
    <div v-if="pendingCount > 0"
         class="border border-yellow-300 dark:border-yellow-700 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg p-3">
      <button
        class="flex items-center justify-between w-full text-left"
        @click="showInvitations = !showInvitations">
        <div class="flex items-center gap-2 text-sm font-medium text-yellow-800 dark:text-yellow-200">
          <Mail class="h-4 w-4" />
          您有 {{ pendingCount }} 条待处理邀请
        </div>
        <component :is="showInvitations ? ChevronUp : ChevronDown" class="h-4 w-4 text-yellow-600" />
      </button>

      <div v-if="showInvitations" class="mt-3 space-y-2">
        <div v-for="inv in invitations" :key="inv.id"
             class="flex items-center justify-between p-2.5 bg-white dark:bg-gray-800 rounded-lg border">
          <div class="text-sm">
            <span class="font-medium">{{ inv.invited_by || '未知用户' }}</span>
            <span class="text-gray-500 dark:text-gray-400"> 邀请您加入 </span>
            <span class="font-medium">{{ inv.tenant_name }}</span>
          </div>
          <div class="flex items-center gap-1.5">
            <button @click="handleAccept(inv.id)"
                    class="px-2.5 py-1 text-xs font-medium bg-green-500 text-white rounded hover:bg-green-600 flex items-center gap-1">
              <Check class="h-3 w-3" /> 接受
            </button>
            <button @click="handleReject(inv.id)"
                    class="px-2.5 py-1 text-xs font-medium bg-red-500 text-white rounded hover:bg-red-600 flex items-center gap-1">
              <XCircle class="h-3 w-3" /> 拒绝
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- My teams -->
    <div>
      <div class="flex items-center justify-between mb-2">
        <h3 class="text-sm font-semibold text-foreground">我的团队</h3>
        <button @click="showCreateTeam = !showCreateTeam"
                class="flex items-center gap-1 text-xs font-medium text-primary hover:text-primary/80">
          <Plus class="h-3.5 w-3.5" /> 新建团队
        </button>
      </div>

      <!-- Create team form -->
      <div v-if="showCreateTeam" class="flex gap-2 mb-3">
        <input v-model="newTeamName" @keyup.enter="handleCreateTeam"
               placeholder="输入团队名称..."
               class="flex-1 px-3 py-2 border rounded text-sm bg-transparent" />
        <button @click="handleCreateTeam"
                class="px-3 py-2 bg-green-500 text-white rounded text-sm hover:bg-green-600">
          创建
        </button>
        <button @click="showCreateTeam = false; newTeamName = ''"
                class="px-2 py-2 text-gray-400 hover:text-foreground">
          <X class="h-4 w-4" />
        </button>
      </div>

      <!-- Teams list -->
      <div class="space-y-1.5">
        <div v-for="team in teams" :key="team.tenant_id"
             class="flex items-center justify-between p-2.5 border rounded-lg">
          <div>
            <div class="text-sm font-medium">{{ team.name }}</div>
            <div class="text-xs text-gray-400">
              {{ ROLE_LABELS[team.role] || team.role }} · {{ team.member_count }} 人
            </div>
          </div>
          <span v-if="team.role === 'owner'"
                class="text-[10px] px-1.5 py-0.5 bg-primary/10 text-primary rounded font-medium">
            管理员
          </span>
        </div>
        <div v-if="teams.length === 0" class="text-center py-4 text-xs text-gray-400">
          暂无团队
        </div>
      </div>
    </div>

    <!-- Divider -->
    <hr class="border-border" />

    <!-- Invite form -->
    <div>
      <h3 class="text-sm font-semibold text-foreground mb-2">邀请成员</h3>
      <div class="flex gap-2">
        <input v-model="inviteUsername" @keyup.enter="handleInvite"
               placeholder="输入用户名邀请成员..."
               class="flex-1 px-3 py-2 border rounded text-sm bg-transparent" />
        <button @click="handleInvite"
                class="px-3 py-2 bg-blue-500 text-white rounded text-sm hover:bg-blue-600 flex items-center gap-1">
          <UserPlus class="h-4 w-4" /> 邀请
        </button>
      </div>
    </div>

    <!-- Members list -->
    <div>
      <h3 class="text-sm font-semibold text-foreground mb-2">团队成员</h3>
      <div class="space-y-2">
        <div v-for="member in members" :key="member.user_id"
             class="flex items-center justify-between p-3 border rounded-lg">
          <div class="flex items-center gap-3">
            <div class="w-8 h-8 rounded-full bg-gray-200 dark:bg-gray-700 flex items-center justify-center text-sm font-medium">
              {{ member.username?.[0]?.toUpperCase() || '?' }}
            </div>
            <div>
              <div class="text-sm font-medium">
                {{ member.username }}
                <span v-if="member.status === 'pending'" class="text-xs text-yellow-600 ml-1">(待确认)</span>
              </div>
              <div class="flex items-center gap-1 text-xs text-gray-400">
                <Shield class="h-3 w-3" />
                {{ ROLE_LABELS[member.role] || member.role }}
              </div>
            </div>
          </div>

          <div class="flex items-center gap-2">
            <!-- Role selector for owner -->
            <select v-if="member.role !== 'owner' && member.status === 'active'"
                    :value="member.role"
                    @change="handleRoleChange(member.user_id, $event.target.value)"
                    class="text-xs border rounded px-1.5 py-0.5 bg-transparent">
              <option value="normal">成员</option>
              <option value="owner">管理员</option>
            </select>

            <!-- Remove / Cancel invite -->
            <button v-if="member.role !== 'owner'"
                    @click="handleRemove(member.user_id, member.username, member.status)"
                    class="p-1.5 hover:bg-red-50 dark:hover:bg-red-900/20 rounded"
                    :title="member.status === 'pending' ? '撤销邀请' : '移除成员'">
              <Trash2 class="h-4 w-4 text-gray-400 hover:text-red-500" />
            </button>
          </div>
        </div>
      </div>

      <div v-if="!loading && members.length === 0" class="text-center py-8 text-gray-400">
        <Users class="h-8 w-8 mx-auto mb-2" />
        <p class="text-sm">暂无团队成员</p>
      </div>
    </div>
  </div>
</template>
