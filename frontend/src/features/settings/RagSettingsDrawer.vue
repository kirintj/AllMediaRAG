<script setup>
import { ref, onMounted, watch } from 'vue'
import { useSettingsStore } from '../../stores/useSettingsStore.js'
import { useToastStore } from '../../stores/useToastStore.js'
import { Settings, Loader2, Save } from 'lucide-vue-next'

const settingsStore = useSettingsStore()
const toast = useToastStore()

// Local form state (deep copy of settings for editing)
const form = ref({
  // Document parsing enhancement
  auto_keywords: false,
  auto_questions: false,
  metadata_extraction: false,
  toc_extraction: false,
  keywords_topn: 5,
  questions_topn: 5,

  // RAPTOR
  raptor_enabled: false,
  raptor_method: 'gmm',
  raptor_max_clusters: 10,

  // Content Tagging
  tagging_enabled: false,
  tagging_topn: 5,
  tagging_tag_kb_ids: '',

  // GraphRAG
  graphrag_enabled: false,
  graphrag_method: 'general',
  graphrag_entity_resolution: false,
  graphrag_community_detection: false,
  graphrag_pagerank: false,
})

// Sync store settings into local form
watch(() => settingsStore.settings, (val) => {
  if (val) {
    form.value = {
      auto_keywords: val.auto_keywords ?? false,
      auto_questions: val.auto_questions ?? false,
      metadata_extraction: val.metadata_extraction ?? false,
      toc_extraction: val.toc_extraction ?? false,
      keywords_topn: val.keywords_topn ?? 5,
      questions_topn: val.questions_topn ?? 5,
      raptor_enabled: val.raptor_enabled ?? false,
      raptor_method: val.raptor_method ?? 'gmm',
      raptor_max_clusters: val.raptor_max_clusters ?? 10,
      tagging_enabled: val.tagging_enabled ?? false,
      tagging_topn: val.tagging_topn ?? 5,
      tagging_tag_kb_ids: Array.isArray(val.tagging_tag_kb_ids) ? val.tagging_tag_kb_ids.join(', ') : (val.tagging_tag_kb_ids ?? ''),
      graphrag_enabled: val.graphrag_enabled ?? false,
      graphrag_method: val.graphrag_method ?? 'general',
      graphrag_entity_resolution: val.graphrag_entity_resolution ?? false,
      graphrag_community_detection: val.graphrag_community_detection ?? false,
      graphrag_pagerank: val.graphrag_pagerank ?? false,
    }
  }
}, { immediate: true })

async function handleSave() {
  try {
    // Parse comma-separated tag KB IDs
    const payload = {
      ...form.value,
      tagging_tag_kb_ids: form.value.tagging_tag_kb_ids
        ? form.value.tagging_tag_kb_ids.split(',').map(s => s.trim()).filter(Boolean)
        : [],
    }
    await settingsStore.saveSettings(payload)
    toast.success('配置已保存')
  } catch (err) {
    toast.error('保存失败: ' + (err.response?.data?.detail || err.message))
  }
}

onMounted(() => {
  settingsStore.fetchSettings()
})
</script>

<template>
  <div class="flex flex-col h-full p-4 gap-4 overflow-y-auto">
    <!-- Header -->
    <div class="flex items-center gap-2">
      <Settings class="h-5 w-5 text-foreground" />
      <h2 class="text-lg font-semibold text-foreground">RAG 设置</h2>
    </div>

    <!-- Loading -->
    <div v-if="settingsStore.loading" class="flex items-center justify-center gap-2 py-8 text-muted-foreground">
      <Loader2 class="h-4 w-4 animate-spin" />
      <span class="text-sm">加载配置中...</span>
    </div>

    <template v-else>
      <!-- Group 1: Document Parsing Enhancement -->
      <div class="space-y-3">
        <h3 class="text-xs font-medium text-muted-foreground uppercase tracking-wider">文档解析增强</h3>
        <div class="space-y-2.5 p-3 bg-muted rounded-lg">
          <label class="flex items-center justify-between cursor-pointer">
            <span class="text-sm text-foreground">自动关键词</span>
            <input type="checkbox" v-model="form.auto_keywords" class="h-4 w-4 rounded border-input text-primary focus:ring-primary" />
          </label>
          <label class="flex items-center justify-between cursor-pointer">
            <span class="text-sm text-foreground">自动问题</span>
            <input type="checkbox" v-model="form.auto_questions" class="h-4 w-4 rounded border-input text-primary focus:ring-primary" />
          </label>
          <label class="flex items-center justify-between cursor-pointer">
            <span class="text-sm text-foreground">元数据提取</span>
            <input type="checkbox" v-model="form.metadata_extraction" class="h-4 w-4 rounded border-input text-primary focus:ring-primary" />
          </label>
          <label class="flex items-center justify-between cursor-pointer">
            <span class="text-sm text-foreground">TOC 提取</span>
            <input type="checkbox" v-model="form.toc_extraction" class="h-4 w-4 rounded border-input text-primary focus:ring-primary" />
          </label>
          <div class="flex items-center justify-between">
            <span class="text-sm text-foreground">Keywords TopN</span>
            <input
              type="number"
              v-model.number="form.keywords_topn"
              min="1"
              max="20"
              class="w-20 h-8 rounded-md border border-input bg-background px-2 text-sm text-right shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            />
          </div>
          <div class="flex items-center justify-between">
            <span class="text-sm text-foreground">Questions TopN</span>
            <input
              type="number"
              v-model.number="form.questions_topn"
              min="1"
              max="20"
              class="w-20 h-8 rounded-md border border-input bg-background px-2 text-sm text-right shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            />
          </div>
        </div>
      </div>

      <!-- Group 2: RAPTOR -->
      <div class="space-y-3">
        <h3 class="text-xs font-medium text-muted-foreground uppercase tracking-wider">RAPTOR</h3>
        <div class="space-y-2.5 p-3 bg-muted rounded-lg">
          <label class="flex items-center justify-between cursor-pointer">
            <span class="text-sm text-foreground">启用 RAPTOR</span>
            <input type="checkbox" v-model="form.raptor_enabled" class="h-4 w-4 rounded border-input text-primary focus:ring-primary" />
          </label>
          <div class="flex items-center justify-between">
            <span class="text-sm text-foreground">聚类方法</span>
            <select
              v-model="form.raptor_method"
              class="w-32 h-8 rounded-md border border-input bg-background px-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            >
              <option value="gmm">GMM</option>
              <option value="ahc">AHC</option>
            </select>
          </div>
          <div class="flex items-center justify-between">
            <span class="text-sm text-foreground">最大聚类数</span>
            <input
              type="number"
              v-model.number="form.raptor_max_clusters"
              min="2"
              max="100"
              class="w-20 h-8 rounded-md border border-input bg-background px-2 text-sm text-right shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            />
          </div>
        </div>
      </div>

      <!-- Group 3: Content Tagging -->
      <div class="space-y-3">
        <h3 class="text-xs font-medium text-muted-foreground uppercase tracking-wider">标签标注</h3>
        <div class="space-y-2.5 p-3 bg-muted rounded-lg">
          <label class="flex items-center justify-between cursor-pointer">
            <span class="text-sm text-foreground">启用标签标注</span>
            <input type="checkbox" v-model="form.tagging_enabled" class="h-4 w-4 rounded border-input text-primary focus:ring-primary" />
          </label>
          <div class="flex items-center justify-between">
            <span class="text-sm text-foreground">TopN</span>
            <input
              type="number"
              v-model.number="form.tagging_topn"
              min="1"
              max="20"
              class="w-20 h-8 rounded-md border border-input bg-background px-2 text-sm text-right shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            />
          </div>
          <div>
            <span class="text-sm text-foreground block mb-1">Tag KB IDs</span>
            <input
              type="text"
              v-model="form.tagging_tag_kb_ids"
              placeholder="以逗号分隔，如: kb1, kb2"
              class="w-full h-8 rounded-md border border-input bg-background px-3 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            />
          </div>
        </div>
      </div>

      <!-- Group 4: GraphRAG -->
      <div class="space-y-3">
        <h3 class="text-xs font-medium text-muted-foreground uppercase tracking-wider">知识图谱 (GraphRAG)</h3>
        <div class="space-y-2.5 p-3 bg-muted rounded-lg">
          <label class="flex items-center justify-between cursor-pointer">
            <span class="text-sm text-foreground">启用知识图谱</span>
            <input type="checkbox" v-model="form.graphrag_enabled" class="h-4 w-4 rounded border-input text-primary focus:ring-primary" />
          </label>
          <div class="flex items-center justify-between">
            <span class="text-sm text-foreground">方法</span>
            <select
              v-model="form.graphrag_method"
              class="w-32 h-8 rounded-md border border-input bg-background px-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            >
              <option value="general">General</option>
              <option value="light">Light</option>
              <option value="ner">NER</option>
            </select>
          </div>
          <label class="flex items-center justify-between cursor-pointer">
            <span class="text-sm text-foreground">实体消歧</span>
            <input type="checkbox" v-model="form.graphrag_entity_resolution" class="h-4 w-4 rounded border-input text-primary focus:ring-primary" />
          </label>
          <label class="flex items-center justify-between cursor-pointer">
            <span class="text-sm text-foreground">社区检测</span>
            <input type="checkbox" v-model="form.graphrag_community_detection" class="h-4 w-4 rounded border-input text-primary focus:ring-primary" />
          </label>
          <label class="flex items-center justify-between cursor-pointer">
            <span class="text-sm text-foreground">PageRank</span>
            <input type="checkbox" v-model="form.graphrag_pagerank" class="h-4 w-4 rounded border-input text-primary focus:ring-primary" />
          </label>
        </div>
      </div>

      <!-- Save button -->
      <div class="space-y-2 pt-2">
        <button
          class="w-full flex items-center justify-center gap-2 h-9 rounded-md bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          :disabled="settingsStore.saving"
          @click="handleSave"
        >
          <Loader2 v-if="settingsStore.saving" class="h-4 w-4 animate-spin" />
          <Save v-else class="h-4 w-4" />
          保存配置
        </button>
        <p class="text-[11px] text-muted-foreground text-center">部分配置修改后需要重启服务才能生效</p>
      </div>
    </template>
  </div>
</template>
