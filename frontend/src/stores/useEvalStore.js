import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getEvalReports, getEvalReport, getMetrics } from '../api/eval.js'

export const useEvalStore = defineStore('eval', () => {
  const reports = ref([])
  const activeReport = ref(null)
  const metrics = ref(null)
  const loading = ref(false)
  const error = ref(null)

  async function fetchReports() {
    loading.value = true
    error.value = null
    try {
      const { data } = await getEvalReports()
      reports.value = data.reports || []
    } catch (e) {
      error.value = e.message
      reports.value = []
    } finally {
      loading.value = false
    }
  }

  async function fetchReportDetail(filename) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getEvalReport(filename)
      activeReport.value = data
    } catch (e) {
      error.value = e.message
      activeReport.value = null
    } finally {
      loading.value = false
    }
  }

  async function fetchMetrics() {
    try {
      const { data } = await getMetrics()
      metrics.value = data
    } catch (e) {
      error.value = e.message
    }
  }

  function clearActiveReport() {
    activeReport.value = null
  }

  return {
    reports,
    activeReport,
    metrics,
    loading,
    error,
    fetchReports,
    fetchReportDetail,
    fetchMetrics,
    clearActiveReport,
  }
})
