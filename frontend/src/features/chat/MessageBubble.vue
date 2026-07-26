<template>
  <div
    class="mb-5 flex animate-in fade-in-0 slide-in-from-bottom-1 duration-300"
    :style="{ animationDelay: `${Math.min(index * 0.06, 0.3)}s` }"
  >
    <!-- User message: right-aligned pill -->
    <div v-if="message.role === 'user'" class="ml-auto max-w-[min(85%,36rem)] min-w-0">
      <div class="rounded-[18px] bg-secondary/70 px-4 py-2 text-base leading-[1.75] whitespace-pre-wrap text-foreground">
        {{ message.content }}
      </div>
    </div>

    <!-- Assistant message: left-aligned prose -->
    <div v-else class="w-full">
      <!-- Loading dots -->
      <div v-if="message.loading && !message.content" class="flex items-center gap-1.5 py-1">
        <span class="w-2 h-2 rounded-full bg-primary/60 animate-bounce" style="animation-delay: 0s" />
        <span class="w-2 h-2 rounded-full bg-primary/60 animate-bounce" style="animation-delay: 0.15s" />
        <span class="w-2 h-2 rounded-full bg-primary/60 animate-bounce" style="animation-delay: 0.3s" />
      </div>

      <template v-else>
        <MarkdownRenderer :content="message.content" />

        <!-- Sources -->
        <div v-if="message.sources && message.sources.length > 0" class="mt-2 p-2.5 bg-muted rounded-lg border border-border">
          <div class="flex items-center gap-1 text-[11px] font-medium text-muted-foreground mb-1.5">
            <BookOpen class="h-3.5 w-3.5" />
            <span>参考来源</span>
          </div>
          <div class="flex flex-wrap gap-1">
            <span
              v-for="(source, idx) in message.sources"
              :key="idx"
              class="inline-block px-2 py-0.5 rounded-full bg-background border border-border text-[11px] text-muted-foreground"
            >
              {{ (source.section && source.section !== '概述') ? source.section : cleanSourceName(source.source) }}
            </span>
          </div>
        </div>

        <!-- Verification -->
        <div v-if="message.verification" class="mt-2 p-2.5 bg-muted rounded-lg border border-border">
          <div
            class="flex items-center gap-1 text-[11px] font-medium text-muted-foreground cursor-pointer select-none hover:text-foreground transition-colors"
            @click="showVerification = !showVerification"
          >
            <ShieldCheck class="h-3.5 w-3.5" />
            <span>引用核查</span>
            <span
              class="ml-auto px-1.5 py-px rounded-full text-[10px] font-medium"
              :class="{
                'bg-green-100 text-green-700 dark:bg-green-950 dark:text-green-300': riskClass === 'low',
                'bg-yellow-100 text-yellow-700 dark:bg-yellow-950 dark:text-yellow-300': riskClass === 'medium',
                'bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300': riskClass === 'high',
              }"
            >
              {{ riskText }}
            </span>
            <ChevronDown class="h-3 w-3 transition-transform" :class="{ 'rotate-180': showVerification }" />
          </div>

          <div v-if="showVerification" class="mt-2 pt-2 border-t border-border space-y-1.5">
            <div class="grid grid-cols-[80px_1fr_40px] items-center gap-1.5 text-[11px]">
              <span class="text-muted-foreground text-right">置信度:</span>
              <span class="text-right font-medium col-span-2">{{ (message.verification.confidence * 100).toFixed(0) }}%</span>
            </div>

            <!-- Retrieval metrics -->
            <template v-if="message.verification.retrieval_metrics">
              <div class="text-[11px] font-medium text-muted-foreground pt-1.5 border-t border-border">检索质量</div>
              <div class="grid grid-cols-[80px_1fr_40px] items-center gap-1.5 text-[11px]">
                <span class="text-muted-foreground text-right">文档数量:</span>
                <span class="text-right font-medium col-span-2">{{ message.verification.retrieval_metrics.doc_count }}</span>
              </div>
              <MetricRow
                v-if="message.verification.retrieval_metrics.max_similarity != null"
                label="最高相似度"
                :value="message.verification.retrieval_metrics.max_similarity"
              />
              <MetricRow
                v-if="message.verification.retrieval_metrics.avg_similarity != null"
                label="平均相似度"
                :value="message.verification.retrieval_metrics.avg_similarity"
              />
              <MetricRow
                v-if="message.verification.retrieval_metrics.stability != null"
                label="稳定性"
                :value="message.verification.retrieval_metrics.stability"
              />
            </template>

            <!-- Faithfulness metrics -->
            <template v-if="message.verification.faithfulness_metrics">
              <div class="text-[11px] font-medium text-muted-foreground pt-1.5 border-t border-border">忠实度</div>
              <MetricRow
                v-if="message.verification.faithfulness_metrics.support_ratio != null"
                label="支撑比例"
                :value="message.verification.faithfulness_metrics.support_ratio"
              />
              <div v-if="message.verification.faithfulness_metrics.claim_count != null" class="grid grid-cols-[80px_1fr_40px] items-center gap-1.5 text-[11px]">
                <span class="text-muted-foreground text-right">有支撑断言:</span>
                <span class="text-right font-medium col-span-2">{{ message.verification.faithfulness_metrics.supported_count }}/{{ message.verification.faithfulness_metrics.claim_count }}</span>
              </div>
            </template>

            <!-- Context coverage -->
            <MetricRow
              v-if="message.verification.context_coverage != null"
              label="上下文覆盖"
              :value="message.verification.context_coverage"
            />

            <!-- Disclaimer -->
            <div v-if="message.verification.suggested_disclaimer" class="mt-1.5 p-2 bg-yellow-50 dark:bg-yellow-950/30 rounded text-[11px] text-muted-foreground leading-relaxed">
              {{ message.verification.suggested_disclaimer }}
            </div>
          </div>
        </div>

        <!-- Elapsed time -->
        <div v-if="message.elapsed != null" class="flex items-center gap-1 mt-1.5 text-[11px] text-muted-foreground/70">
          <Clock class="h-3 w-3" />
          <span>{{ formattedElapsed }}</span>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { BookOpen, ShieldCheck, ChevronDown, Clock } from 'lucide-vue-next'
import MarkdownRenderer from './MarkdownRenderer.vue'
import MetricRow from './MetricRow.vue'

const props = defineProps({
  message: { type: Object, required: true },
  index: { type: Number, default: 0 },
})

const showVerification = ref(false)

function cleanSourceName(name) {
  if (!name) return ''
  return name.replace(/\.[^.]+$/, '')
}

const riskClass = computed(() => {
  if (!props.message.verification) return ''
  const risk = props.message.verification.hallucination_risk
  if (risk === 'high') return 'high'
  if (risk === 'medium') return 'medium'
  return 'low'
})

const riskText = computed(() => {
  if (!props.message.verification) return ''
  const map = { high: '高风险', medium: '中风险' }
  return map[props.message.verification.hallucination_risk] || '低风险'
})

const formattedElapsed = computed(() => {
  const ms = props.message.elapsed
  if (ms == null) return ''
  return ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(1)}s`
})
</script>
