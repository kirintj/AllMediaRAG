<script setup>
import { useNavigationStore } from '../../stores/useNavigationStore.js'
import { useAuthStore } from '../../stores/useAuthStore.js'
import { ArrowLeft, LogOut } from 'lucide-vue-next'
import PageLayout from '../../components/layout/PageLayout.vue'
import TeamContent from './TeamContent.vue'

const navigationStore = useNavigationStore()
const authStore = useAuthStore()
</script>

<template>
  <PageLayout title="团队管理">
    <template #sidebar>
      <div class="px-3 pt-3 pb-1">
        <button
          @click="navigationStore.setActiveNav('chat')"
          class="flex items-center gap-2 w-full px-3 py-2 rounded-[10px] text-sm text-muted-foreground hover:bg-muted/45 transition-colors"
        >
          <ArrowLeft class="h-4 w-4" />
          <span>返回</span>
        </button>
      </div>
      <div class="px-5 pt-2 pb-3">
        <h1 class="text-lg font-semibold text-foreground">团队管理</h1>
      </div>
      <div class="flex-1" />
      <div class="flex-shrink-0 px-3 py-3 border-t border-border/45">
        <button
          @click="authStore.logout()"
          class="flex items-center gap-3 w-full px-3 py-2.5 rounded-[10px] text-sm text-destructive hover:bg-destructive/10 transition-colors"
        >
          <LogOut class="h-4 w-4 flex-shrink-0" />
          <span>退出登录</span>
        </button>
      </div>
    </template>

    <TeamContent />
  </PageLayout>
</template>
