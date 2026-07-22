<template>
  <div class="stats-header-card">
    <div class="stat-item">
      <span class="stat-value">{{ stats.document_count }}</span>
      <span class="stat-label">文档块</span>
    </div>
    <div class="stat-divider"></div>
    <div class="stat-item">
      <span class="stat-value">{{ stats.source_count }}</span>
      <span class="stat-label">文档数</span>
    </div>
    <div class="stat-divider"></div>
    <div class="stat-item">
      <span class="stat-value">{{ formattedSize }}</span>
      <span class="stat-label">总大小</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  stats: {
    type: Object,
    default: () => ({ document_count: 0, source_count: 0, total_size: 0 })
  }
})

const formattedSize = computed(() => {
  const bytes = props.stats.total_size || 0
  if (bytes === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let i = 0
  let size = bytes
  while (size >= 1024 && i < units.length - 1) {
    size /= 1024
    i++
  }
  return `${size.toFixed(i === 0 ? 0 : 1)} ${units[i]}`
})
</script>

<style scoped>
.stats-header-card {
  display: flex;
  align-items: center;
  justify-content: space-around;
  padding: 1.5rem;
  background: hsl(var(--card));
  border-radius: var(--radius);
  border: 1px solid hsl(var(--border));
  box-shadow: var(--nb-shadow-sm);
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.stat-value {
  font-size: var(--nb-font-3xl);
  font-weight: 700;
  color: hsl(var(--foreground));
}

.stat-label {
  font-size: var(--nb-font-sm);
  color: hsl(var(--muted-foreground) / 0.7);
}

.stat-divider {
  width: 1px;
  height: 32px;
  background: hsl(var(--border));
}
</style>
