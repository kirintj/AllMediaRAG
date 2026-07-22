<template>
  <div class="login-container">
    <div class="login-card nb-animate-in-scale">
      <!-- Logo / 标题 -->
      <div class="login-header">
        <div class="login-icon">
          <svg width="56" height="56" viewBox="0 0 56 56" fill="none">
            <rect width="56" height="56" rx="16" fill="hsl(var(--nb-brand))"/>
            <path d="M16 20h24M16 28h16M16 36h20" stroke="hsl(var(--primary-foreground))" stroke-width="3" stroke-linecap="round"/>
          </svg>
        </div>
        <h1 class="login-title">AI 知识问答助手</h1>
        <p class="login-subtitle">登录以开始对话</p>
      </div>

      <!-- 登录/注册标签切换 -->
      <div class="login-tabs">
        <button
          class="tab-btn"
          :class="{ active: mode === 'login' }"
          @click="mode = 'login'"
        >
          登录
        </button>
        <button
          v-if="allowRegistration"
          class="tab-btn"
          :class="{ active: mode === 'register' }"
          @click="mode = 'register'"
        >
          注册
        </button>
      </div>

      <!-- 表单 -->
      <form class="login-form" @submit.prevent="handleSubmit">
        <div class="form-field">
          <label class="field-label">用户名</label>
          <input
            v-model="username"
            type="text"
            class="field-input"
            placeholder="请输入用户名"
            autocomplete="username"
            maxlength="32"
          />
        </div>

        <div class="form-field">
          <label class="field-label">密码</label>
          <input
            v-model="password"
            type="password"
            class="field-input"
            :placeholder="mode === 'register' ? '至少 6 位密码' : '请输入密码'"
            autocomplete="current-password"
            maxlength="128"
          />
        </div>

        <!-- 错误提示 -->
        <div v-if="errorMsg" class="error-msg">{{ errorMsg }}</div>

        <!-- 提交按钮 -->
        <button
          type="submit"
          class="submit-btn"
          :disabled="loading || !username || !password"
        >
          <span v-if="loading" class="loading-spinner"></span>
          <span v-else>{{ mode === 'login' ? '登录' : '注册并登录' }}</span>
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAuthStore } from '../../stores/useAuthStore.js'
import { getMe } from '../../api/auth.js'

const emit = defineEmits(['login-success'])
const authStore = useAuthStore()

const mode = ref('login')
const username = ref('')
const password = ref('')
const loading = ref(false)
const errorMsg = ref('')
const allowRegistration = ref(true)

onMounted(async () => {
  // 检查是否已有有效 token
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
    if (err.response?.data?.detail) {
      errorMsg.value = err.response.data.detail
    } else {
      errorMsg.value = '网络错误，请稍后重试'
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: hsl(var(--muted));
}

.login-card {
  width: 380px;
  padding: 4rem 3.25rem;
  box-shadow: var(--nb-shadow-md);
  background: hsl(var(--card));
  border-radius: var(--radius);
}

.login-header {
  text-align: center;
  margin-bottom: 4rem;
}

.login-icon {
  margin-bottom: 1.5rem;
}

.login-title {
  font-size: var(--nb-font-3xl);
  font-weight: 700;
  color: hsl(var(--foreground));
  margin: 0 0 0.75rem;
}

.login-subtitle {
  font-size: var(--nb-font-base);
  color: hsl(var(--muted-foreground));
  margin: 0;
}

.login-tabs {
  display: flex;
  gap: 0.75rem;
  margin-bottom: 3rem;
  background: hsl(var(--muted));
  border-radius: var(--radius);
  padding: 0.5rem;
}

.tab-btn {
  flex: 1;
  padding: 1rem 2rem;
  height: 36px;
  line-height: 20px;
  border: none;
  background: transparent;
  border-radius: var(--radius);
  font-size: var(--nb-font-base);
  font-weight: 500;
  color: hsl(var(--muted-foreground));
  cursor: pointer;
  transition: all 0.2s ease;
}

.tab-btn:hover:not(.active) {
  background: hsl(var(--accent));
  color: hsl(var(--foreground));
}

.tab-btn.active {
  background: hsl(var(--primary));
  color: hsl(var(--primary-foreground));
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.field-label {
  font-size: var(--nb-font-base);
  font-weight: 500;
  color: hsl(var(--foreground));
}

.field-input {
  width: 100%;
  padding: 1rem 1.5rem;
  border: none;
  border-radius: var(--radius);
  font-size: var(--nb-font-lg);
  color: hsl(var(--foreground));
  background: hsl(var(--nb-surface-glass));
  backdrop-filter: blur(8px);
  box-shadow: var(--nb-surface-glass-shadow);
  outline: none;
  transition: box-shadow 0.2s ease;
  box-sizing: border-box;
  height: 40px;
  line-height: 24px;
}

.field-input:focus {
  box-shadow: 0 0 0 2px hsl(var(--nb-brand));
}

.field-input::placeholder {
  color: hsl(var(--muted-foreground));
}

.error-msg {
  font-size: var(--nb-font-sm);
  color: hsl(var(--nb-danger));
  background: hsl(var(--nb-danger-bg));
  padding: 1rem 1.5rem;
  border-radius: var(--radius);
}

.submit-btn {
  width: 100%;
  padding: 1.25rem 0;
  height: 40px;
  border: none;
  border-radius: var(--radius);
  background: hsl(var(--primary));
  color: hsl(var(--primary-foreground));
  font-size: var(--nb-font-lg);
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  margin-top: 0.5rem;
}

.submit-btn:hover:not(:disabled) {
  background: hsl(var(--nb-brand-hover));
}

.submit-btn:active:not(:disabled) {
  background: hsl(var(--nb-brand-pressed));
  transition-duration: 0.08s;
}

.submit-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.loading-spinner {
  width: 18px;
  height: 18px;
  border: 2px solid hsl(var(--primary-foreground) / 0.4);
  border-top-color: hsl(var(--primary-foreground));
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
