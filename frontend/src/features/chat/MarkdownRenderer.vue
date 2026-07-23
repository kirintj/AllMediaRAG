<script setup>
import { computed } from 'vue'
import { marked } from 'marked'

const props = defineProps({
  content: { type: String, default: '' },
})

const html = computed(() => {
  if (!props.content) return ''
  return marked.parse(props.content, { breaks: true, gfm: true })
})
</script>

<template>
  <div class="markdown-content text-[15px] leading-[var(--cjk-line-height,1.625)]" v-html="html" />
</template>

<style scoped>
.markdown-content :deep(pre) {
  background: hsl(var(--muted));
  color: hsl(var(--foreground));
  padding: 0.75rem 1rem;
  border-radius: var(--radius);
  margin: 0.625rem 0;
  overflow-x: auto;
  font-family: var(--font-mono);
  font-size: 13px;
  line-height: 1.6;
  border: 1px solid hsl(var(--border));
}

.markdown-content :deep(code) {
  background: hsl(var(--muted));
  padding: 1px 4px;
  border-radius: 4px;
  font-family: var(--font-mono);
  font-size: 13px;
}

.markdown-content :deep(pre code) {
  background: none;
  padding: 0;
  border-radius: 0;
  font-size: inherit;
}

.markdown-content :deep(strong) { font-weight: 600; }

.markdown-content :deep(h1),
.markdown-content :deep(h2),
.markdown-content :deep(h3),
.markdown-content :deep(h4) {
  margin: 0.75rem 0 0.375rem;
  font-weight: 600;
  line-height: 1.4;
}
.markdown-content :deep(h1) { font-size: 1.25rem; }
.markdown-content :deep(h2) { font-size: 1.125rem; }
.markdown-content :deep(h3) { font-size: 1rem; }

.markdown-content :deep(p) { margin: 0.375rem 0; }
.markdown-content :deep(p:first-child) { margin-top: 0; }
.markdown-content :deep(p:last-child) { margin-bottom: 0; }

.markdown-content :deep(ul),
.markdown-content :deep(ol) {
  margin: 0.375rem 0;
  padding-left: 1.25rem;
}
.markdown-content :deep(li) { margin: 0.1875rem 0; }

.markdown-content :deep(blockquote) {
  margin: 0.5rem 0;
  padding: 0.25rem 0.75rem;
  border-left: 3px solid hsl(var(--primary));
  color: hsl(var(--muted-foreground));
  background: hsl(var(--muted));
  border-radius: 0 var(--radius) var(--radius) 0;
}

.markdown-content :deep(table) {
  border-collapse: collapse;
  margin: 0.5rem 0;
  font-size: 13px;
  width: 100%;
}
.markdown-content :deep(th),
.markdown-content :deep(td) {
  border: 1px solid hsl(var(--border));
  padding: 0.25rem 0.5rem;
  text-align: left;
}
.markdown-content :deep(th) {
  background: hsl(var(--muted));
  font-weight: 600;
}

.markdown-content :deep(hr) {
  border: none;
  border-top: 1px solid hsl(var(--border));
  margin: 0.75rem 0;
}

.markdown-content :deep(a) {
  color: hsl(var(--primary));
  text-decoration: none;
}
.markdown-content :deep(a:hover) {
  text-decoration: underline;
}
</style>
