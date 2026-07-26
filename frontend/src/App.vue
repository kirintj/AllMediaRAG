<template>
  <LoginView v-if="!authStore.isAuthenticated" @login-success="onLoginSuccess" />

  <div v-else class="relative h-full w-full overflow-hidden">
    <div class="flex h-full w-full">
      <!-- L1: Icon sidebar (always visible on desktop) -->
      <L1Sidebar class="hidden lg:flex" @logout="handleLogout" />

      <!-- L2: Content panel (collapsible, resizable) -->
      <L2Sidebar
        class="hidden lg:block"
        :width="navigationStore.l2Width"
        :expanded="navigationStore.l2Expanded"
        @update:width="navigationStore.setL2Width($event)"
        @open-docs="showDocs = true"
        @open-eval="showEval = true"
        @open-models="showModels = true"
        @open-tag-kb="showTagKb = true"
        @open-settings="showRagSettings = true"
        @open-graph="showGraph = true"
        @open-kb="showKb = true"
        @open-team="showTeam = true"
        @logout="handleLogout"
      />

      <!-- Main content -->
      <main class="flex-1 flex flex-col min-w-0 overflow-hidden bg-background">
        <ChatShell
          @open-docs="showDocs = true"
          @open-eval="showEval = true"
        />
      </main>
    </div>

    <!-- Mobile sidebar overlay -->
    <Sheet v-model="navigationStore.mobileSidebarOpen" side="left" class="w-[min(280px,calc(100vw-12px))] p-0 lg:hidden">
      <L2Sidebar
        :width="280"
        :expanded="true"
        @open-docs="showDocs = true; navigationStore.closeMobileSidebar()"
        @open-eval="showEval = true; navigationStore.closeMobileSidebar()"
        @open-models="showModels = true; navigationStore.closeMobileSidebar()"
        @open-tag-kb="showTagKb = true; navigationStore.closeMobileSidebar()"
        @open-settings="showRagSettings = true; navigationStore.closeMobileSidebar()"
        @open-graph="showGraph = true; navigationStore.closeMobileSidebar()"
        @open-kb="showKb = true; navigationStore.closeMobileSidebar()"
        @open-team="showTeam = true; navigationStore.closeMobileSidebar()"
        @logout="handleLogout"
      />
    </Sheet>

    <!-- Document drawer -->
    <Sheet v-model="showDocs" side="right" class="w-[400px] sm:w-[540px]">
      <DocumentDrawer />
    </Sheet>

    <!-- Eval dashboard -->
    <EvalDashboard v-model="showEval" />

    <!-- Model manager drawer -->
    <Sheet v-model="showModels" side="right" class="w-[400px] sm:w-[540px]">
      <ModelManager />
    </Sheet>

    <!-- Tag KB drawer -->
    <Sheet v-model="showTagKb" side="right" class="w-[400px] sm:w-[540px]">
      <TagKbDrawer />
    </Sheet>

    <!-- RAG settings drawer -->
    <Sheet v-model="showRagSettings" side="right" class="w-[400px] sm:w-[540px]">
      <RagSettingsDrawer />
    </Sheet>

    <!-- Graph viewer -->
    <GraphViewer :open="showGraph" @close="showGraph = false" />

    <!-- Knowledgebase drawer -->
    <KnowledgebaseDrawer :open="showKb" @close="showKb = false" />

    <!-- Team drawer -->
    <TeamDrawer :open="showTeam" @close="showTeam = false" />

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
import { useNavigationStore } from './stores/useNavigationStore.js'
import Sheet from './components/ui/sheet.vue'
import L1Sidebar from './features/navigation/L1Sidebar.vue'
import L2Sidebar from './features/navigation/L2Sidebar.vue'
import ChatShell from './features/chat/ChatShell.vue'
import DocumentDrawer from './features/documents/DocumentDrawer.vue'
import EvalDashboard from './features/eval/EvalDashboard.vue'
import ModelManager from './features/model-manager/ModelManager.vue'
import TagKbDrawer from './features/tag-kb/TagKbDrawer.vue'
import RagSettingsDrawer from './features/settings/RagSettingsDrawer.vue'
import GraphViewer from './features/graph/GraphViewer.vue'
import KnowledgebaseDrawer from './features/kb/KnowledgebaseDrawer.vue'
import TeamDrawer from './features/team/TeamDrawer.vue'
import LoginView from './features/auth/LoginView.vue'

const authStore = useAuthStore()
const toastStore = useToastStore()
const navigationStore = useNavigationStore()

const showDocs = ref(false)
const showEval = ref(false)
const showModels = ref(false)
const showTagKb = ref(false)
const showRagSettings = ref(false)
const showGraph = ref(false)
const showKb = ref(false)
const showTeam = ref(false)

provide('toggleMobileSidebar', () => { navigationStore.openMobileSidebar() })

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
