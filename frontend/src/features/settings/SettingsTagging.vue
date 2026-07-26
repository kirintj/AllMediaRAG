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
    <SettingsSectionTitle>内容标签标注</SettingsSectionTitle>

    <SettingsGroup>
      <SettingsRow title="启用标签标注" description="自动为文档块生成语义标签，用于标签路由和过滤检索">
        <ToggleButton
          :checked="form.tagging_enabled"
          label="启用标签标注"
          @update:checked="updateField('tagging_enabled', $event)"
        />
      </SettingsRow>

      <SettingsRow title="TopN" description="每个文档块生成的标签数量上限">
        <Input
          type="number"
          :model-value="form.tagging_topn"
          @update:model-value="updateField('tagging_topn', Number($event))"
          min="1"
          max="20"
          class="w-20 h-8 text-right"
        />
      </SettingsRow>

      <SettingsRow title="Tag KB IDs" description="用于标签检索的知识库 ID 列表，以逗号分隔">
        <Input
          type="text"
          :model-value="form.tagging_tag_kb_ids"
          @update:model-value="updateField('tagging_tag_kb_ids', $event)"
          placeholder="kb1, kb2"
          class="w-48 h-8"
        />
      </SettingsRow>
    </SettingsGroup>
  </div>
</template>
