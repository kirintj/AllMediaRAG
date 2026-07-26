<script setup>
import { ref, onMounted } from 'vue'
import { useTagKbStore } from '../../stores/useTagKbStore.js'
import { useToastStore } from '../../stores/useToastStore.js'
import { useConfirmStore } from '../../stores/useConfirmStore.js'
import { Upload, Trash2, Loader2, Tags, ChevronDown, ChevronRight, X, FileSpreadsheet } from 'lucide-vue-next'

const tagKbStore = useTagKbStore()
const toast = useToastStore()
const confirmStore = useConfirmStore()

const fileInputRef = ref(null)
const uploading = ref(false)
const expandedId = ref(null)
const loadingTags = ref(false)

function triggerFileInput() {
  fileInputRef.value?.click()
}

async function handleFileSelect(e) {
  const file = e.target.files?.[0]
  if (!file) return
  await uploadFile(file)
}

async function handleDrop(e) {
  const file = e.dataTransfer?.files?.[0]
  if (!file) return
  await uploadFile(file)
}

async function uploadFile(file) {
  uploading.value = true
  try {
    await tagKbStore.upload(file)
    toast.success('标签知识库上传成功')
  } catch (err) {
    toast.error('上传失败: ' + (err.response?.data?.detail || err.message))
  } finally {
    uploading.value = false
    if (fileInputRef.value) fileInputRef.value.value = ''
  }
}

async function handleDelete(tagKbId) {
  if (!await confirmStore.confirm({ message: '确认删除该标签知识库？', destructive: true })) return
  try {
    await tagKbStore.remove(tagKbId)
    toast.success('已删除')
    if (expandedId.value === tagKbId) expandedId.value = null
  } catch (err) {
    toast.error('删除失败')
  }
}

async function toggleExpand(tagKbId) {
  if (expandedId.value === tagKbId) {
    expandedId.value = null
    return
  }
  expandedId.value = tagKbId
  if (!tagKbStore.selectedTags[tagKbId]) {
    loadingTags.value = true
    try {
      await tagKbStore.fetchTags(tagKbId)
    } catch (err) {
      toast.error('加载标签失败')
    } finally {
      loadingTags.value = false
    }
  }
}

onMounted(() => {
  tagKbStore.fetchTagKbs()
})
</script>

<template>
  <div class="space-y-4">
    <!-- Header -->
    <div class="flex items-center gap-2">
      <Tags class="h-5 w-5 text-foreground" />
      <h2 class="text-lg font-semibold text-foreground">标签知识库</h2>
    </div>

    <!-- Upload area -->
    <div
      class="border-2 border-dashed border-border rounded-lg p-6 text-center cursor-pointer hover:border-primary/50 hover:bg-accent/50 transition-colors"
      @dragover.prevent
      @drop.prevent="handleDrop"
      @click="triggerFileInput"
    >
      <Upload class="h-8 w-8 mx-auto text-muted-foreground mb-2" />
      <p class="text-sm text-muted-foreground">拖拽文件到此处或点击上传</p>
      <p class="text-[11px] text-muted-foreground/70 mt-1">支持 .xlsx、.csv 格式</p>
      <input
        ref="fileInputRef"
        type="file"
        class="hidden"
        accept=".xlsx,.csv"
        @change="handleFileSelect"
      />
    </div>

    <!-- Upload progress -->
    <div v-if="uploading" class="flex items-center gap-2 px-3 py-2 bg-muted rounded-lg">
      <Loader2 class="h-4 w-4 animate-spin text-primary" />
      <span class="text-sm text-muted-foreground">上传中...</span>
    </div>

    <!-- Separator -->
    <div class="h-px w-full shrink-0 bg-border" />

    <!-- Tag KB list -->
    <div class="flex-1 min-h-0 overflow-y-auto">
      <div class="flex items-center justify-between mb-2">
        <span class="text-xs font-medium text-muted-foreground uppercase tracking-wider">标签知识库列表</span>
        <button
          class="text-[11px] text-muted-foreground hover:text-foreground transition-colors"
          @click="tagKbStore.fetchTagKbs()"
        >
          刷新
        </button>
      </div>

      <!-- Loading -->
      <div v-if="tagKbStore.loading" class="flex items-center justify-center gap-2 py-4 text-muted-foreground">
        <Loader2 class="h-4 w-4 animate-spin" />
        <span class="text-sm">加载中...</span>
      </div>

      <!-- Empty -->
      <div v-else-if="!tagKbStore.tagKbs.length" class="text-center py-8 text-sm text-muted-foreground">
        <FileSpreadsheet class="h-8 w-8 mx-auto mb-2 opacity-50" />
        <p>暂无标签知识库</p>
        <p class="text-[11px] mt-1">上传 .xlsx 或 .csv 文件开始</p>
      </div>

      <!-- List -->
      <div v-else class="flex flex-col gap-1">
        <div v-for="kb in tagKbStore.tagKbs" :key="kb.tag_kb_id">
          <!-- KB item -->
          <div
            class="group flex items-center gap-2 px-2 py-2 rounded-md hover:bg-accent transition-colors cursor-pointer"
            @click="toggleExpand(kb.tag_kb_id)"
          >
            <component
              :is="expandedId === kb.tag_kb_id ? ChevronDown : ChevronRight"
              class="h-3.5 w-3.5 text-muted-foreground flex-shrink-0"
            />
            <FileSpreadsheet class="h-3.5 w-3.5 text-muted-foreground flex-shrink-0" />
            <div class="flex-1 min-w-0">
              <span class="text-[13px] text-foreground truncate block">{{ kb.tag_kb_id }}</span>
              <span class="text-[11px] text-muted-foreground">{{ kb.chunk_count || 0 }} 个分块</span>
            </div>
            <button
              class="flex-shrink-0 h-5 w-5 flex items-center justify-center rounded opacity-0 group-hover:opacity-100 hover:bg-destructive/10 hover:text-destructive transition-all"
              @click.stop="handleDelete(kb.tag_kb_id)"
              title="删除"
            >
              <X class="h-3 w-3" />
            </button>
          </div>

          <!-- Expanded tags -->
          <div v-if="expandedId === kb.tag_kb_id" class="ml-7 mr-2 mb-1">
            <div v-if="loadingTags && !tagKbStore.selectedTags[kb.tag_kb_id]" class="flex items-center gap-2 py-2 text-muted-foreground">
              <Loader2 class="h-3 w-3 animate-spin" />
              <span class="text-[11px]">加载标签中...</span>
            </div>
            <div v-else-if="tagKbStore.selectedTags[kb.tag_kb_id]" class="flex flex-wrap gap-1 py-1">
              <span
                v-for="(description, tag) in tagKbStore.selectedTags[kb.tag_kb_id]"
                :key="tag"
                class="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] bg-primary/10 text-primary"
                :title="description"
              >
                {{ tag }}
              </span>
              <span
                v-if="Object.keys(tagKbStore.selectedTags[kb.tag_kb_id]).length === 0"
                class="text-[11px] text-muted-foreground"
              >
                无标签
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
