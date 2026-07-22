<template>
  <!-- 未认证：显示登录页 -->
  <LoginView v-if="!authStore.isAuthenticated" @login-success="onLoginSuccess" />

  <!-- 已认证：显示主界面 -->
  <div v-else class="app-container">
    <div class="app-layout">
      <!-- 左侧栏 -->
      <aside class="sidebar sidebar-glass">
        <ChatSidebar />
      </aside>

      <!-- 中间对话区 -->
      <main class="main-content">
        <ChatView
          :is-dark="isDark"
          @open-docs="showDocs = true"
          @toggle-dashboard="showDashboard = true"
          @toggle-dark="toggleDark"
          @logout="handleLogout"
        />
      </main>

    </div>

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
  document.documentElement.classList.toggle('dark', isDark.value)
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
  display: flex;
  height: 100%;
}

.sidebar {
  width: 272px;
  flex-shrink: 0;
  overflow-y: auto;
  border-right: 1px solid hsl(var(--border));
}

.main-content {
  display: flex;
  flex-direction: column;
  flex: 1;
  padding: 0;
  overflow: hidden;
  background: hsl(var(--background));
}

/* ── Toast 容器 ── */
.toast-container {
  position: fixed;
  top: var(--nb-space-8);
  right: var(--nb-space-8);
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: var(--nb-space-2);
}

.toast-item {
  padding: var(--nb-space-3) var(--nb-space-5);
  border-radius: var(--radius);
  font-size: var(--nb-font-sm);
  font-weight: 500;
  box-shadow: var(--nb-shadow-md);
  animation: nb-fade-in-up 0.3s ease;
}

.toast-item.success {
  background: hsl(var(--nb-success-bg));
  color: hsl(var(--nb-success));
  border: 1px solid hsl(var(--nb-success) / 0.2);
}

.toast-item.error {
  background: hsl(var(--nb-danger-bg));
  color: hsl(var(--nb-danger));
  border: 1px solid hsl(var(--nb-danger) / 0.2);
}

.toast-item.warning {
  background: hsl(var(--nb-warning-bg));
  color: hsl(var(--nb-warning));
  border: 1px solid hsl(var(--nb-warning) / 0.2);
}

.toast-item.info {
  background: hsl(var(--muted));
  color: hsl(var(--muted-foreground));
  border: 1px solid hsl(var(--border));
}

@media (max-width: 1024px) {
  .sidebar { display: none; }
}
</style>
