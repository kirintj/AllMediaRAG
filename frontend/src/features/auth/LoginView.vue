<template>
  <div class="login-container">
    <div class="login-card harmony-animate-in-scale">
      <!-- Logo / 标题 -->
      <div class="login-header">
        <div class="login-icon">
          <svg width="56" height="56" viewBox="0 0 56 56" fill="none">
            <rect width="56" height="56" rx="16" fill="var(--harmony-brand)"/>
            <path d="M16 20h24M16 28h16M16 36h20" stroke="var(--harmony-font-on-primary)" stroke-width="3" stroke-linecap="round"/>
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
  background: var(--harmony-background-tertiary);
}

.login-card {
  width: 380px;
  padding: var(--harmony-padding-level16) var(--harmony-padding-level13);
  box-shadow: var(--harmony-shadow-md);
  background: var(--harmony-comp-background-primary);
  border-radius: var(--harmony-corner-radius-level10);
}

.login-header {
  text-align: center;
  margin-bottom: var(--harmony-padding-level16);
}

.login-icon {
  margin-bottom: var(--harmony-padding-level6);
}

.login-title {
  font-size: var(--harmony-font-size-title-m);
  font-weight: var(--harmony-font-weight-title-m);
  color: var(--harmony-font-primary);
  margin: 0 0 var(--harmony-padding-level3);
}

.login-subtitle {
  font-size: var(--harmony-font-size-body-m);
  color: var(--harmony-font-secondary);
  margin: 0;
}

.login-tabs {
  display: flex;
  gap: var(--harmony-padding-level3);
  margin-bottom: var(--harmony-padding-level12);
  background: var(--harmony-comp-background-secondary);
  border-radius: var(--harmony-corner-radius-level10);
  padding: var(--harmony-padding-level2);
}

.tab-btn {
  flex: 1;
  padding: var(--harmony-padding-level4) var(--harmony-padding-level8);
  height: var(--harmony-control-height-36);
  line-height: 20px;
  border: none;
  background: transparent;
  border-radius: var(--harmony-corner-radius-level10);
  font-size: var(--harmony-font-size-body-m);
  font-weight: var(--harmony-font-weight-subtitle-m);
  color: var(--harmony-font-secondary);
  cursor: pointer;
  transition: all 0.2s var(--harmony-ease-out);
}

.tab-btn:hover:not(.active) {
  background: var(--harmony-interactive-hover);
  color: var(--harmony-font-primary);
}

.tab-btn.active {
  background: var(--harmony-comp-background-emphasize);
  color: var(--harmony-font-on-primary);
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: var(--harmony-padding-level8);
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: var(--harmony-padding-level3);
}

.field-label {
  font-size: var(--harmony-font-size-body-m);
  font-weight: var(--harmony-font-weight-subtitle-s);
  color: var(--harmony-font-primary);
}

.field-input {
  width: 100%;
  padding: var(--harmony-padding-level4) var(--harmony-padding-level6);
  border: none;
  border-radius: var(--harmony-corner-radius-level12);
  font-size: var(--harmony-font-size-body-l);
  color: var(--harmony-font-primary);
  background: var(--harmony-input-glass-bg);
  backdrop-filter: blur(8px);
  box-shadow: var(--harmony-input-glass-shadow);
  outline: none;
  transition: box-shadow 0.2s var(--harmony-ease-out);
  box-sizing: border-box;
  height: 40px;
  line-height: 24px;
}

.field-input:focus {
  box-shadow: 0 0 0 2px var(--harmony-brand);
}

.field-input::placeholder {
  color: var(--harmony-font-secondary);
}

.error-msg {
  font-size: var(--harmony-font-size-body-s);
  color: var(--harmony-warning);
  background: var(--harmony-warning-subtle);
  padding: var(--harmony-padding-level4) var(--harmony-padding-level6);
  border-radius: var(--harmony-corner-radius-level4);
}

.submit-btn {
  width: 100%;
  padding: var(--harmony-padding-level5) 0;
  height: 40px;
  border: none;
  border-radius: var(--harmony-corner-radius-level10);
  background: var(--harmony-comp-background-emphasize);
  color: var(--harmony-font-on-primary);
  font-size: var(--harmony-font-size-subtitle-m);
  font-weight: var(--harmony-font-weight-subtitle-m);
  cursor: pointer;
  transition: background 0.2s var(--harmony-ease-out);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--harmony-padding-level4);
  margin-top: var(--harmony-padding-level2);
}

.submit-btn:hover:not(:disabled) {
  background: var(--harmony-brand-hover);
}

.submit-btn:active:not(:disabled) {
  background: var(--harmony-brand-pressed);
  transition-duration: 0.08s;
}

.submit-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.loading-spinner {
  width: 18px;
  height: 18px;
  border: 2px solid var(--harmony-font-on-tertiary);
  border-top-color: var(--harmony-font-on-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
