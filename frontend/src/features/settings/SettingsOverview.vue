<script setup>
import { useNavigationStore } from '../../stores/useNavigationStore.js'
import { FileText, Layers, Tag, Network, ChevronRight } from 'lucide-vue-next'
import SettingsGroup from '../../components/ui/settings-group.vue'
import SettingsSectionTitle from '../../components/ui/settings-section-title.vue'

const props = defineProps({
  form: { type: Object, default: () => ({}) },
})

const navigationStore = useNavigationStore()

const sections = [
  {
    key: 'doc-parsing',
    label: '文档解析增强',
    icon: FileText,
    getStatus: (f) => {
      const enabled = [f.auto_keywords, f.auto_questions, f.metadata_extraction, f.toc_extraction].filter(Boolean).length
      return `${enabled}/4 项已启用`
    },
  },
  {
    key: 'raptor',
    label: 'RAPTOR',
    icon: Layers,
    getStatus: (f) => f.raptor_enabled ? `已启用 · ${f.raptor_method?.toUpperCase()}` : '未启用',
  },
  {
    key: 'tagging',
    label: '内容标签',
    icon: Tag,
    getStatus: (f) => f.tagging_enabled ? `已启用 · TopN ${f.tagging_topn}` : '未启用',
  },
  {
    key: 'graphrag',
    label: '知识图谱',
    icon: Network,
    getStatus: (f) => f.graphrag_enabled ? `已启用 · ${f.graphrag_method}` : '未启用',
  },
]

function goToSection(key) {
  navigationStore.setActiveSettingsSection(key)
}
</script>

<template>
  <div class="space-y-4">
    <SettingsSectionTitle>RAG 配置概览</SettingsSectionTitle>

    <SettingsGroup>
      <button
        v-for="section in sections"
        :key="section.key"
        @click="goToSection(section.key)"
        class="flex items-center gap-4 w-full px-4 py-3.5 sm:px-5 min-h-[62px] text-left hover:bg-muted/45 transition-colors"
      >
        <component :is="section.icon" class="h-5 w-5 text-muted-foreground flex-shrink-0" />
        <div class="flex-1 min-w-0">
          <div class="text-[14px] font-medium text-foreground">{{ section.label }}</div>
          <div class="text-[12px] text-muted-foreground mt-0.5">
            {{ section.getStatus(form) }}
          </div>
        </div>
        <ChevronRight class="h-4 w-4 text-muted-foreground flex-shrink-0" />
      </button>
    </SettingsGroup>
  </div>
</template>
