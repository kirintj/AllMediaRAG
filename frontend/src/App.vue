<template>
  <LoginView v-if="!authStore.isAuthenticated" @login-success="onLoginSuccess" />

  <div v-else class="relative h-full w-full overflow-hidden">
    <div class="flex h-full w-full">
      <!-- Sidebar -->
      <aside
        class="flex-shrink-0 border-r border-sidebar-border bg-sidebar overflow-hidden transition-all duration-300 ease-out hidden lg:block"
        :style="{ width: sidebarCollapsed ? '56px' : '272px' }"
      >
        <AppSidebar
          :collapsed="sidebarCollapsed"
          @toggle-collapse="sidebarCollapsed = !sidebarCollapsed"
          @open-docs="showDocs = true"
          @open-eval="showEval = true"
          @logout="handleLogout"
        />
      </aside>

      <!-- Mobile sidebar overlay -->
      <Sheet v-model="mobileSidebar" side="left" class="w-[min(272px,calc(100vw-12px))] p-0 lg:hidden">
        <AppSidebar
          :collapsed="false"
          @toggle-collapse="mobileSidebar = false"
          @open-docs="showDocs = true; mobileSidebar = false"
          @open-eval="showEval = true; mobileSidebar = false"
          @logout="handleLogout"
        />
      </Sheet>

      <!-- Main content -->
      <main class="flex-1 flex flex-col min-w-0 overflow-hidden bg-background">
        <ChatShell
          @open-docs="showDocs = true"
          @open-eval="showEval = true"
        />
      </main>
    </div>

    <!-- Document drawer -->
    <Sheet v-model="showDocs" side="right" class="w-[400px] sm:w-[540px]">
      <DocumentDrawer />
    </Sheet>

    <!-- Eval dashboard -->
    <EvalDashboard v-model="showEval" />

    <!-- Toast container -->
    <div class="fixed top-4 right-4 z-[9999] flex flex-col gap-2">
      <div
        v-for="toast in toastStore.toasts"
        :key="toast.id"
        class="px-4 py-2.5 rounded-lg text-sm font-medium shadow-md animate-in fade-in-0 slide-in-from-top-2 duration-300"
        :class="{
          'bg-green-50 text-green-700 border border-green-200 dark:bg-green-950 dark:text-green-300 dark:border-green-800': toast.type === 'success',
          'bg-red-50 text-red-700 border border-red-200 dark:bg-red-950 dark:text-red-300 dark:border-red-800': toast.type === 'error',
          'bg-yellow-50 text-yellow-700 border border-yellow-200 dark:bg-yellow-950 dark:text-yellow-300 dark:border-yellow-800': toast.type === 'warning',
          'bg-muted text-muted-foreground border border-border': toast.type === 'info',
        }"
      >
        {{ toast.msg }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, provide, onMounted, onUnmounted } from 'vue'
import { useAuthStore } from './stores/useAuthStore.js'
import { useToastStore } from './stores/useToastStore.js'
import Sheet from './components/ui/sheet.vue'
import AppSidebar from './features/conversations/AppSidebar.vue'
import ChatShell from './features/chat/ChatShell.vue'
import DocumentDrawer from './features/documents/DocumentDrawer.vue'
import EvalDashboard from './features/eval/EvalDashboard.vue'
import LoginView from './features/auth/LoginView.vue'

const authStore = useAuthStore()
const toastStore = useToastStore()

const sidebarCollapsed = ref(false)
const mobileSidebar = ref(false)
const showDocs = ref(false)
const showEval = ref(false)

provide('toggleMobileSidebar', () => { mobileSidebar.value = true })

function onLoginSuccess() {}
function handleLogout() { authStore.logout() }
function onAuthExpired() { authStore.onAuthExpired() }

onMounted(async () => {
  await authStore.checkAuth()
  window.addEventListener('auth-expired', onAuthExpired)
})

onUnmounted(() => {
  window.removeEventListener('auth-expired', onAuthExpired)
})
</script>
