<script setup>
import { ref, onMounted, computed } from 'vue'
import { useModelStore } from '../../stores/useModelStore.js'
import { useToastStore } from '../../stores/useToastStore.js'
import { X, Plus, Trash2, Star, Cpu, Settings, Loader2 } from 'lucide-vue-next'
import Button from '../../components/ui/button.vue'
import Input from '../../components/ui/input.vue'

const modelStore = useModelStore()
const toast = useToastStore()

// Add model form state
const showAddForm = ref(false)
const newModel = ref({
  llm_factory: '',
  model_type: 'chat',
  llm_name: '',
  api_key: '',
  api_base: '',
})

const MODEL_TYPE_LABELS = {
  chat: '对话模型',
  embedding: '向量模型',
  rerank: '重排序',
  cv: '视觉模型',
  ocr: 'OCR',
  tts: '语音合成',
  asr: '语音识别',
}

const MODEL_TYPE_ICONS = {
  chat: 'Chat',
  embedding: 'Embed',
  rerank: 'Rerank',
  cv: 'CV',
  ocr: 'OCR',
  tts: 'TTS',
  asr: 'ASR',
}

// Group models by type
const modelsByType = computed(() => {
  const groups = {}
  for (const m of modelStore.models) {
    if (!groups[m.model_type]) groups[m.model_type] = []
    groups[m.model_type].push(m)
  }
  return groups
})

// Available factory names for the selected type
const availableFactories = computed(() => {
  const type = newModel.value.model_type
  return modelStore.factories
    .filter(f => f.tags && f.tags.includes(typeToTag(type)))
    .map(f => f.name)
})

function typeToTag(type) {
  const map = {
    chat: 'LLM',
    embedding: 'TEXT EMBEDDING',
    rerank: 'RERANK',
    cv: 'CV',
    ocr: 'OCR',
    tts: 'TTS',
    asr: 'ASR',
  }
  return map[type] || type
}

async function handleAdd() {
  try {
    await modelStore.addNewModel(newModel.value)
    toast.success('模型添加成功')
    showAddForm.value = false
    newModel.value = { llm_factory: '', model_type: 'chat', llm_name: '', api_key: '', api_base: '' }
  } catch (err) {
    toast.error('添加失败: ' + (err.response?.data?.detail || err.message))
  }
}

async function handleDelete(modelId) {
  if (!confirm('确认删除该模型？')) return
  try {
    await modelStore.removeModel(modelId)
    toast.success('模型已删除')
  } catch (err) {
    toast.error('删除失败')
  }
}

async function handleSetDefault(modelType, modelId) {
  try {
    await modelStore.setDefault(modelType, modelId)
    toast.success(`默认 ${MODEL_TYPE_LABELS[modelType]} 已设置`)
  } catch (err) {
    toast.error('设置失败')
  }
}

onMounted(() => {
  modelStore.fetchFactories()
  modelStore.fetchModels()
  modelStore.fetchModelTypes()
})
</script>

<template>
  <div class="flex flex-col h-full p-4 gap-4 overflow-y-auto">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-2">
        <Settings class="h-5 w-5 text-foreground" />
        <h2 class="text-lg font-semibold text-foreground">模型管理</h2>
      </div>
    </div>

    <!-- Add model button -->
    <button
      class="w-full flex items-center justify-center gap-2 p-3 border-2 border-dashed border-border rounded-lg hover:border-primary/50 hover:bg-accent/50 transition-colors text-muted-foreground hover:text-foreground"
      @click="showAddForm = !showAddForm"
    >
      <Plus class="h-4 w-4" />
      <span class="text-sm">添加模型</span>
    </button>

    <!-- Add model form -->
    <div v-if="showAddForm" class="p-4 bg-muted rounded-lg space-y-3">
      <div>
        <label class="text-xs font-medium text-muted-foreground">模型类型</label>
        <select
          v-model="newModel.model_type"
          class="w-full mt-1 h-9 rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
        >
          <option v-for="t in modelStore.modelTypes" :key="t.value" :value="t.value">
            {{ t.label }}
          </option>
        </select>
      </div>
      <div>
        <label class="text-xs font-medium text-muted-foreground">厂商</label>
        <select
          v-model="newModel.llm_factory"
          class="w-full mt-1 h-9 rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
        >
          <option value="" disabled>选择厂商</option>
          <option v-for="f in availableFactories" :key="f" :value="f">{{ f }}</option>
        </select>
      </div>
      <div>
        <label class="text-xs font-medium text-muted-foreground">模型名称</label>
        <Input v-model="newModel.llm_name" placeholder="如 gpt-4o、deepseek-chat" class="mt-1" />
      </div>
      <div>
        <label class="text-xs font-medium text-muted-foreground">API Key</label>
        <Input v-model="newModel.api_key" type="password" placeholder="sk-..." class="mt-1" />
      </div>
      <div>
        <label class="text-xs font-medium text-muted-foreground">API Base (可选)</label>
        <Input v-model="newModel.api_base" placeholder="https://api.openai.com/v1" class="mt-1" />
      </div>
      <div class="flex gap-2">
        <Button :disabled="!newModel.llm_factory || !newModel.llm_name" class="flex-1" @click="handleAdd">
          添加
        </Button>
        <Button variant="outline" @click="showAddForm = false">取消</Button>
      </div>
    </div>

    <!-- Loading indicator -->
    <div v-if="modelStore.loading" class="flex items-center justify-center gap-2 py-4 text-muted-foreground">
      <Loader2 class="h-4 w-4 animate-spin" />
      <span class="text-sm">加载中...</span>
    </div>

    <!-- Models grouped by type -->
    <div v-for="(typeModels, type) in modelsByType" :key="type" class="space-y-2">
      <h3 class="text-xs font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
        <Cpu class="h-3.5 w-3.5" />
        {{ MODEL_TYPE_LABELS[type] || type }}
      </h3>
      <div
        v-for="model in typeModels"
        :key="model.id"
        class="flex items-center justify-between p-3 bg-muted rounded-lg group"
      >
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2">
            <span class="text-sm font-medium text-foreground truncate">{{ model.llm_name }}</span>
            <span class="text-[11px] text-muted-foreground">{{ model.llm_factory }}</span>
          </div>
          <div class="text-[11px] text-muted-foreground mt-0.5">
            Tokens: {{ model.used_tokens?.toLocaleString() || 0 }}
          </div>
        </div>
        <div class="flex items-center gap-1">
          <button
            class="p-1.5 rounded-md hover:bg-background text-muted-foreground hover:text-foreground transition-colors"
            title="设为默认"
            @click="handleSetDefault(type, model.id)"
          >
            <Star class="h-4 w-4" />
          </button>
          <button
            class="p-1.5 rounded-md hover:bg-destructive/10 text-muted-foreground hover:text-destructive transition-colors opacity-0 group-hover:opacity-100"
            title="删除"
            @click="handleDelete(model.id)"
          >
            <Trash2 class="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>

    <!-- Empty state -->
    <div
      v-if="!modelStore.loading && modelStore.models.length === 0"
      class="text-center py-8 text-muted-foreground"
    >
      <Cpu class="h-8 w-8 mx-auto mb-2 opacity-50" />
      <p class="text-sm">尚未配置任何模型</p>
      <p class="text-[11px] mt-1">点击上方"添加模型"开始配置</p>
    </div>
  </div>
</template>
