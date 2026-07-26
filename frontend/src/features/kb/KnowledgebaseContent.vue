<script setup>
import { ref, onMounted } from 'vue'
import { useKbStore } from '../../stores/useKbStore.js'
import { useToastStore } from '../../stores/useToastStore.js'
import { useConfirmStore } from '../../stores/useConfirmStore.js'
import { X, Plus, Trash2, FolderOpen, Upload, ChevronDown, ChevronRight } from 'lucide-vue-next'

const kbStore = useKbStore()
const toast = useToastStore()
const confirmStore = useConfirmStore()

const showCreate = ref(false)
const expandedKb = ref(null)
const newKb = ref({ name: '', permission: 'me', language: 'zh', description: '' })

const PERMISSION_LABELS = { me: '私有', team: '团队共享' }

async function handleCreate() {
  if (!newKb.value.name.trim()) return
  try {
    await kbStore.createKb(newKb.value)
    toast.success('知识库创建成功')
    showCreate.value = false
    newKb.value = { name: '', permission: 'me', language: 'zh', description: '' }
  } catch (err) {
    toast.error('创建失败: ' + (err.response?.data?.detail || err.message))
  }
}

async function handleDelete(kbId, name) {
  if (!await confirmStore.confirm({ message: `确定删除知识库"${name}"？所有文档将被删除。`, destructive: true })) return
  try {
    await kbStore.deleteKb(kbId)
    toast.success('知识库已删除')
  } catch (err) {
    toast.error('删除失败')
  }
}

async function toggleExpand(kbId) {
  if (expandedKb.value === kbId) {
    expandedKb.value = null
  } else {
    expandedKb.value = kbId
    await kbStore.fetchDocuments(kbId)
  }
}

async function handleUpload(kbId, event) {
  const file = event.target.files[0]
  if (!file) return
  try {
    await kbStore.uploadDocument(kbId, file)
    toast.success('文档上传成功')
    await kbStore.fetchDocuments(kbId)
    await kbStore.fetchKnowledgebases()
  } catch (err) {
    toast.error('上传失败: ' + (err.response?.data?.detail || err.message))
  }
  event.target.value = ''
}

async function handleDeleteDoc(kbId, docId) {
  try {
    await kbStore.deleteDocument(kbId, docId)
    toast.success('文档已删除')
    await kbStore.fetchKnowledgebases()
  } catch (err) {
    toast.error('删除失败')
  }
}

onMounted(() => kbStore.fetchKnowledgebases())
</script>

<template>
  <div class="space-y-3">
    <!-- Create button -->
    <button @click="showCreate = !showCreate"
            class="w-full flex items-center justify-center gap-2 p-3 border-2 border-dashed rounded-lg hover:border-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition text-sm">
      <Plus class="h-4 w-4" /> 创建知识库
    </button>

    <!-- Create form -->
    <div v-if="showCreate" class="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg space-y-3">
      <div>
        <label class="text-xs font-medium text-gray-500">名称</label>
        <input v-model="newKb.name" placeholder="如：产品手册" class="w-full mt-1 px-3 py-2 border rounded text-sm bg-transparent" />
      </div>
      <div>
        <label class="text-xs font-medium text-gray-500">可见性</label>
        <select v-model="newKb.permission" class="w-full mt-1 px-3 py-2 border rounded text-sm bg-transparent">
          <option value="me">私有（仅自己可见）</option>
          <option value="team">团队共享</option>
        </select>
      </div>
      <div>
        <label class="text-xs font-medium text-gray-500">描述</label>
        <input v-model="newKb.description" placeholder="可选" class="w-full mt-1 px-3 py-2 border rounded text-sm bg-transparent" />
      </div>
      <div class="flex gap-2">
        <button @click="handleCreate" class="flex-1 px-3 py-2 bg-blue-500 text-white rounded text-sm hover:bg-blue-600">创建</button>
        <button @click="showCreate = false" class="px-3 py-2 border rounded text-sm">取消</button>
      </div>
    </div>

    <!-- KB list -->
    <div v-for="kb in kbStore.knowledgebases" :key="kb.id"
         class="border rounded-lg overflow-hidden">
      <!-- KB header -->
      <div class="flex items-center justify-between p-3 hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer"
           @click="toggleExpand(kb.id)">
        <div class="flex items-center gap-2 min-w-0">
          <component :is="expandedKb === kb.id ? ChevronDown : ChevronRight" class="h-4 w-4 flex-shrink-0" />
          <div class="min-w-0">
            <div class="flex items-center gap-2">
              <span class="text-sm font-medium truncate">{{ kb.name }}</span>
              <span class="text-xs px-1.5 py-0.5 rounded"
                    :class="kb.permission === 'team' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-500'">
                {{ PERMISSION_LABELS[kb.permission] }}
              </span>
            </div>
            <span class="text-xs text-gray-400">{{ kb.document_count }} 个文档</span>
          </div>
        </div>
        <div class="flex items-center gap-1">
          <label class="p-1.5 hover:bg-gray-200 dark:hover:bg-gray-700 rounded cursor-pointer" @click.stop>
            <Upload class="h-4 w-4 text-gray-400" />
            <input type="file" class="hidden" accept=".pdf,.docx,.txt,.md,.html,.xlsx,.csv,.pptx,.json"
                   @change="(e) => handleUpload(kb.id, e)" />
          </label>
          <button @click.stop="handleDelete(kb.id, kb.name)"
                  class="p-1.5 hover:bg-red-50 dark:hover:bg-red-900/20 rounded">
            <Trash2 class="h-4 w-4 text-gray-400 hover:text-red-500" />
          </button>
        </div>
      </div>

      <!-- Documents list (expanded) -->
      <div v-if="expandedKb === kb.id" class="border-t bg-gray-50/50 dark:bg-gray-800/50">
        <div v-if="kbStore.kbDocuments.length === 0" class="p-4 text-center text-sm text-gray-400">
          暂无文档，点击上传按钮添加
        </div>
        <div v-for="doc in kbStore.kbDocuments" :key="doc.id"
             class="flex items-center justify-between px-4 py-2 border-b last:border-b-0">
          <div class="min-w-0">
            <div class="text-sm truncate">{{ doc.name }}</div>
            <div class="text-xs text-gray-400">
              {{ doc.file_type }} · {{ (doc.file_size / 1024).toFixed(1) }}KB ·
              <span :class="{
                'text-green-600': doc.status === 'completed',
                'text-yellow-600': doc.status === 'pending' || doc.status === 'parsing',
                'text-red-600': doc.status === 'failed',
              }">{{ doc.status }}</span>
              <span v-if="doc.chunk_count"> · {{ doc.chunk_count }} 块</span>
            </div>
          </div>
          <button @click="handleDeleteDoc(kb.id, doc.id)"
                  class="p-1 hover:bg-red-50 dark:hover:bg-red-900/20 rounded">
            <Trash2 class="h-3.5 w-3.5 text-gray-400 hover:text-red-500" />
          </button>
        </div>
      </div>
    </div>

    <!-- Empty state -->
    <div v-if="!kbStore.loading && kbStore.knowledgebases.length === 0"
         class="text-center py-8 text-gray-400">
      <FolderOpen class="h-8 w-8 mx-auto mb-2" />
      <p class="text-sm">尚未创建知识库</p>
    </div>
  </div>
</template>
