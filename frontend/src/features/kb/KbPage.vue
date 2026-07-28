<script setup>
import { onMounted } from 'vue'
import { useNavigationStore } from '../../stores/useNavigationStore.js'
import { useAuthStore } from '../../stores/useAuthStore.js'
import { FolderOpen, FileText, Tags, Network, ArrowLeft, LogOut } from 'lucide-vue-next'
import { cn } from '../../lib/utils.js'
import PageLayout from '../../components/layout/PageLayout.vue'
import KnowledgebaseContent from './KnowledgebaseContent.vue'
import DocumentContent from '../documents/DocumentContent.vue'
import TagKbContent from '../tag-kb/TagKbContent.vue'
import GraphContent from '../graph/GraphContent.vue'

const navigationStore = useNavigationStore()
const authStore = useAuthStore()

const navItems = [
  { key: 'knowledgebases', label: '知识库管理', icon: FolderOpen },
  { key: 'documents', label: '文档管理', icon: FileText },
  { key: 'tag-kb', label: '标签知识库', icon: Tags },
  { key: 'graph', label: '知识图谱', icon: Network },
]

onMounted(() => {
  if (!navigationStore.activePage || !navItems.find(i => i.key === navigationStore.activePage)) {
    navigationStore.setActivePage('knowledgebases')
  }
})
</script>

<template>
  <PageLayout title="知识库">
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
        <h1 class="text-lg font-semibold text-foreground">知识库</h1>
      </div>
      <nav class="flex-1 overflow-y-auto min-h-0 px-3">
        <div class="flex flex-col gap-0.5">
          <button
            v-for="item in navItems"
            :key="item.key"
            @click="navigationStore.setActivePage(item.key)"
            :class="cn(
              'flex items-center gap-3 w-full px-3 py-2.5 rounded-[10px] text-sm transition-colors',
              navigationStore.activePage === item.key
                ? 'bg-muted/60 text-foreground font-medium'
                : 'text-muted-foreground hover:bg-muted/45 hover:text-foreground',
            )"
          >
            <component :is="item.icon" class="h-4 w-4 flex-shrink-0" />
            <span>{{ item.label }}</span>
          </button>
        </div>
      </nav>
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

    <KnowledgebaseContent v-if="navigationStore.activePage === 'knowledgebases'" />
    <DocumentContent v-else-if="navigationStore.activePage === 'documents'" />
    <TagKbContent v-else-if="navigationStore.activePage === 'tag-kb'" />
    <GraphContent v-else-if="navigationStore.activePage === 'graph'" />
  </PageLayout>
</template>
