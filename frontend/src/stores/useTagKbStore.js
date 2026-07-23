import { ref } from 'vue'
import { defineStore } from 'pinia'

export const useTagKbStore = defineStore('tagKb', () => {
  const tagKbs = ref([])
  const loading = ref(false)
  const selectedTags = ref({})

  async function fetchTagKbs() {
    loading.value = true
    try {
      const { listTagKbs } = await import('../api/tagKb.js')
      const data = await listTagKbs()
      tagKbs.value = data.tag_kbs || []
    } finally {
      loading.value = false
    }
  }

  async function upload(file) {
    const { uploadTagFile } = await import('../api/tagKb.js')
    const data = await uploadTagFile(file)
    await fetchTagKbs()
    return data
  }

  async function remove(tagKbId) {
    const { deleteTagKb } = await import('../api/tagKb.js')
    await deleteTagKb(tagKbId)
    await fetchTagKbs()
  }

  async function fetchTags(tagKbId) {
    const { getTagKbTags } = await import('../api/tagKb.js')
    const data = await getTagKbTags(tagKbId)
    selectedTags.value[tagKbId] = data.tags || {}
    return data.tags
  }

  return { tagKbs, loading, selectedTags, fetchTagKbs, upload, remove, fetchTags }
})
