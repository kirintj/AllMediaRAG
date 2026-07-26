<template>
  <div class="flex flex-col h-full">
    <!-- Header -->
    <div class="flex items-center justify-between px-4 h-12 border-b border-border flex-shrink-0">
      <h3 class="text-sm font-semibold text-foreground">知识库</h3>
      <button
        class="h-7 w-7 flex items-center justify-center rounded-md hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
        @click="$emit('open-kb')"
        title="新建知识库"
      >
        <Plus class="h-4 w-4" />
      </button>
    </div>

    <!-- KB list -->
    <div class="flex-1 overflow-y-auto min-h-0 px-2 py-2">
      <!-- Loading state -->
      <div v-if="kbStore.loading" class="flex items-center justify-center py-10">
        <Loader2 class="h-5 w-5 text-muted-foreground animate-spin" />
      </div>

      <!-- Empty state -->
      <div v-else-if="kbStore.knowledgebases.length === 0" class="flex flex-col items-center justify-center py-10 px-4 text-center">
        <div class="w-10 h-10 rounded-xl bg-muted flex items-center justify-center mb-3">
          <Database class="h-5 w-5 text-muted-foreground" />
        </div>
        <p class="text-sm text-muted-foreground">暂无知识库</p>
        <p class="text-[11px] text-muted-foreground/70 mt-0.5">点击上方 + 创建</p>
      </div>

      <!-- KB items -->
      <div v-else class="flex flex-col gap-1">
        <div
          v-for="kb in kbStore.knowledgebases"
          :key="kb.id"
          class="group flex items-start gap-2.5 px-2.5 py-2 rounded-md cursor-pointer hover:bg-accent transition-colors"
          @click="$emit('open-kb')"
        >
          <FolderOpen class="h-4 w-4 text-muted-foreground flex-shrink-0 mt-0.5" />
          <div class="flex-1 min-w-0">
            <p class="text-sm font-medium text-foreground truncate">{{ kb.name }}</p>
            <p class="text-[11px] text-muted-foreground mt-0.5">
              {{ kb.document_count || 0 }} 份文档
              <span v-if="kb.status === 'processing'" class="text-primary">· 处理中</span>
            </p>
            <!-- Progress bar for processing KBs -->
            <div
              v-if="kb.status === 'processing' && kb.progress != null"
              class="mt-1.5 h-1 rounded-full bg-muted overflow-hidden"
            >
              <div class="h-full bg-primary rounded-full transition-all" :style="{ width: kb.progress + '%' }" />
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Footer -->
    <div class="flex-shrink-0 border-t border-border px-3 py-2">
      <button
        class="flex items-center justify-center gap-2 w-full h-8 rounded-md text-xs font-medium text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
        @click="$emit('open-kb')"
      >
        <Settings class="h-3.5 w-3.5" />
        <span>管理知识库</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { Plus, Database, FolderOpen, Settings, Loader2 } from 'lucide-vue-next'
import { useKbStore } from '../../../stores/useKbStore.js'

defineEmits(['open-kb'])

const kbStore = useKbStore()

onMounted(() => {
  if (kbStore.knowledgebases.length === 0) {
    kbStore.fetchKnowledgebases()
  }
})
</script>
