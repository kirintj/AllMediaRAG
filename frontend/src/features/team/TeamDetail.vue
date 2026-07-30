<template>
  <div class="flex flex-col h-full overflow-hidden">
    <!-- Empty state: no team selected -->
    <div v-if="!navigationStore.selectedTeamId" class="flex-1 flex items-center justify-center text-muted-foreground px-6">
      <div class="text-center">
        <Users class="h-12 w-12 mx-auto mb-3 opacity-30" />
        <p class="text-sm mb-3">请选择一个团队</p>
        <!-- 移动端：点击打开团队列表抽屉 -->
        <button
          class="lg:hidden h-9 px-4 text-sm font-medium bg-primary text-primary-foreground rounded-md hover:bg-primary/90 inline-flex items-center gap-1.5"
          @click="navigationStore.openMobileSidebar()"
        >
          <Users class="h-4 w-4" /> 选择团队
        </button>
      </div>
    </div>

    <template v-else>
      <!-- Header -->
      <div class="flex-shrink-0 h-12 border-b border-border px-3 sm:px-6 flex items-center justify-between gap-2">
        <div class="flex items-center gap-2 min-w-0">
          <!-- 移动端：返回团队列表 -->
          <button
            class="lg:hidden h-8 w-8 flex-shrink-0 flex items-center justify-center rounded-md hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
            @click="navigationStore.openMobileSidebar()"
            title="团队列表"
          >
            <ArrowLeft class="h-4 w-4" />
          </button>
          <h1 class="text-sm font-semibold text-foreground truncate">{{ teamName }}</h1>
          <span class="text-xs text-muted-foreground flex-shrink-0 hidden sm:inline">
            {{ ROLE_LABELS[navigationStore.selectedTeamRole] || navigationStore.selectedTeamRole }}
            · {{ members.length }} 人
          </span>
        </div>
        <span v-if="navigationStore.selectedTeamRole === 'owner'"
              class="text-xs px-2 py-0.5 bg-primary/10 text-primary rounded-md font-medium flex-shrink-0">
          管理员
        </span>
      </div>

      <!-- Content -->
      <div class="flex-1 overflow-y-auto min-h-0">
        <div class="max-w-3xl mx-auto px-3 py-4 sm:px-6 sm:py-6 space-y-5 sm:space-y-6">

          <!-- Invite section (owner only) -->
          <div v-if="navigationStore.selectedTeamRole === 'owner'" class="space-y-2">
            <h2 class="text-sm font-semibold text-foreground flex items-center gap-1.5">
              <UserPlus class="h-4 w-4" /> 邀请成员
            </h2>
            <div class="flex gap-2">
              <input v-model="inviteUsername" @keyup.enter="handleInvite"
                     placeholder="输入用户名..."
                     class="flex-1 h-10 px-3 text-sm rounded-md bg-muted border-0 outline-none focus:ring-1 focus:ring-ring placeholder:text-muted-foreground min-w-0" />
              <button @click="handleInvite"
                      class="h-10 px-3 sm:px-4 text-sm font-medium bg-blue-500 text-white rounded-md hover:bg-blue-600 flex items-center gap-1.5 flex-shrink-0">
                <UserPlus class="h-4 w-4" />
                <span class="hidden sm:inline">发送邀请</span>
                <span class="sm:hidden">邀请</span>
              </button>
            </div>
          </div>

          <!-- Members list -->
          <div class="space-y-3">
            <h2 class="text-sm font-semibold text-foreground">团队成员</h2>

            <!-- 桌面端：表格布局 -->
            <div class="hidden sm:block rounded-lg border border-border overflow-hidden">
              <!-- Table header -->
              <div class="flex items-center px-4 py-2.5 bg-muted/50 border-b border-border text-xs font-medium text-muted-foreground">
                <div class="flex-1">成员</div>
                <div class="w-24 text-center">角色</div>
                <div class="w-24 text-center">状态</div>
                <div v-if="navigationStore.selectedTeamRole === 'owner'" class="w-20 text-center">操作</div>
              </div>

              <!-- Member rows -->
              <div v-for="member in members" :key="member.user_id"
                   class="flex items-center px-4 py-3 border-b border-border last:border-0 hover:bg-accent/30 transition-colors">
                <!-- Username + avatar -->
                <div class="flex-1 flex items-center gap-3 min-w-0">
                  <div class="w-8 h-8 rounded-full bg-muted flex items-center justify-center text-sm font-medium flex-shrink-0">
                    {{ member.username?.[0]?.toUpperCase() || '?' }}
                  </div>
                  <span class="text-sm font-medium truncate">{{ member.username }}</span>
                </div>

                <!-- Role -->
                <div class="w-24 text-center">
                  <select v-if="navigationStore.selectedTeamRole === 'owner' && member.role !== 'owner' && member.status === 'active'"
                          :value="member.role"
                          @change="handleRoleChange(member.user_id, $event.target.value)"
                          class="text-xs h-7 px-1.5 rounded-md bg-muted border-0 outline-none focus:ring-1 focus:ring-ring cursor-pointer">
                    <option value="normal">成员</option>
                    <option value="owner">管理员</option>
                  </select>
                  <span v-else class="text-xs text-muted-foreground">
                    {{ ROLE_LABELS[member.role] || member.role }}
                  </span>
                </div>

                <!-- Status -->
                <div class="w-24 text-center">
                  <span v-if="member.status === 'active'"
                        class="inline-flex items-center gap-1 text-xs text-green-600">
                    <span class="h-1.5 w-1.5 rounded-full bg-green-500"></span> 已加入
                  </span>
                  <span v-else
                        class="inline-flex items-center gap-1 text-xs text-yellow-600">
                    <span class="h-1.5 w-1.5 rounded-full bg-yellow-500"></span> 待确认
                  </span>
                </div>

                <!-- Actions -->
                <div v-if="navigationStore.selectedTeamRole === 'owner'" class="w-20 text-center">
                  <button v-if="member.role !== 'owner'"
                          @click="handleRemove(member.user_id, member.username, member.status)"
                          class="h-7 px-2 text-xs text-destructive hover:bg-destructive/10 rounded-md transition-colors"
                          :title="member.status === 'pending' ? '撤销邀请' : '移除成员'">
                    {{ member.status === 'pending' ? '撤销' : '移除' }}
                  </button>
                  <span v-else class="text-xs text-muted-foreground">—</span>
                </div>
              </div>

              <!-- Empty -->
              <div v-if="members.length === 0" class="px-4 py-8 text-center text-sm text-muted-foreground">
                暂无成员
              </div>
            </div>

            <!-- 移动端：卡片布局 -->
            <div class="sm:hidden space-y-2">
              <div v-for="member in members" :key="member.user_id"
                   class="rounded-lg border border-border p-3 space-y-2">
                <!-- 顶部：头像 + 用户名 + 状态 -->
                <div class="flex items-center gap-3">
                  <div class="w-9 h-9 rounded-full bg-muted flex items-center justify-center text-sm font-medium flex-shrink-0">
                    {{ member.username?.[0]?.toUpperCase() || '?' }}
                  </div>
                  <div class="flex-1 min-w-0">
                    <div class="flex items-center gap-2">
                      <span class="text-sm font-medium truncate">{{ member.username }}</span>
                      <span v-if="member.status === 'active'"
                            class="inline-flex items-center gap-1 text-[11px] text-green-600 flex-shrink-0">
                        <span class="h-1.5 w-1.5 rounded-full bg-green-500"></span>已加入
                      </span>
                      <span v-else
                            class="inline-flex items-center gap-1 text-[11px] text-yellow-600 flex-shrink-0">
                        <span class="h-1.5 w-1.5 rounded-full bg-yellow-500"></span>待确认
                      </span>
                    </div>
                    <div class="text-xs text-muted-foreground mt-0.5">
                      {{ ROLE_LABELS[member.role] || member.role }}
                    </div>
                  </div>
                </div>
                <!-- 底部：操作区（owner 且非 owner 成员） -->
                <div v-if="navigationStore.selectedTeamRole === 'owner' && member.role !== 'owner' && member.status === 'active'"
                     class="flex items-center justify-between gap-2 pt-2 border-t border-border">
                  <select
                    :value="member.role"
                    @change="handleRoleChange(member.user_id, $event.target.value)"
                    class="flex-1 text-xs h-8 px-2 rounded-md bg-muted border-0 outline-none focus:ring-1 focus:ring-ring cursor-pointer">
                    <option value="normal">成员</option>
                    <option value="owner">管理员</option>
                  </select>
                  <button
                    @click="handleRemove(member.user_id, member.username, member.status)"
                    class="h-8 px-3 text-xs text-destructive hover:bg-destructive/10 rounded-md transition-colors flex-shrink-0"
                    :title="member.status === 'pending' ? '撤销邀请' : '移除成员'">
                    {{ member.status === 'pending' ? '撤销' : '移除' }}
                  </button>
                </div>
                <div v-else-if="navigationStore.selectedTeamRole === 'owner' && member.role !== 'owner' && member.status === 'pending'"
                     class="flex justify-end pt-2 border-t border-border">
                  <button
                    @click="handleRemove(member.user_id, member.username, member.status)"
                    class="h-8 px-3 text-xs text-destructive hover:bg-destructive/10 rounded-md transition-colors">
                    撤销邀请
                  </button>
                </div>
              </div>

              <!-- Empty -->
              <div v-if="members.length === 0" class="py-8 text-center text-sm text-muted-foreground">
                暂无成员
              </div>
            </div>
          </div>

        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { Users, UserPlus, ArrowLeft } from 'lucide-vue-next'
import { useNavigationStore } from '../../stores/useNavigationStore.js'
import { useToastStore } from '../../stores/useToastStore.js'
import { useConfirmStore } from '../../stores/useConfirmStore.js'
import {
  listMembers, listTeams, inviteMember, removeMember, updateMemberRole,
} from '../../api/team.js'

const navigationStore = useNavigationStore()
const toast = useToastStore()
const confirmStore = useConfirmStore()

const members = ref([])
const teamName = ref('')
const inviteUsername = ref('')

const ROLE_LABELS = { owner: '管理员', normal: '成员' }

async function fetchDetail() {
  if (!navigationStore.selectedTeamId) {
    members.value = []
    teamName.value = ''
    return
  }
  try {
    // Fetch members + team name in parallel
    const [membersData, teamsData] = await Promise.all([
      listMembers(navigationStore.selectedTeamId),
      listTeams(),
    ])
    members.value = membersData.members || []
    const team = (teamsData.teams || []).find(t => t.tenant_id === navigationStore.selectedTeamId)
    teamName.value = team?.name || '未知团队'
  } catch (err) {
    toast.error('加载团队信息失败: ' + (err.response?.data?.detail || err.message))
  }
}

async function handleInvite() {
  if (!inviteUsername.value.trim()) return
  try {
    const res = await inviteMember(navigationStore.selectedTeamId, inviteUsername.value.trim())
    toast.success(res.message)
    inviteUsername.value = ''
    await fetchDetail()
  } catch (err) {
    toast.error('邀请失败: ' + (err.response?.data?.detail || err.message))
  }
}

async function handleRoleChange(userId, newRole) {
  try {
    await updateMemberRole(navigationStore.selectedTeamId, userId, newRole)
    toast.success('角色已更新')
    await fetchDetail()
  } catch (err) {
    toast.error('更新角色失败: ' + (err.response?.data?.detail || err.message))
  }
}

async function handleRemove(userId, username, status) {
  const label = status === 'pending' ? '撤销邀请' : '移除成员'
  if (!await confirmStore.confirm({ message: `确定${label} ${username}？`, destructive: true })) return
  try {
    await removeMember(navigationStore.selectedTeamId, userId)
    toast.success(`${label}成功`)
    await fetchDetail()
  } catch (err) {
    toast.error('操作失败: ' + (err.response?.data?.detail || err.message))
  }
}

// Re-fetch when selected team changes
watch(() => navigationStore.selectedTeamId, () => fetchDetail())

onMounted(() => fetchDetail())
</script>
