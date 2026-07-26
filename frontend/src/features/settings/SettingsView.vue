<script setup>
import { ref, watch, onMounted } from 'vue'
import { useSettingsStore } from '../../stores/useSettingsStore.js'
import { useNavigationStore } from '../../stores/useNavigationStore.js'
import { useToastStore } from '../../stores/useToastStore.js'
import { Loader2, Save } from 'lucide-vue-next'
import Button from '../../components/ui/button.vue'
import ScrollArea from '../../components/ui/scroll-area.vue'
import SettingsSidebar from './SettingsSidebar.vue'
import SettingsOverview from './SettingsOverview.vue'
import SettingsDocParsing from './SettingsDocParsing.vue'
import SettingsRaptor from './SettingsRaptor.vue'
import SettingsTagging from './SettingsTagging.vue'
import SettingsGraphRAG from './SettingsGraphRAG.vue'
import ModelContent from '../model-manager/ModelContent.vue'
import EvalContent from '../eval/EvalContent.vue'

const settingsStore = useSettingsStore()
const navigationStore = useNavigationStore()
const toast = useToastStore()

const form = ref({
  auto_keywords: false,
  auto_questions: false,
  metadata_extraction: false,
  toc_extraction: false,
  keywords_topn: 5,
  questions_topn: 5,
  raptor_enabled: false,
  raptor_method: 'gmm',
  raptor_max_clusters: 10,
  tagging_enabled: false,
  tagging_topn: 5,
  tagging_tag_kb_ids: '',
  graphrag_enabled: false,
  graphrag_method: 'general',
  graphrag_entity_resolution: false,
  graphrag_community_detection: false,
  graphrag_pagerank: false,
})

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
      tagging_tag_kb_ids: Array.isArray(val.tagging_tag_kb_ids)
        ? val.tagging_tag_kb_ids.join(', ')
        : (val.tagging_tag_kb_ids ?? ''),
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
  <div class="flex h-full w-full">
    <!-- Settings sidebar -->
    <SettingsSidebar
      class="hidden lg:flex"
    />

    <!-- Content area -->
    <main class="flex-1 min-w-0 overflow-hidden">
      <ScrollArea class="h-full">
        <div class="mx-auto max-w-[920px] px-6 py-6 sm:px-8 sm:py-8">
          <!-- Loading state -->
          <div v-if="settingsStore.loading" class="flex items-center justify-center gap-2 py-16 text-muted-foreground">
            <Loader2 class="h-5 w-5 animate-spin" />
            <span class="text-sm">加载配置中...</span>
          </div>

          <template v-else>
            <!-- Section content -->
            <SettingsOverview
              v-if="navigationStore.activeSettingsSection === 'overview'"
              :form="form"
            />
            <SettingsDocParsing
              v-else-if="navigationStore.activeSettingsSection === 'doc-parsing'"
              :form="form"
              @update:form="form = $event"
            />
            <SettingsRaptor
              v-else-if="navigationStore.activeSettingsSection === 'raptor'"
              :form="form"
              @update:form="form = $event"
            />
            <SettingsTagging
              v-else-if="navigationStore.activeSettingsSection === 'tagging'"
              :form="form"
              @update:form="form = $event"
            />
            <SettingsGraphRAG
              v-else-if="navigationStore.activeSettingsSection === 'graphrag'"
              :form="form"
              @update:form="form = $event"
            />
            <ModelContent v-else-if="navigationStore.activeSettingsSection === 'models'" />
            <EvalContent v-else-if="navigationStore.activeSettingsSection === 'eval'" />

            <!-- Save button (not on overview) -->
            <div v-if="navigationStore.activeSettingsSection !== 'overview'" class="mt-6 flex flex-col items-center gap-2">
              <Button
                :disabled="settingsStore.saving"
                @click="handleSave"
                class="w-full max-w-xs"
              >
                <Loader2 v-if="settingsStore.saving" class="h-4 w-4 animate-spin mr-2" />
                <Save v-else class="h-4 w-4 mr-2" />
                保存配置
              </Button>
              <p class="text-[11px] text-muted-foreground">部分配置修改后需要重启服务才能生效</p>
            </div>
          </template>
        </div>
      </ScrollArea>
    </main>
  </div>
</template>
