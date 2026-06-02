<template>
  <div class="app-container" :class="{ dark: isDark }">
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

    <!-- 深色模式切换 -->
    <button class="dark-toggle hm-icon-btn" @click="toggleDark" :title="isDark ? '切换浅色模式' : '切换深色模式'">
      <span v-if="isDark" style="font-size: 18px">&#9728;&#65039;</span>
      <span v-else style="font-size: 18px">&#127769;</span>
    </button>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import ChatSidebar from './components/ChatSidebar.vue'
import ChatView from './components/ChatView.vue'
import DocumentPanel from './components/DocumentPanel.vue'

const isDark = ref(false)

function toggleDark() {
  isDark.value = !isDark.value
  document.documentElement.classList.toggle('dark', isDark.value)
}
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

.dark-toggle {
  position: fixed;
  top: 12px;
  right: 12px;
  z-index: 100;
  width: 36px;
  height: 36px;
  border-radius: var(--hm-radius-full);
  background: var(--hm-bg-glass);
  border: 1px solid var(--hm-border-glass);
  box-shadow: var(--hm-shadow-sm);
  backdrop-filter: blur(12px);
}
</style>
