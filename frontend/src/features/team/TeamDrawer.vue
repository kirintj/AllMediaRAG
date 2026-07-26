<script setup>
import { ref, onMounted } from 'vue'
import { useToastStore } from '../../stores/useToastStore.js'
import { useConfirmStore } from '../../stores/useConfirmStore.js'
import { X, UserPlus, Trash2, Users, Shield } from 'lucide-vue-next'
import { listMembers, inviteMember, removeMember } from '../../api/team.js'

const props = defineProps({ open: Boolean })
const emit = defineEmits(['close'])

const toast = useToastStore()
const confirmStore = useConfirmStore()
const members = ref([])
const inviteUsername = ref('')
const loading = ref(false)

const ROLE_LABELS = { owner: '管理员', normal: '成员' }

async function fetchMembers() {
  loading.value = true
  try {
    const data = await listMembers()
    members.value = data.members || []
  } finally {
    loading.value = false
  }
}

async function handleInvite() {
  if (!inviteUsername.value.trim()) return
  try {
    await inviteMember(inviteUsername.value)
    toast.success(`已邀请 ${inviteUsername.value}`)
    inviteUsername.value = ''
    await fetchMembers()
  } catch (err) {
    toast.error('邀请失败: ' + (err.response?.data?.detail || err.message))
  }
}

async function handleRemove(userId, username) {
  if (!await confirmStore.confirm({ message: `确定移除成员 ${username}？`, destructive: true })) return
  try {
    await removeMember(userId)
    toast.success('成员已移除')
    await fetchMembers()
  } catch (err) {
    toast.error('移除失败: ' + (err.response?.data?.detail || err.message))
  }
}

onMounted(() => fetchMembers())
</script>

<template>
  <div v-if="open" class="fixed inset-0 z-50 flex justify-end">
    <div class="absolute inset-0 bg-black/30" @click="emit('close')"></div>
    <div class="relative w-[400px] bg-white dark:bg-gray-900 shadow-xl flex flex-col h-full">
      <!-- Header -->
      <div class="flex items-center justify-between p-4 border-b">
        <div class="flex items-center gap-2">
          <Users class="h-5 w-5" />
          <h2 class="text-lg font-semibold">团队管理</h2>
        </div>
        <button @click="emit('close')" class="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded">
          <X class="h-5 w-5" />
        </button>
      </div>

      <div class="flex-1 overflow-y-auto p-4 space-y-4">
        <!-- Invite form -->
        <div class="flex gap-2">
          <input v-model="inviteUsername" @keyup.enter="handleInvite"
                 placeholder="输入用户名邀请成员..." class="flex-1 px-3 py-2 border rounded text-sm bg-transparent" />
          <button @click="handleInvite" class="px-3 py-2 bg-blue-500 text-white rounded text-sm hover:bg-blue-600 flex items-center gap-1">
            <UserPlus class="h-4 w-4" /> 邀请
          </button>
        </div>

        <!-- Members list -->
        <div class="space-y-2">
          <div v-for="member in members" :key="member.user_id"
               class="flex items-center justify-between p-3 border rounded-lg">
            <div class="flex items-center gap-3">
              <div class="w-8 h-8 rounded-full bg-gray-200 dark:bg-gray-700 flex items-center justify-center text-sm font-medium">
                {{ member.username?.[0]?.toUpperCase() || '?' }}
              </div>
              <div>
                <div class="text-sm font-medium">{{ member.username }}</div>
                <div class="flex items-center gap-1 text-xs text-gray-400">
                  <Shield class="h-3 w-3" />
                  {{ ROLE_LABELS[member.role] || member.role }}
                  <span v-if="member.status === 'pending'" class="text-yellow-600 ml-1">(待接受)</span>
                </div>
              </div>
            </div>
            <button v-if="member.role !== 'owner'"
                    @click="handleRemove(member.user_id, member.username)"
                    class="p-1.5 hover:bg-red-50 dark:hover:bg-red-900/20 rounded">
              <Trash2 class="h-4 w-4 text-gray-400 hover:text-red-500" />
            </button>
          </div>
        </div>

        <div v-if="!loading && members.length === 0" class="text-center py-8 text-gray-400">
          <Users class="h-8 w-8 mx-auto mb-2" />
          <p class="text-sm">暂无团队成员</p>
        </div>
      </div>
    </div>
  </div>
</template>
