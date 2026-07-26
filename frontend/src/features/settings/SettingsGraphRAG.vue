<script setup>
import SettingsGroup from '../../components/ui/settings-group.vue'
import SettingsRow from '../../components/ui/settings-row.vue'
import SettingsSectionTitle from '../../components/ui/settings-section-title.vue'
import ToggleButton from '../../components/ui/toggle-button.vue'
import { cn } from '../../lib/utils.js'

const props = defineProps({
  form: { type: Object, required: true },
})

const emit = defineEmits(['update:form'])

function updateField(key, value) {
  emit('update:form', { ...props.form, [key]: value })
}

const methodOptions = [
  { value: 'general', label: 'General' },
  { value: 'light', label: 'Light' },
  { value: 'ner', label: 'NER' },
]
</script>

<template>
  <div class="space-y-4">
    <SettingsSectionTitle>知识图谱 (GraphRAG)</SettingsSectionTitle>

    <SettingsGroup>
      <SettingsRow title="启用知识图谱" description="基于实体-关系图谱进行检索，适用于复杂关联性问题">
        <ToggleButton
          :checked="form.graphrag_enabled"
          label="启用知识图谱"
          @update:checked="updateField('graphrag_enabled', $event)"
        />
      </SettingsRow>

      <SettingsRow title="图谱构建方法" description="选择知识图谱的构建策略">
        <div class="inline-flex h-8 items-center rounded-full bg-muted p-0.5">
          <button
            v-for="opt in methodOptions"
            :key="opt.value"
            @click="updateField('graphrag_method', opt.value)"
            :class="cn(
              'px-3 py-1 text-xs font-medium rounded-full transition-all',
              form.graphrag_method === opt.value
                ? 'bg-background text-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground',
            )"
          >
            {{ opt.label }}
          </button>
        </div>
      </SettingsRow>
    </SettingsGroup>

    <SettingsGroup>
      <SettingsRow title="实体消歧" description="自动合并指代同一实体的不同表述（如 'OpenAI' 和 'open ai'）">
        <ToggleButton
          :checked="form.graphrag_entity_resolution"
          label="实体消歧"
          @update:checked="updateField('graphrag_entity_resolution', $event)"
        />
      </SettingsRow>

      <SettingsRow title="社区检测" description="将关联紧密的实体聚类为社区，生成摘要用于全局检索">
        <ToggleButton
          :checked="form.graphrag_community_detection"
          label="社区检测"
          @update:checked="updateField('graphrag_community_detection', $event)"
        />
      </SettingsRow>

      <SettingsRow title="PageRank" description="使用 PageRank 算法对实体进行重要性排序，影响检索权重">
        <ToggleButton
          :checked="form.graphrag_pagerank"
          label="PageRank"
          @update:checked="updateField('graphrag_pagerank', $event)"
        />
      </SettingsRow>
    </SettingsGroup>
  </div>
</template>
