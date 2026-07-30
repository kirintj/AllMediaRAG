<template>
  <div class="flex flex-col h-full">
    <!-- Header -->
    <div class="flex items-center justify-between pl-4 pr-10 lg:px-4 h-12 border-b border-border flex-shrink-0">
      <h3 class="text-sm font-semibold text-foreground">团队</h3>
      <div class="flex items-center gap-1.5 sm:gap-2">
        <button
          v-if="pendingCount > 0"
          class="relative h-9 w-9 flex items-center justify-center rounded-md hover:bg-accent text-yellow-500 hover:text-yellow-600 transition-colors"
          @click="showInvitations = !showInvitations"
          title="待处理邀请"
        >
          <Mail class="h-4 w-4" />
          <span class="absolute -top-0.5 -right-0.5 h-4 min-w-4 px-0.5 text-[10px] font-bold leading-4 text-center bg-yellow-500 text-white rounded-full">
            {{ pendingCount }}
          </span>
        </button>
        <button
          class="h-9 w-9 flex items-center justify-center rounded-md hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
          @click="showCreateTeam = !showCreateTeam"
          title="新建团队"
        >
          <Plus class="h-4 w-4" />
        </button>
      </div>
    </div>

    <!-- Invitations (collapsible) -->
    <div v-if="showInvitations && pendingCount > 0" class="flex-shrink-0 border-b border-border bg-yellow-50/50 dark:bg-yellow-900/10">
      <div class="px-3 py-2 space-y-1.5">
        <div v-for="inv in invitations" :key="inv.id"
             class="flex items-center justify-between p-2 rounded-md bg-background border">
          <div class="text-xs min-w-0 flex-1 mr-2">
            <span class="font-medium">{{ inv.invited_by || '未知' }}</span>
            <span class="text-muted-foreground"> 邀请您加入 </span>
            <span class="font-medium">{{ inv.tenant_name }}</span>
          </div>
          <div class="flex items-center gap-1 flex-shrink-0">
            <button @click="handleAccept(inv.id)"
                    class="h-6 px-1.5 text-[11px] font-medium bg-green-500 text-white rounded hover:bg-green-600 flex items-center gap-0.5">
              <Check class="h-3 w-3" /> 接受
            </button>
            <button @click="handleReject(inv.id)"
                    class="h-6 px-1.5 text-[11px] font-medium bg-red-500 text-white rounded hover:bg-red-600 flex items-center gap-0.5">
              <XCircle class="h-3 w-3" /> 拒绝
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Create team form (collapsible) -->
    <div v-if="showCreateTeam" class="flex-shrink-0 border-b border-border px-3 py-2">
      <div class="flex gap-1.5">
        <input v-model="newTeamName" @keyup.enter="handleCreateTeam"
               placeholder="团队名称..."
               class="flex-1 h-8 px-2.5 text-sm rounded-md bg-muted border-0 outline-none focus:ring-1 focus:ring-ring placeholder:text-muted-foreground" />
        <button @click="handleCreateTeam"
                class="h-8 px-3 text-xs font-medium bg-primary text-primary-foreground rounded-md hover:bg-primary/90">
          创建
        </button>
      </div>
    </div>

    <!-- Team list -->
    <div class="flex-1 overflow-y-auto min-h-0">
      <div v-for="team in teams" :key="team.tenant_id" class="px-1.5 py-0.5">
        <button
          class="w-full flex items-center justify-between px-2.5 py-2 rounded-md text-left hover:bg-accent transition-colors"
          :class="navigationStore.selectedTeamId === team.tenant_id ? 'bg-accent' : ''"
          @click="handleSelectTeam(team)">
          <div class="min-w-0 flex-1">
            <div class="text-sm font-medium truncate">{{ team.name }}</div>
            <div class="text-[11px] text-muted-foreground">
              {{ ROLE_LABELS[team.role] || team.role }} · {{ team.member_count }} 人
            </div>
          </div>
          <span v-if="team.role === 'owner'"
                class="text-[10px] px-1.5 py-0.5 bg-primary/10 text-primary rounded font-medium flex-shrink-0 ml-2">
            管理员
          </span>
        </button>
      </div>

      <div v-if="!loading && teams.length === 0" class="text-center py-8 text-muted-foreground">
        <Users class="h-8 w-8 mx-auto mb-2 opacity-40" />
        <p class="text-xs">暂无团队，点击上方按钮新建</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { Users, Plus, Mail, Check, XCircle } from 'lucide-vue-next'
import { useNavigationStore } from '../../../stores/useNavigationStore.js'
import { useToastStore } from '../../../stores/useToastStore.js'
import { useConfirmStore } from '../../../stores/useConfirmStore.js'
import {
  listTeams, createTeam, listInvitations, acceptInvitation, rejectInvitation,
} from '../../../api/team.js'

const navigationStore = useNavigationStore()
const toast = useToastStore()
const confirmStore = useConfirmStore()

const teams = ref([])
const invitations = ref([])
const newTeamName = ref('')
const loading = ref(false)
const showCreateTeam = ref(false)
const showInvitations = ref(false)

const pendingCount = computed(() => invitations.value.length)
const ROLE_LABELS = { owner: '管理员', normal: '成员' }

function handleSelectTeam(team) {
  navigationStore.selectTeam(team.tenant_id, team.role)
  // 移动端选择团队后关闭侧栏抽屉，显示详情
  navigationStore.closeMobileSidebar()
}

async function fetchAll() {
  loading.value = true
  try {
    const [teamsData, invitationsData] = await Promise.all([listTeams(), listInvitations()])
    teams.value = teamsData.teams || []
    invitations.value = invitationsData.invitations || []

    // Auto-select first team if none selected or selected no longer exists
    const exists = teams.value.some(t => t.tenant_id === navigationStore.selectedTeamId)
    if (!exists && teams.value.length > 0) {
      navigationStore.selectTeam(teams.value[0].tenant_id, teams.value[0].role)
    } else if (!exists) {
      navigationStore.selectTeam(null, null)
    } else if (exists) {
      // Keep selection, just update role
      const t = teams.value.find(t => t.tenant_id === navigationStore.selectedTeamId)
      navigationStore.selectTeam(t.tenant_id, t.role)
    }
  } finally {
    loading.value = false
  }
}

async function handleCreateTeam() {
  if (!newTeamName.value.trim()) return
  try {
    const res = await createTeam(newTeamName.value.trim())
    toast.success(res.message)
    newTeamName.value = ''
    showCreateTeam.value = false
    await fetchAll()
  } catch (err) {
    toast.error('创建失败: ' + (err.response?.data?.detail || err.message))
  }
}

async function handleAccept(id) {
  try {
    const res = await acceptInvitation(id)
    toast.success(res.message)
    await fetchAll()
  } catch (err) {
    toast.error('接受失败: ' + (err.response?.data?.detail || err.message))
  }
}

async function handleReject(id) {
  if (!await confirmStore.confirm({ message: '确定拒绝此邀请？', destructive: true })) return
  try {
    const res = await rejectInvitation(id)
    toast.success(res.message)
    await fetchAll()
  } catch (err) {
    toast.error('拒绝失败: ' + (err.response?.data?.detail || err.message))
  }
}

onMounted(() => fetchAll())
</script>
