<script setup>
import SettingsGroup from '../../components/ui/settings-group.vue'
import SettingsRow from '../../components/ui/settings-row.vue'
import SettingsSectionTitle from '../../components/ui/settings-section-title.vue'
import ToggleButton from '../../components/ui/toggle-button.vue'
import Input from '../../components/ui/input.vue'
import { cn } from '../../lib/utils.js'

const props = defineProps({
  form: { type: Object, required: true },
})

const emit = defineEmits(['update:form'])

function updateField(key, value) {
  emit('update:form', { ...props.form, [key]: value })
}

const methodOptions = [
  { value: 'gmm', label: 'GMM' },
  { value: 'ahc', label: 'AHC' },
]
</script>

<template>
  <div class="space-y-4">
    <SettingsSectionTitle>RAPTOR 递归抽象处理</SettingsSectionTitle>

    <SettingsGroup>
      <SettingsRow title="启用 RAPTOR" description="使用递归聚类算法对文档块进行层级化组织，提升长文档检索效果">
        <ToggleButton
          :checked="form.raptor_enabled"
          label="启用 RAPTOR"
          @update:checked="updateField('raptor_enabled', $event)"
        />
      </SettingsRow>

      <SettingsRow title="聚类方法" description="选择文档块聚类的算法">
        <div class="inline-flex h-8 items-center rounded-full bg-muted p-0.5">
          <button
            v-for="opt in methodOptions"
            :key="opt.value"
            @click="updateField('raptor_method', opt.value)"
            :class="cn(
              'px-3 py-1 text-xs font-medium rounded-full transition-all',
              form.raptor_method === opt.value
                ? 'bg-background text-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground',
            )"
          >
            {{ opt.label }}
          </button>
        </div>
      </SettingsRow>

      <SettingsRow title="最大聚类数" description="每个层级的最大聚类数量">
        <Input
          type="number"
          :model-value="form.raptor_max_clusters"
          @update:model-value="updateField('raptor_max_clusters', Number($event))"
          min="2"
          max="100"
          class="w-20 h-8 text-right"
        />
      </SettingsRow>
    </SettingsGroup>
  </div>
</template>
