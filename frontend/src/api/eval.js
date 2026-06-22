import api from './index.js'

export const getEvalReports = () => api.get('/eval/reports')

export const getEvalReport = (filename) => api.get(`/eval/reports/${filename}`)

export const getMetrics = () => api.get('/metrics')
