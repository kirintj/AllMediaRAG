<script setup>
import { ref, onMounted } from 'vue'
import { useModelStore } from '../../stores/useModelStore.js'
import { useToastStore } from '../../stores/useToastStore.js'
import { useConfirmStore } from '../../stores/useConfirmStore.js'
import {
  ChevronDown, ChevronRight,
  Plus, Trash2, Star, CheckCircle2, AlertCircle,
  Cpu, Loader2, Save, X,
  MessageSquare, Box, ArrowRightLeft, Image, FileText, Volume2, Mic,
} from 'lucide-vue-next'
import Button from '../../components/ui/button.vue'
import Input from '../../components/ui/input.vue'

const modelStore = useModelStore()
const toast = useToastStore()
const confirmStore = useConfirmStore()

// --- Model type configuration ---
const MODEL_TYPES = [
  { key: 'chat',      label: '对话模型',     icon: MessageSquare },
  { key: 'embedding', label: '向量模型',     icon: Box },
  { key: 'rerank',    label: '重排序模型',   icon: ArrowRightLeft },
  { key: 'cv',        label: '视觉模型',     icon: Image },
  { key: 'ocr',       label: 'OCR 模型',     icon: FileText },
  { key: 'tts',       label: '语音合成',     icon: Volume2 },
  { key: 'asr',       label: '语音识别',     icon: Mic },
]

// Which type-block is currently expanded
const expandedType = ref(null)

function toggleType(typeKey) {
  expandedType.value = expandedType.value === typeKey ? null : typeKey
}

// --- Derived data per type ---
function modelsOfType(typeKey) {
  return modelStore.models.filter(m => m.model_type === typeKey)
}

function isTypeConfigured(typeKey) {
  return modelsOfType(typeKey).length > 0
}

function defaultModelOfType(typeKey) {
  const defaultId = modelStore.defaults[typeKey]
  if (!defaultId) return null
  return modelStore.models.find(m => m.id === defaultId)
}

function configStatus(typeKey) {
  const count = modelsOfType(typeKey).length
  const defaultM = defaultModelOfType(typeKey)
  if (count === 0) return { text: '未配置', ok: false }
  if (defaultM) return { text: `默认: ${defaultM.llm_name}`, ok: true }
  return { text: `${count} 个模型`, ok: true }
}

// --- Editing state ---
// Track which model is being edited inline (by id), null = none
const editingModelId = ref(null)
const editForm = ref({ llm_name: '', api_key: '', api_base: '', max_tokens: 8192 })
const savingEdit = ref(false)

// Track add model form per type
const addingForType = ref(null)
const newModel = ref({ llm_name: '', api_key: '', api_base: '' })
const adding = ref(false)

// --- Actions ---

function startEdit(model) {
  editingModelId.value = model.id
  editForm.value = {
    llm_name: model.llm_name || '',
    api_key: model.api_key || '',
    api_base: model.api_base || '',
    max_tokens: model.max_tokens ?? 8192,
  }
}

function cancelEdit() {
  editingModelId.value = null
  editForm.value = { llm_name: '', api_key: '', api_base: '', max_tokens: 8192 }
}

async function saveEdit(modelId) {
  savingEdit.value = true
  try {
    await modelStore.updateModel(modelId, editForm.value)
    toast.success('模型配置已更新')
    editingModelId.value = null
  } catch (err) {
    toast.error('保存失败: ' + (err.response?.data?.detail || err.message))
  } finally {
    savingEdit.value = false
  }
}

async function handleDelete(modelId) {
  if (!await confirmStore.confirm({ message: '确认删除该模型？', destructive: true })) return
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
    toast.success(`默认 ${MODEL_TYPES.find(t => t.key === modelType)?.label || modelType} 已设置`)
  } catch (err) {
    toast.error('设置失败')
  }
}

function startAdd(type) {
  addingForType.value = type
  newModel.value = { llm_name: '', api_key: '', api_base: '' }
}

function cancelAdd() {
  addingForType.value = null
  newModel.value = { llm_name: '', api_key: '', api_base: '' }
}

async function handleAdd() {
  adding.value = true
  try {
    await modelStore.addNewModel({
      ...newModel.value,
      model_type: addingForType.value,
    })
    toast.success('模型添加成功')
    cancelAdd()
  } catch (err) {
    toast.error('添加失败: ' + (err.response?.data?.detail || err.message))
  } finally {
    adding.value = false
  }
}

onMounted(() => {
  modelStore.fetchModels()
  modelStore.fetchModelTypes()
  modelStore.fetchDefaults()
})
</script>

<template>
  <div class="space-y-3">
    <!-- Header -->
    <div class="flex items-center gap-2 mb-2">
      <Cpu class="h-5 w-5 text-foreground" />
      <h2 class="text-lg font-semibold text-foreground">模型管理</h2>
    </div>

    <!-- Loading -->
    <div v-if="modelStore.loading" class="flex items-center justify-center gap-2 py-8 text-muted-foreground">
      <Loader2 class="h-4 w-4 animate-spin" />
      <span class="text-sm">加载中...</span>
    </div>

    <!-- Model type blocks -->
    <div
      v-for="mt in MODEL_TYPES"
      :key="mt.key"
      class="overflow-hidden rounded-xl border border-border/60 bg-card shadow-sm transition-shadow hover:shadow-md"
    >
      <!-- Block header (clickable) -->
      <button
        class="w-full flex items-center gap-3 px-4 py-3.5 text-left transition-colors hover:bg-accent/40"
        @click="toggleType(mt.key)"
      >
        <component :is="mt.icon" class="h-4 w-4 text-muted-foreground" />
        <span class="flex-1 text-sm font-medium text-foreground">{{ mt.label }}</span>

        <!-- Status badge -->
        <span
          v-if="configStatus(mt.key).ok"
          class="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/40 px-2 py-0.5 rounded-full"
        >
          <CheckCircle2 class="h-3 w-3" />
          {{ configStatus(mt.key).text }}
        </span>
        <span
          v-else
          class="inline-flex items-center gap-1 text-[11px] font-medium text-muted-foreground bg-muted px-2 py-0.5 rounded-full"
        >
          <AlertCircle class="h-3 w-3" />
          未配置
        </span>

        <!-- Expand indicator -->
        <component :is="expandedType === mt.key ? ChevronDown : ChevronRight" class="h-4 w-4 text-muted-foreground flex-shrink-0" />
      </button>

      <!-- Expanded panel -->
      <transition name="expand">
        <div
          v-if="expandedType === mt.key"
          class="border-t border-border/60 overflow-hidden"
        >
          <div class="p-4 space-y-3">

            <!-- Existing models -->
            <div v-if="modelsOfType(mt.key).length" class="space-y-2">
              <div
                v-for="model in modelsOfType(mt.key)"
                :key="model.id"
                class="rounded-lg border border-border/40 bg-muted/30 overflow-hidden"
              >
                <!-- Model row (collapsed) -->
                <div v-if="editingModelId !== model.id" class="flex items-center gap-3 px-3 py-2.5">
                  <div class="flex-1 min-w-0">
                    <div class="flex items-center gap-2">
                      <span class="text-sm font-medium text-foreground truncate">{{ model.llm_name }}</span>
                      <span class="text-[11px] text-muted-foreground">{{ model.llm_factory }}</span>
                      <span
                        v-if="defaultModelOfType(mt.key)?.id === model.id"
                        class="text-[10px] font-medium text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/40 px-1.5 py-0.5 rounded"
                      >默认</span>
                    </div>
                    <div class="text-[11px] text-muted-foreground mt-0.5">
                      Tokens: {{ model.used_tokens?.toLocaleString() || 0 }}
                    </div>
                  </div>
                  <div class="flex items-center gap-1">
                    <button
                      v-if="defaultModelOfType(mt.key)?.id !== model.id"
                      class="p-1.5 rounded-md hover:bg-background text-muted-foreground hover:text-amber-500 transition-colors"
                      title="设为默认"
                      @click="handleSetDefault(mt.key, model.id)"
                    >
                      <Star class="h-3.5 w-3.5" />
                    </button>
                    <button
                      class="p-1.5 rounded-md hover:bg-background text-muted-foreground hover:text-foreground transition-colors"
                      title="编辑"
                      @click="startEdit(model)"
                    >
                      <Cpu class="h-3.5 w-3.5" />
                    </button>
                    <button
                      class="p-1.5 rounded-md hover:bg-background text-muted-foreground hover:text-destructive transition-colors"
                      title="删除"
                      @click="handleDelete(model.id)"
                    >
                      <Trash2 class="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>

                <!-- Inline editor (expanded) -->
                <div v-else class="divide-y divide-border/40">
                  <div class="flex items-center gap-3 px-3 py-2.5 bg-muted/50">
                    <div class="flex-1 min-w-0">
                      <span class="text-sm font-medium text-foreground">编辑配置</span>
                    </div>
                    <button
                      class="p-1 rounded-md hover:bg-background text-muted-foreground hover:text-foreground transition-colors"
                      title="取消编辑"
                      @click="cancelEdit"
                    >
                      <X class="h-3.5 w-3.5" />
                    </button>
                  </div>
                  <div class="px-3 py-2.5 space-y-2.5">
                    <div>
                      <label class="text-[11px] font-medium text-muted-foreground">模型名称</label>
                      <Input v-model="editForm.llm_name" placeholder="模型名称" class="mt-0.5 text-sm" />
                    </div>
                    <div>
                      <label class="text-[11px] font-medium text-muted-foreground">API Key</label>
                      <Input v-model="editForm.api_key" type="password" placeholder="sk-..." class="mt-0.5 text-sm" />
                    </div>
                    <div>
                      <label class="text-[11px] font-medium text-muted-foreground">API Base</label>
                      <Input v-model="editForm.api_base" placeholder="https://api.openai.com/v1" class="mt-0.5 text-sm" />
                    </div>
                    <div>
                      <label class="text-[11px] font-medium text-muted-foreground">Max Tokens</label>
                      <Input v-model.number="editForm.max_tokens" type="number" placeholder="8192" class="mt-0.5 text-sm" />
                    </div>
                    <div class="flex gap-2 pt-1">
                      <Button size="sm" :disabled="savingEdit" @click="saveEdit(model.id)" class="flex-1">
                        <Loader2 v-if="savingEdit" class="h-3 w-3 animate-spin mr-1" />
                        <Save v-else class="h-3 w-3 mr-1" />
                        保存
                      </Button>
                      <Button size="sm" variant="outline" @click="cancelEdit">取消</Button>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Empty state for this type -->
            <div v-else class="text-center py-4 text-muted-foreground">
              <p class="text-xs">暂无 {{ mt.label }}</p>
            </div>

            <!-- Add model form (inline) -->
            <div v-if="addingForType === mt.key" class="rounded-lg border border-border/40 bg-muted/20 p-3 space-y-2.5">
              <h4 class="text-xs font-medium text-foreground">添加 {{ mt.label }}</h4>
              <div>
                <label class="text-[11px] font-medium text-muted-foreground">模型名称</label>
                <Input v-model="newModel.llm_name" placeholder="如 gpt-4o" class="mt-0.5 text-sm" />
              </div>
              <div>
                <label class="text-[11px] font-medium text-muted-foreground">API Key</label>
                <Input v-model="newModel.api_key" type="password" placeholder="sk-..." class="mt-0.5 text-sm" />
              </div>
              <div>
                <label class="text-[11px] font-medium text-muted-foreground">API Base (可选)</label>
                <Input v-model="newModel.api_base" placeholder="https://api.openai.com/v1" class="mt-0.5 text-sm" />
              </div>
              <div class="flex gap-2 pt-1">
                <Button size="sm" :disabled="adding || !newModel.llm_name" @click="handleAdd" class="flex-1">
                  <Loader2 v-if="adding" class="h-3 w-3 animate-spin mr-1" />
                  <Plus v-else class="h-3 w-3 mr-1" />
                  添加
                </Button>
                <Button size="sm" variant="outline" @click="cancelAdd">取消</Button>
              </div>
            </div>

            <!-- Add button -->
            <button
              v-if="addingForType !== mt.key"
              class="w-full flex items-center justify-center gap-1.5 py-2 border-2 border-dashed border-border rounded-lg hover:border-primary/40 hover:bg-accent/30 transition-colors text-muted-foreground hover:text-foreground text-xs"
              @click="startAdd(mt.key)"
            >
              <Plus class="h-3.5 w-3.5" />
              添加 {{ mt.label }}
            </button>
          </div>
        </div>
      </transition>
    </div>
  </div>
</template>
