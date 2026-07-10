<template>
  <!-- 未认证：显示登录页 -->
  <LoginView v-if="!authStore.isAuthenticated" @login-success="onLoginSuccess" />

  <!-- 已认证：显示主界面 -->
  <div v-else class="app-container">
    <el-container class="app-layout">
      <!-- 左侧栏 -->
      <el-aside :width="'260px'" class="sidebar harmony-animate-in">
        <ChatSidebar />
      </el-aside>

      <!-- 中间对话区 -->
      <el-main class="main-content">
        <ChatView
          :is-dark="isDark"
          @open-docs="showDocs = true"
          @toggle-dashboard="showDashboard = true"
          @toggle-dark="toggleDark"
          @logout="handleLogout"
        />
      </el-main>

    </el-container>

    <!-- 评测仪表盘对话框 -->
    <EvalDashboard v-model="showDashboard" />

    <!-- Toast 容器 -->
    <div class="toast-container">
      <div
        v-for="toast in toastStore.toasts"
        :key="toast.id"
        class="toast-item"
        :class="toast.type"
      >
        {{ toast.msg }}
      </div>
    </div>

    <!-- 文档抽屉 -->
    <DocumentDrawer v-model="showDocs" />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useAuthStore } from './stores/useAuthStore.js'
import { useToastStore } from './stores/useToastStore.js'
import ChatSidebar from './features/chat/ChatSidebar.vue'
import ChatView from './features/chat/ChatView.vue'
import DocumentDrawer from './features/documents/DocumentDrawer.vue'
import LoginView from './features/auth/LoginView.vue'
import EvalDashboard from './features/eval/EvalDashboard.vue'

const authStore = useAuthStore()
const toastStore = useToastStore()
const isDark = ref(false)
const showDashboard = ref(false)
const showDocs = ref(false)

function toggleDark() {
  isDark.value = !isDark.value
  document.documentElement.setAttribute('data-theme', isDark.value ? 'dark' : 'light')
}

function onLoginSuccess() {
  // auth state is already updated by the store's login/register methods
}

function handleLogout() {
  authStore.logout()
}

function onAuthExpired() {
  authStore.onAuthExpired()
}

onMounted(async () => {
  // 检查是否有有效 token
  await authStore.checkAuth()

  // 监听 401 过期事件
  window.addEventListener('auth-expired', onAuthExpired)
})

onUnmounted(() => {
  window.removeEventListener('auth-expired', onAuthExpired)
})
</script>

<style scoped>
.app-container {
  height: 100vh;
  position: relative;
}

.app-layout {
  height: 100%;
}

.sidebar {
  background: var(--harmony-comp-background-primary);
  border-right: 1px solid var(--harmony-comp-divider);
  box-shadow: 1px 0 0 var(--harmony-comp-divider);
  overflow-y: auto;
}

.main-content {
  display: flex;
  flex-direction: column;
  padding: 0;
  overflow: hidden;
  background: var(--harmony-background-secondary);
}

/* ── Toast 容器 ── */
.toast-container {
  position: fixed;
  top: calc(var(--harmony-titlebar-height) + var(--harmony-padding-level4));
  right: var(--harmony-padding-level8);
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: var(--harmony-padding-level4);
}

.toast-item {
  padding: var(--harmony-padding-level5) var(--harmony-padding-level10);
  border-radius: var(--harmony-corner-radius-level8);
  font-size: var(--harmony-font-size-caption-l);
  font-weight: var(--harmony-font-weight-subtitle-m);
  box-shadow: var(--harmony-shadow-md);
  animation: toast-in 0.3s var(--harmony-ease-out);
}

.toast-item.success {
  background: var(--harmony-confirm-light);
  color: var(--harmony-confirm);
  border: 1px solid var(--harmony-confirm-border);
}

.toast-item.error {
  background: var(--harmony-warning-light);
  color: var(--harmony-warning);
  border: 1px solid var(--harmony-warning-border);
}

.toast-item.warning {
  background: var(--harmony-alert-light);
  color: var(--harmony-alert);
  border: 1px solid var(--harmony-alert-border);
}

.toast-item.info {
  background: var(--harmony-comp-background-tertiary);
  color: var(--harmony-font-secondary);
  border: 1px solid var(--harmony-comp-divider);
}

@keyframes toast-in {
  from {
    opacity: 0;
    transform: translateX(30px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}
</style>
