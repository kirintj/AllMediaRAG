import { ref } from 'vue'
import { defineStore } from 'pinia'

export const useKbStore = defineStore('kb', () => {
  const knowledgebases = ref([])
  const activeKb = ref(null)
  const kbDocuments = ref([])
  const loading = ref(false)

  async function fetchKnowledgebases() {
    loading.value = true
    try {
      const { listKnowledgebases } = await import('../api/knowledgebases.js')
      const data = await listKnowledgebases()
      knowledgebases.value = data.knowledgebases || []
    } finally {
      loading.value = false
    }
  }

  async function createKb(params) {
    const { createKnowledgebase } = await import('../api/knowledgebases.js')
    const data = await createKnowledgebase(params)
    await fetchKnowledgebases()
    return data
  }

  async function deleteKb(kbId) {
    const { deleteKnowledgebase } = await import('../api/knowledgebases.js')
    await deleteKnowledgebase(kbId)
    await fetchKnowledgebases()
  }

  async function fetchDocuments(kbId) {
    const { listKBDocuments } = await import('../api/knowledgebases.js')
    const data = await listKBDocuments(kbId)
    kbDocuments.value = data.documents || []
  }

  async function uploadDocument(kbId, file) {
    const { uploadToKB } = await import('../api/knowledgebases.js')
    return await uploadToKB(kbId, file)
  }

  async function deleteDocument(kbId, docId) {
    const { deleteKBDocument } = await import('../api/knowledgebases.js')
    await deleteKBDocument(kbId, docId)
    await fetchDocuments(kbId)
  }

  return {
    knowledgebases, activeKb, kbDocuments, loading,
    fetchKnowledgebases, createKb, deleteKb,
    fetchDocuments, uploadDocument, deleteDocument,
  }
})
