<template>
  <!-- 未认证：显示登录页 -->
  <LoginView v-if="!isAuthenticated" @login-success="onLoginSuccess" />

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

    <!-- 工具栏：深色模式 + 退出登录 -->
    <div class="toolbar">
      <button class="dark-toggle hm-icon-btn" @click="toggleDark" :title="isDark ? '切换浅色模式' : '切换深色模式'">
        <span v-if="isDark" style="font-size: 18px">&#9728;&#65039;</span>
        <span v-else style="font-size: 18px">&#127769;</span>
      </button>
      <button class="logout-btn hm-icon-btn" @click="handleLogout" title="退出登录">
        <span style="font-size: 16px">⏻</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import ChatSidebar from './components/ChatSidebar.vue'
import ChatView from './components/ChatView.vue'
import DocumentPanel from './components/DocumentPanel.vue'
import LoginView from './components/LoginView.vue'

const isDark = ref(false)
const isAuthenticated = ref(false)

function toggleDark() {
  isDark.value = !isDark.value
  document.documentElement.classList.toggle('dark', isDark.value)
}

function onLoginSuccess() {
  isAuthenticated.value = true
}

function handleLogout() {
  localStorage.removeItem('token')
  isAuthenticated.value = false
}

function onAuthExpired() {
  isAuthenticated.value = false
}

onMounted(async () => {
  // 检查是否有有效 token
  const token = localStorage.getItem('token')
  if (token) {
    try {
      const { getMe } = await import('./api/index.js')
      await getMe()
      isAuthenticated.value = true
    } catch {
      localStorage.removeItem('token')
    }
  }

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
.logout-btn {
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
</style>
