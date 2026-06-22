<template>
  <!-- 未认证：显示登录页 -->
  <LoginView v-if="!authStore.isAuthenticated" @login-success="onLoginSuccess" />

  <!-- 已认证：显示主界面 -->
  <div v-else class="app-container" :class="{ dark: isDark }">
    <el-container class="app-layout">
      <!-- 左侧栏 -->
      <el-aside :width="isDark ? '260px' : '260px'" class="sidebar hm-animate-in">
        <ChatSidebar />
      </el-aside>

      <!-- 中间对话区 -->
      <el-main class="main-content">
        <ChatView />
      </el-main>

      <!-- 右侧栏 -->
      <el-aside width="280px" class="docs-panel hm-animate-in" style="animation-delay: 0.1s">
        <DocumentPanel />
      </el-aside>
    </el-container>

    <!-- 工具栏：深色模式 + 仪表盘 + 退出登录 -->
    <div class="toolbar">
      <button class="dashboard-btn hm-icon-btn" @click="showDashboard = true" title="评测与性能">
        <span style="font-size: 16px">&#128202;</span>
      </button>
      <button class="dark-toggle hm-icon-btn" @click="toggleDark" :title="isDark ? '切换浅色模式' : '切换深色模式'">
        <span v-if="isDark" style="font-size: 18px">&#9728;&#65039;</span>
        <span v-else style="font-size: 18px">&#127769;</span>
      </button>
      <button class="logout-btn hm-icon-btn" @click="handleLogout" title="退出登录">
        <span style="font-size: 16px">&#x23FB;</span>
      </button>
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
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useAuthStore } from './stores/useAuthStore.js'
import { useToastStore } from './stores/useToastStore.js'
import ChatSidebar from './features/chat/ChatSidebar.vue'
import ChatView from './features/chat/ChatView.vue'
import DocumentPanel from './features/documents/DocumentPanel.vue'
import LoginView from './features/auth/LoginView.vue'
import EvalDashboard from './features/eval/EvalDashboard.vue'

const authStore = useAuthStore()
const toastStore = useToastStore()
const isDark = ref(false)
const showDashboard = ref(false)

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
  height: 100%;
}

.sidebar {
  background: var(--hm-bg-primary);
  border-right: 1px solid var(--hm-divider);
  overflow-y: auto;
}

.main-content {
  display: flex;
  flex-direction: column;
  padding: 0;
  overflow: hidden;
  background: var(--hm-bg-primary);
}

.docs-panel {
  background: var(--hm-bg-primary);
  border-left: 1px solid var(--hm-divider);
  overflow-y: auto;
}

.toolbar {
  position: fixed;
  top: 12px;
  right: 12px;
  z-index: 100;
  display: flex;
  gap: 8px;
}

.dark-toggle,
.logout-btn,
.dashboard-btn {
  width: 36px;
  height: 36px;
  border-radius: var(--hm-radius-full);
  background: var(--hm-bg-glass);
  border: 1px solid var(--hm-border-glass);
  box-shadow: var(--hm-shadow-sm);
  backdrop-filter: blur(12px);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s var(--hm-ease-out);
}

.dark-toggle:hover,
.logout-btn:hover {
  box-shadow: var(--hm-shadow-md);
  background: var(--hm-hover-bg);
}

.logout-btn {
  color: var(--hm-font-secondary);
}

.logout-btn:hover {
  color: var(--hm-error);
}

/* ── Toast 容器 ── */
.toast-container {
  position: fixed;
  top: 60px;
  right: 16px;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.toast-item {
  padding: 10px 20px;
  border-radius: var(--hm-radius-md);
  font-size: 13px;
  font-weight: 500;
  box-shadow: var(--hm-shadow-md);
  animation: toast-in 0.3s var(--hm-spring);
}

.toast-item.success {
  background: #f0f9eb;
  color: #67c23a;
  border: 1px solid #e1f3d8;
}

.toast-item.error {
  background: #fef0f0;
  color: #f56c6c;
  border: 1px solid #fde2e2;
}

.toast-item.warning {
  background: #fdf6ec;
  color: #e6a23c;
  border: 1px solid #faecd8;
}

.toast-item.info {
  background: #f4f4f5;
  color: #909399;
  border: 1px solid #e9e9eb;
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
