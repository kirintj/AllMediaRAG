<template>
  <div class="login-container">
    <div class="login-card">
      <!-- Logo / 标题 -->
      <div class="login-header">
        <div class="login-icon">🤖</div>
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
import { login as apiLogin, register as apiRegister, getMe } from '../api/index.js'

const emit = defineEmits(['login-success'])

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
    let data
    if (mode.value === 'login') {
      data = await apiLogin(username.value, password.value)
    } else {
      data = await apiRegister(username.value, password.value)
    }

    localStorage.setItem('token', data.access_token)
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
  background: var(--hm-bg-primary);
}

.login-card {
  width: 380px;
  padding: 40px 36px;
  background: var(--hm-bg-glass);
  border: 1px solid var(--hm-border-glass);
  border-radius: var(--hm-radius-xl);
  box-shadow: var(--hm-shadow-layered);
  backdrop-filter: blur(20px);
}

.login-header {
  text-align: center;
  margin-bottom: 32px;
}

.login-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.login-title {
  font-size: 22px;
  font-weight: 600;
  color: var(--hm-font-primary);
  margin: 0 0 6px;
}

.login-subtitle {
  font-size: 14px;
  color: var(--hm-font-secondary);
  margin: 0;
}

.login-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 24px;
  background: var(--hm-bg-container-secondary);
  border-radius: var(--hm-radius-sm);
  padding: 4px;
}

.tab-btn {
  flex: 1;
  padding: 8px 0;
  border: none;
  background: transparent;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  color: var(--hm-font-secondary);
  cursor: pointer;
  transition: all 0.2s var(--hm-ease-out);
}

.tab-btn.active {
  background: white;
  color: var(--hm-brand);
  box-shadow: var(--hm-shadow-sm);
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--hm-font-primary);
}

.field-input {
  width: 100%;
  padding: 10px 14px;
  border: 1px solid var(--hm-border);
  border-radius: var(--hm-radius-sm);
  font-size: 14px;
  color: var(--hm-font-primary);
  background: var(--hm-bg-secondary);
  outline: none;
  transition: border-color 0.2s, box-shadow 0.2s;
  box-sizing: border-box;
}

.field-input:focus {
  border-color: var(--hm-brand);
  box-shadow: var(--hm-focus-ring);
}

.field-input::placeholder {
  color: var(--hm-font-tertiary);
}

.error-msg {
  font-size: 13px;
  color: var(--hm-error);
  background: rgba(232, 64, 38, 0.06);
  padding: 8px 12px;
  border-radius: 6px;
}

.submit-btn {
  width: 100%;
  padding: 11px 0;
  border: none;
  border-radius: var(--hm-radius-sm);
  background: var(--hm-brand-gradient);
  color: var(--hm-font-on-brand);
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.2s, box-shadow 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-top: 4px;
}

.submit-btn:hover:not(:disabled) {
  box-shadow: var(--hm-shadow-brand);
}

.submit-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.loading-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
