<script setup>
import SettingsGroup from '../../components/ui/settings-group.vue'
import SettingsRow from '../../components/ui/settings-row.vue'
import SettingsSectionTitle from '../../components/ui/settings-section-title.vue'
import ToggleButton from '../../components/ui/toggle-button.vue'
import Input from '../../components/ui/input.vue'

const props = defineProps({
  form: { type: Object, required: true },
})

const emit = defineEmits(['update:form'])

function updateField(key, value) {
  emit('update:form', { ...props.form, [key]: value })
}
</script>

<template>
  <div class="space-y-4">
    <SettingsSectionTitle>文档解析增强</SettingsSectionTitle>

    <SettingsGroup>
      <SettingsRow title="自动关键词" description="为文档块自动生成关键词，提升检索召回率">
        <ToggleButton
          :checked="form.auto_keywords"
          label="自动关键词"
          @update:checked="updateField('auto_keywords', $event)"
        />
      </SettingsRow>

      <SettingsRow title="自动问题" description="为文档块自动生成可能的提问，用于问题匹配检索">
        <ToggleButton
          :checked="form.auto_questions"
          label="自动问题"
          @update:checked="updateField('auto_questions', $event)"
        />
      </SettingsRow>

      <SettingsRow title="元数据提取" description="自动提取文档的标题、作者、日期等元数据信息">
        <ToggleButton
          :checked="form.metadata_extraction"
          label="元数据提取"
          @update:checked="updateField('metadata_extraction', $event)"
        />
      </SettingsRow>

      <SettingsRow title="TOC 提取" description="自动提取文档的目录结构，用于层级检索">
        <ToggleButton
          :checked="form.toc_extraction"
          label="TOC 提取"
          @update:checked="updateField('toc_extraction', $event)"
        />
      </SettingsRow>
    </SettingsGroup>

    <SettingsGroup>
      <SettingsRow title="Keywords TopN" description="每个文档块生成的关键词数量上限">
        <Input
          type="number"
          :model-value="form.keywords_topn"
          @update:model-value="updateField('keywords_topn', Number($event))"
          min="1"
          max="20"
          class="w-20 h-8 text-right"
        />
      </SettingsRow>

      <SettingsRow title="Questions TopN" description="每个文档块生成的问题数量上限">
        <Input
          type="number"
          :model-value="form.questions_topn"
          @update:model-value="updateField('questions_topn', Number($event))"
          min="1"
          max="20"
          class="w-20 h-8 text-right"
        />
      </SettingsRow>
    </SettingsGroup>
  </div>
</template>
