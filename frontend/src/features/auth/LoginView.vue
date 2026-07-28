<template>
  <div class="min-h-screen h-screen flex items-center justify-center bg-muted px-4 py-6 overflow-y-auto">
    <div class="w-full max-w-[380px] p-6 sm:p-10 bg-card rounded-lg shadow-lg border border-border animate-in fade-in-0 zoom-in-95 duration-300 my-auto">
      <!-- Header -->
      <div class="text-center mb-6 sm:mb-8 lg:mb-10">
        <div class="inline-flex items-center justify-center w-12 h-12 sm:w-14 sm:h-14 rounded-2xl bg-primary mb-3 sm:mb-4">
          <Sparkles class="h-6 w-6 sm:h-7 sm:w-7 text-primary-foreground" />
        </div>
        <h1 class="text-lg sm:text-xl font-bold text-foreground mb-1">AI 知识问答助手</h1>
        <p class="text-sm text-muted-foreground">登录以开始对话</p>
      </div>

      <!-- Tab toggle -->
      <div class="flex gap-1 bg-muted rounded-lg p-1 mb-5 sm:mb-6 lg:mb-8">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          class="flex-1 h-9 rounded-md text-sm font-medium transition-colors"
          :class="mode === tab.key
            ? 'bg-primary text-primary-foreground shadow-sm'
            : 'text-muted-foreground hover:text-foreground hover:bg-accent'"
          @click="mode = tab.key"
        >
          {{ tab.label }}
        </button>
      </div>

      <!-- Form -->
      <form class="flex flex-col gap-4 sm:gap-5" @submit.prevent="handleSubmit">
        <div class="flex flex-col gap-1.5">
          <label class="text-sm font-medium text-foreground">用户名</label>
          <input
            v-model="username"
            type="text"
            class="h-11 w-full rounded-md border border-input bg-transparent px-3 py-1 text-base sm:text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            placeholder="请输入用户名"
            autocomplete="username"
            maxlength="32"
          />
        </div>

        <div class="flex flex-col gap-1.5">
          <label class="text-sm font-medium text-foreground">密码</label>
          <input
            v-model="password"
            type="password"
            class="h-11 w-full rounded-md border border-input bg-transparent px-3 py-1 text-base sm:text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            :placeholder="mode === 'register' ? '至少 6 位密码' : '请输入密码'"
            autocomplete="current-password"
            maxlength="128"
          />
        </div>

        <!-- Error -->
        <div v-if="errorMsg" class="px-3 py-2 rounded-md bg-destructive/10 text-destructive text-sm">
          {{ errorMsg }}
        </div>

        <!-- Submit -->
        <button
          type="submit"
          class="w-full h-11 rounded-md bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          :disabled="loading || !username || !password"
        >
          <Loader2 v-if="loading" class="h-4 w-4 animate-spin" />
          <span v-else>{{ mode === 'login' ? '登录' : '注册并登录' }}</span>
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { Loader2, Sparkles } from 'lucide-vue-next'
import { useAuthStore } from '../../stores/useAuthStore.js'
import { getMe } from '../../api/auth.js'

const emit = defineEmits(['login-success'])
const authStore = useAuthStore()

const mode = ref('login')
const username = ref('')
const password = ref('')
const loading = ref(false)
const errorMsg = ref('')

const tabs = [
  { key: 'login', label: '登录' },
  { key: 'register', label: '注册' },
]

onMounted(async () => {
  const token = localStorage.getItem('token')
  if (token) {
    try {
      await getMe()
      emit('login-success')
    } catch {
      localStorage.removeItem('token')
    }
  }
})

async function handleSubmit() {
  if (!username.value || !password.value) return
  loading.value = true
  errorMsg.value = ''
  try {
    if (mode.value === 'login') {
      await authStore.login(username.value, password.value)
    } else {
      await authStore.register(username.value, password.value)
    }
    emit('login-success')
  } catch (err) {
    errorMsg.value = err.response?.data?.detail || '网络错误，请稍后重试'
  } finally {
    loading.value = false
  }
}
</script>
