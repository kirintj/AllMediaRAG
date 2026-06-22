<template>
  <el-dialog
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
    title="评测与性能仪表盘"
    fullscreen
    :close-on-click-modal="false"
    class="eval-dialog"
  >
    <el-tabs v-model="activeTab" @tab-change="onTabChange">
      <!-- Tab 1: 评测报告 -->
      <el-tab-pane label="评测报告" name="reports">
        <div v-if="evalStore.loading && !evalStore.reports.length" class="loading-state">
          <el-icon class="is-loading" :size="24"><i class="el-icon-loading" /></el-icon>
          <span>加载中...</span>
        </div>

        <div v-else-if="!evalStore.reports.length" class="empty-state">
          <el-empty description="暂无评测报告，请先运行评测脚本生成报告" />
        </div>

        <template v-else>
          <!-- 报告列表 -->
          <el-table
            :data="evalStore.reports"
            stripe
            highlight-current-row
            @row-click="onReportClick"
            style="width: 100%"
          >
            <el-table-column prop="filename" label="文件名" min-width="180" />
            <el-table-column prop="framework" label="框架" width="100">
              <template #default="{ row }">
                <el-tag :type="row.framework === 'ragas' ? 'success' : 'primary'" size="small">
                  {{ row.framework }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="total_samples" label="样本数" width="90" align="center" />
            <el-table-column label="MRR" width="100" align="center">
              <template #default="{ row }">
                {{ fmtMetric(row.metrics?.retrieval?.mrr) }}
              </template>
            </el-table-column>
            <el-table-column label="Recall@K" width="100" align="center">
              <template #default="{ row }">
                {{ fmtMetric(row.metrics?.retrieval?.recall_at_k) }}
              </template>
            </el-table-column>
            <el-table-column label="Faithfulness" width="120" align="center">
              <template #default="{ row }">
                {{ fmtMetric(row.metrics?.generation?.faithfulness) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="100" align="center">
              <template #default="{ row }">
                <el-button link type="primary" size="small" @click.stop="onReportClick(row)">
                  查看详情
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <!-- 报告详情 -->
          <div v-if="evalStore.activeReport" class="report-detail">
            <el-divider content-position="left">报告详情: {{ selectedFilename }}</el-divider>

            <div class="metrics-grid">
              <!-- 检索指标 -->
              <el-card shadow="never" class="metric-card">
                <template #header>检索指标</template>
                <div v-if="evalStore.activeReport.retrieval" class="metric-bars">
                  <div v-for="(val, key) in evalStore.activeReport.retrieval" :key="key" class="metric-row">
                    <span class="metric-label">{{ key }}</span>
                    <el-progress
                      :percentage="Math.round((val || 0) * 100)"
                      :stroke-width="18"
                      :text-inside="true"
                      :color="getProgressColor(val)"
                    />
                  </div>
                </div>
              </el-card>

              <!-- 生成指标 -->
              <el-card shadow="never" class="metric-card">
                <template #header>生成指标</template>
                <div v-if="evalStore.activeReport.generation" class="metric-bars">
                  <div v-for="(val, key) in evalStore.activeReport.generation" :key="key" class="metric-row">
                    <span class="metric-label">{{ key }}</span>
                    <el-progress
                      :percentage="val != null ? Math.round((val / 5) * 100) : 0"
                      :stroke-width="18"
                      :text-inside="true"
                      :color="getProgressColor(val / 5)"
                    />
                    <span class="metric-value">{{ val != null ? val.toFixed(1) + '/5' : 'N/A' }}</span>
                  </div>
                </div>
              </el-card>
            </div>
          </div>
        </template>
      </el-tab-pane>

      <!-- Tab 2: 工程性能 -->
      <el-tab-pane label="工程性能" name="metrics">
        <div v-if="!evalStore.metrics" class="loading-state">
          <el-button @click="evalStore.fetchMetrics()" :loading="evalStore.loading">
            加载性能数据
          </el-button>
        </div>

        <template v-else>
          <!-- 概览卡片 -->
          <div class="stat-cards">
            <el-card shadow="hover" class="stat-card">
              <el-statistic title="请求总数" :value="evalStore.metrics.requests?.total || 0" />
            </el-card>
            <el-card shadow="hover" class="stat-card">
              <el-statistic title="成功率">
                <template #default>
                  <span :style="{ color: successRateColor, fontSize: '28px', fontWeight: '600' }">
                    {{ successRateText }}
                  </span>
                </template>
              </el-statistic>
            </el-card>
            <el-card shadow="hover" class="stat-card">
              <el-statistic title="P95 延迟">
                <template #default>
                  <span style="font-size: 28px; font-weight: 600">
                    {{ evalStore.metrics.latency?.total?.p95 != null ? evalStore.metrics.latency.total.p95 + 'ms' : 'N/A' }}
                  </span>
                </template>
              </el-statistic>
            </el-card>
            <el-card shadow="hover" class="stat-card">
              <el-statistic title="缓存命中率">
                <template #default>
                  <span :style="{ color: cacheRateColor, fontSize: '28px', fontWeight: '600' }">
                    {{ cacheRateText }}
                  </span>
                </template>
              </el-statistic>
            </el-card>
          </div>

          <!-- 延迟详情表格 -->
          <el-card shadow="never" style="margin-top: 16px">
            <template #header>
              <div style="display: flex; justify-content: space-between; align-items: center">
                <span>各阶段延迟 (ms)</span>
                <el-button link type="primary" size="small" @click="evalStore.fetchMetrics()">
                  刷新
                </el-button>
              </div>
            </template>
            <el-table :data="latencyRows" stripe style="width: 100%">
              <el-table-column prop="stage" label="阶段" width="140" />
              <el-table-column prop="avg" label="平均" width="100" align="center" />
              <el-table-column prop="p50" label="P50" width="100" align="center" />
              <el-table-column prop="p95" label="P95" width="100" align="center" />
            </el-table>
          </el-card>

          <!-- 缓存统计 -->
          <el-card shadow="never" style="margin-top: 16px">
            <template #header>缓存统计</template>
            <el-descriptions :column="3" border>
              <el-descriptions-item label="命中次数">{{ evalStore.metrics.cache?.hits || 0 }}</el-descriptions-item>
              <el-descriptions-item label="未命中次数">{{ evalStore.metrics.cache?.misses || 0 }}</el-descriptions-item>
              <el-descriptions-item label="命中率">{{ cacheRateText }}</el-descriptions-item>
            </el-descriptions>
          </el-card>
        </template>
      </el-tab-pane>
    </el-tabs>
  </el-dialog>
</template>

<script setup>
import { ref, computed, onUnmounted, watch } from 'vue'
import { useEvalStore } from '../../stores/useEvalStore.js'

const props = defineProps({
  modelValue: { type: Boolean, default: false }
})
defineEmits(['update:modelValue'])

const evalStore = useEvalStore()
const activeTab = ref('reports')
const selectedFilename = ref(null)
let metricsTimer = null

// ── 格式化 ──

function fmtMetric(val) {
  if (val == null) return 'N/A'
  return typeof val === 'number' ? val.toFixed(3) : val
}

function getProgressColor(val) {
  if (val == null) return '#909399'
  if (val >= 0.8) return '#67c23a'
  if (val >= 0.5) return '#e6a23c'
  return '#f56c6c'
}

// ── 计算属性 ──

const successRate = computed(() => {
  const r = evalStore.metrics?.requests
  if (!r || !r.total) return null
  return r.success_rate
})

const successRateText = computed(() => {
  return successRate.value != null ? (successRate.value * 100).toFixed(1) + '%' : 'N/A'
})

const successRateColor = computed(() => {
  if (successRate.value == null) return '#909399'
  return successRate.value >= 0.95 ? '#67c23a' : successRate.value >= 0.8 ? '#e6a23c' : '#f56c6c'
})

const cacheRate = computed(() => {
  return evalStore.metrics?.cache?.hit_rate ?? null
})

const cacheRateText = computed(() => {
  return cacheRate.value != null ? (cacheRate.value * 100).toFixed(1) + '%' : 'N/A'
})

const cacheRateColor = computed(() => {
  if (cacheRate.value == null) return '#909399'
  return cacheRate.value >= 0.7 ? '#67c23a' : cacheRate.value >= 0.4 ? '#e6a23c' : '#f56c6c'
})

const latencyRows = computed(() => {
  const lat = evalStore.metrics?.latency
  if (!lat) return []
  const stages = [
    { key: 'classify', label: '意图分类' },
    { key: 'search', label: '向量+BM25 检索' },
    { key: 'rerank', label: '重排序' },
    { key: 'total', label: '检索总计' },
    { key: 'generation', label: 'LLM 生成' },
  ]
  return stages
    .filter(s => lat[s.key])
    .map(s => ({
      stage: s.label,
      avg: lat[s.key].avg != null ? lat[s.key].avg.toFixed(1) : '-',
      p50: lat[s.key].p50 != null ? lat[s.key].p50.toFixed(1) : '-',
      p95: lat[s.key].p95 != null ? lat[s.key].p95.toFixed(1) : '-',
    }))
})

// ── 交互 ──

function onReportClick(row) {
  selectedFilename.value = row.filename
  evalStore.fetchReportDetail(row.filename)
}

function onTabChange(tab) {
  if (tab === 'reports' && !evalStore.reports.length) {
    evalStore.fetchReports()
  } else if (tab === 'metrics') {
    evalStore.fetchMetrics()
    startMetricsPolling()
  }
}

function startMetricsPolling() {
  stopMetricsPolling()
  metricsTimer = setInterval(() => {
    if (props.modelValue && activeTab.value === 'metrics') {
      evalStore.fetchMetrics()
    }
  }, 30000)
}

function stopMetricsPolling() {
  if (metricsTimer) {
    clearInterval(metricsTimer)
    metricsTimer = null
  }
}

// ── 生命周期 ──

watch(() => props.modelValue, (open) => {
  if (open) {
    evalStore.fetchReports()
    if (activeTab.value === 'metrics') {
      evalStore.fetchMetrics()
      startMetricsPolling()
    }
  } else {
    stopMetricsPolling()
  }
})

onUnmounted(() => {
  stopMetricsPolling()
})
</script>

<style scoped>
.eval-dialog :deep(.el-dialog__body) {
  padding: 16px 24px;
  background: var(--el-bg-color-page, #f5f7fa);
}

.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 0;
  gap: 12px;
  color: var(--el-text-color-secondary);
}

.report-detail {
  margin-top: 20px;
}

.metrics-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.metric-bars {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.metric-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.metric-label {
  width: 140px;
  font-size: 13px;
  color: var(--el-text-color-regular);
  flex-shrink: 0;
}

.metric-row .el-progress {
  flex: 1;
}

.metric-value {
  width: 60px;
  text-align: right;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.stat-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.stat-card {
  text-align: center;
}

@media (max-width: 900px) {
  .metrics-grid {
    grid-template-columns: 1fr;
  }
  .stat-cards {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
