<template>
  <DialogRoot :open="modelValue" @update:open="$emit('update:modelValue', $event)">
    <DialogPortal>
      <DialogOverlay class="fixed inset-0 z-50 bg-black/80 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0" />
      <DialogContent class="fixed left-1/2 top-1/2 z-50 w-[90vw] max-w-5xl max-h-[85vh] -translate-x-1/2 -translate-y-1/2 border bg-background shadow-lg sm:rounded-lg flex flex-col overflow-hidden">
        <!-- Header -->
        <div class="flex items-center justify-between px-6 py-4 border-b border-border">
          <h2 class="text-lg font-semibold text-foreground">评测与性能仪表盘</h2>
          <DialogClose class="rounded-sm opacity-70 hover:opacity-100 transition-opacity">
            <X class="h-4 w-4" />
          </DialogClose>
        </div>

        <!-- Body -->
        <div class="flex-1 overflow-y-auto p-6">
          <TabsRoot v-model="activeTab" default-value="reports" @update:model-value="onTabChange">
            <TabsList class="mb-4">
              <TabsTrigger value="reports">评测报告</TabsTrigger>
              <TabsTrigger value="metrics">工程性能</TabsTrigger>
            </TabsList>

            <!-- Reports tab -->
            <TabsContent value="reports">
              <div v-if="evalStore.loading && !evalStore.reports.length" class="flex items-center justify-center py-16 text-muted-foreground">
                <Loader2 class="h-5 w-5 animate-spin mr-2" />
                加载中...
              </div>

              <div v-else-if="!evalStore.reports.length" class="text-center py-16 text-muted-foreground">
                暂无评测报告，请先运行评测脚本生成报告
              </div>

              <template v-else>
                <!-- Reports table -->
                <div class="border rounded-lg overflow-hidden">
                  <table class="w-full text-sm">
                    <thead class="bg-muted">
                      <tr>
                        <th class="px-3 py-2 text-left font-medium text-muted-foreground">文件名</th>
                        <th class="px-3 py-2 text-left font-medium text-muted-foreground">框架</th>
                        <th class="px-3 py-2 text-center font-medium text-muted-foreground">样本数</th>
                        <th class="px-3 py-2 text-center font-medium text-muted-foreground">MRR</th>
                        <th class="px-3 py-2 text-center font-medium text-muted-foreground">Recall@K</th>
                        <th class="px-3 py-2 text-center font-medium text-muted-foreground">Faithfulness</th>
                        <th class="px-3 py-2 text-center font-medium text-muted-foreground">操作</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr
                        v-for="row in evalStore.reports"
                        :key="row.filename"
                        class="border-t border-border hover:bg-accent/50 cursor-pointer transition-colors"
                        @click="onReportClick(row)"
                      >
                        <td class="px-3 py-2 text-foreground">{{ row.filename }}</td>
                        <td class="px-3 py-2">
                          <span class="inline-block px-2 py-0.5 rounded-full text-[11px] font-medium"
                            :class="row.framework === 'ragas' ? 'bg-green-100 text-green-700 dark:bg-green-950 dark:text-green-300' : 'bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300'"
                          >
                            {{ row.framework }}
                          </span>
                        </td>
                        <td class="px-3 py-2 text-center">{{ row.total_samples }}</td>
                        <td class="px-3 py-2 text-center font-mono text-xs">{{ fmtMetric(row.metrics?.retrieval?.mrr) }}</td>
                        <td class="px-3 py-2 text-center font-mono text-xs">{{ fmtMetric(row.metrics?.retrieval?.recall_at_k) }}</td>
                        <td class="px-3 py-2 text-center font-mono text-xs">{{ fmtMetric(row.metrics?.generation?.faithfulness) }}</td>
                        <td class="px-3 py-2 text-center">
                          <button class="text-primary text-xs hover:underline" @click.stop="onReportClick(row)">详情</button>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                <!-- Report detail -->
                <div v-if="evalStore.activeReport" class="mt-6">
                  <h3 class="text-sm font-semibold text-foreground mb-4 pb-2 border-b border-border">
                    报告详情: {{ selectedFilename }}
                  </h3>
                  <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div class="border rounded-lg p-4">
                      <h4 class="text-sm font-medium text-foreground mb-3">检索指标</h4>
                      <div v-if="evalStore.activeReport.retrieval" class="space-y-2">
                        <div v-for="(val, key) in evalStore.activeReport.retrieval" :key="key" class="flex items-center gap-3">
                          <span class="w-28 text-xs text-muted-foreground shrink-0">{{ key }}</span>
                          <div class="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                            <div class="h-full rounded-full transition-all" :style="{ width: ((val || 0) * 100) + '%', background: getProgressColor(val) }" />
                          </div>
                          <span class="text-xs font-mono text-muted-foreground w-10 text-right">{{ ((val || 0) * 100).toFixed(0) }}%</span>
                        </div>
                      </div>
                    </div>
                    <div class="border rounded-lg p-4">
                      <h4 class="text-sm font-medium text-foreground mb-3">生成指标</h4>
                      <div v-if="evalStore.activeReport.generation" class="space-y-2">
                        <div v-for="(val, key) in evalStore.activeReport.generation" :key="key" class="flex items-center gap-3">
                          <span class="w-28 text-xs text-muted-foreground shrink-0">{{ key }}</span>
                          <div class="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                            <div class="h-full rounded-full transition-all" :style="{ width: (val != null ? (val / 5) * 100 : 0) + '%', background: getProgressColor(val / 5) }" />
                          </div>
                          <span class="text-xs font-mono text-muted-foreground w-12 text-right">{{ val != null ? val.toFixed(1) + '/5' : 'N/A' }}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </template>
            </TabsContent>

            <!-- Metrics tab -->
            <TabsContent value="metrics">
              <div v-if="!evalStore.metrics" class="text-center py-16">
                <button
                  class="h-9 px-4 rounded-md bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors"
                  @click="evalStore.fetchMetrics()"
                >
                  加载性能数据
                </button>
              </div>

              <template v-else>
                <!-- Stat cards -->
                <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                  <div class="border rounded-lg p-4 text-center">
                    <div class="text-2xl font-bold text-foreground">{{ evalStore.metrics.requests?.total || 0 }}</div>
                    <div class="text-xs text-muted-foreground mt-1">请求总数</div>
                  </div>
                  <div class="border rounded-lg p-4 text-center">
                    <div class="text-2xl font-bold" :class="successRateClass">{{ successRateText }}</div>
                    <div class="text-xs text-muted-foreground mt-1">成功率</div>
                  </div>
                  <div class="border rounded-lg p-4 text-center">
                    <div class="text-2xl font-bold text-foreground">
                      {{ evalStore.metrics.latency?.total?.p95 != null ? evalStore.metrics.latency.total.p95 + 'ms' : 'N/A' }}
                    </div>
                    <div class="text-xs text-muted-foreground mt-1">P95 延迟</div>
                  </div>
                  <div class="border rounded-lg p-4 text-center">
                    <div class="text-2xl font-bold" :class="cacheRateClass">{{ cacheRateText }}</div>
                    <div class="text-xs text-muted-foreground mt-1">缓存命中率</div>
                  </div>
                </div>

                <!-- Latency table -->
                <div class="border rounded-lg overflow-hidden mb-4">
                  <div class="flex items-center justify-between px-3 py-2 bg-muted">
                    <span class="text-sm font-medium text-foreground">各阶段延迟 (ms)</span>
                    <button class="text-xs text-primary hover:underline" @click="evalStore.fetchMetrics()">刷新</button>
                  </div>
                  <table class="w-full text-sm">
                    <thead class="bg-muted/50">
                      <tr>
                        <th class="px-3 py-1.5 text-left font-medium text-muted-foreground text-xs">阶段</th>
                        <th class="px-3 py-1.5 text-center font-medium text-muted-foreground text-xs">平均</th>
                        <th class="px-3 py-1.5 text-center font-medium text-muted-foreground text-xs">P50</th>
                        <th class="px-3 py-1.5 text-center font-medium text-muted-foreground text-xs">P95</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="row in latencyRows" :key="row.stage" class="border-t border-border">
                        <td class="px-3 py-1.5">{{ row.stage }}</td>
                        <td class="px-3 py-1.5 text-center font-mono text-xs">{{ row.avg }}</td>
                        <td class="px-3 py-1.5 text-center font-mono text-xs">{{ row.p50 }}</td>
                        <td class="px-3 py-1.5 text-center font-mono text-xs">{{ row.p95 }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                <!-- Cache stats -->
                <div class="border rounded-lg p-4">
                  <h4 class="text-sm font-medium text-foreground mb-3">缓存统计</h4>
                  <div class="grid grid-cols-3 gap-4 text-sm">
                    <div>
                      <span class="text-muted-foreground">命中次数:</span>
                      <span class="ml-1 font-medium">{{ evalStore.metrics.cache?.hits || 0 }}</span>
                    </div>
                    <div>
                      <span class="text-muted-foreground">未命中:</span>
                      <span class="ml-1 font-medium">{{ evalStore.metrics.cache?.misses || 0 }}</span>
                    </div>
                    <div>
                      <span class="text-muted-foreground">命中率:</span>
                      <span class="ml-1 font-medium">{{ cacheRateText }}</span>
                    </div>
                  </div>
                </div>
              </template>
            </TabsContent>
          </TabsRoot>
        </div>
      </DialogContent>
    </DialogPortal>
  </DialogRoot>
</template>

<script setup>
import { ref, computed, watch, onUnmounted } from 'vue'
import { DialogRoot, DialogPortal, DialogOverlay, DialogContent, DialogClose } from 'radix-vue'
import { X, Loader2 } from 'lucide-vue-next'
import TabsRoot from '../../components/ui/tabs.vue'
import TabsList from '../../components/ui/tabs-list.vue'
import TabsTrigger from '../../components/ui/tabs-trigger.vue'
import TabsContent from '../../components/ui/tabs-content.vue'
import { useEvalStore } from '../../stores/useEvalStore.js'

const props = defineProps({ modelValue: { type: Boolean, default: false } })
defineEmits(['update:modelValue'])

const evalStore = useEvalStore()
const activeTab = ref('reports')
const selectedFilename = ref(null)
let metricsTimer = null

function fmtMetric(val) {
  if (val == null) return 'N/A'
  return typeof val === 'number' ? val.toFixed(3) : val
}

function getProgressColor(val) {
  if (val == null) return 'hsl(var(--muted-foreground))'
  if (val >= 0.8) return 'hsl(142 71% 45%)'
  if (val >= 0.5) return 'hsl(38 92% 50%)'
  return 'hsl(0 84% 60%)'
}

const successRate = computed(() => evalStore.metrics?.requests?.success_rate ?? null)
const successRateText = computed(() => successRate.value != null ? (successRate.value * 100).toFixed(1) + '%' : 'N/A')
const successRateClass = computed(() => {
  if (successRate.value == null) return 'text-muted-foreground'
  return successRate.value >= 0.95 ? 'text-green-600 dark:text-green-400' : successRate.value >= 0.8 ? 'text-yellow-600 dark:text-yellow-400' : 'text-red-600 dark:text-red-400'
})

const cacheRate = computed(() => evalStore.metrics?.cache?.hit_rate ?? null)
const cacheRateText = computed(() => cacheRate.value != null ? (cacheRate.value * 100).toFixed(1) + '%' : 'N/A')
const cacheRateClass = computed(() => {
  if (cacheRate.value == null) return 'text-muted-foreground'
  return cacheRate.value >= 0.7 ? 'text-green-600 dark:text-green-400' : cacheRate.value >= 0.4 ? 'text-yellow-600 dark:text-yellow-400' : 'text-red-600 dark:text-red-400'
})

const latencyRows = computed(() => {
  const lat = evalStore.metrics?.latency
  if (!lat) return []
  return [
    { key: 'classify', label: '意图分类' },
    { key: 'search', label: '向量+BM25 检索' },
    { key: 'rerank', label: '重排序' },
    { key: 'total', label: '检索总计' },
    { key: 'generation', label: 'LLM 生成' },
  ].filter(s => lat[s.key]).map(s => ({
    stage: s.label,
    avg: lat[s.key].avg?.toFixed(1) ?? '-',
    p50: lat[s.key].p50?.toFixed(1) ?? '-',
    p95: lat[s.key].p95?.toFixed(1) ?? '-',
  }))
})

function onReportClick(row) {
  selectedFilename.value = row.filename
  evalStore.fetchReportDetail(row.filename)
}

function onTabChange(tab) {
  if (tab === 'reports' && !evalStore.reports.length) evalStore.fetchReports()
  else if (tab === 'metrics') { evalStore.fetchMetrics(); startMetricsPolling() }
}

function startMetricsPolling() {
  stopMetricsPolling()
  metricsTimer = setInterval(() => {
    if (props.modelValue && activeTab.value === 'metrics') evalStore.fetchMetrics()
  }, 30000)
}

function stopMetricsPolling() {
  if (metricsTimer) { clearInterval(metricsTimer); metricsTimer = null }
}

watch(() => props.modelValue, (open) => {
  if (open) {
    evalStore.fetchReports()
    if (activeTab.value === 'metrics') { evalStore.fetchMetrics(); startMetricsPolling() }
  } else {
    stopMetricsPolling()
  }
})

onUnmounted(() => stopMetricsPolling())
</script>
