<template>
  <div
    class="doc-list-item"
    @mouseenter="isHovered = true"
    @mouseleave="isHovered = false"
  >
    <!-- 左侧图标 -->
    <div class="doc-item-icon" :class="typeClass">
      <span class="type-label">{{ typeLabel }}</span>
    </div>

    <!-- 中间文本组 -->
    <div class="doc-item-text">
      <span class="doc-item-name" :title="source">{{ source }}</span>
      <span class="doc-item-meta">
        <span class="meta-type" :class="typeClass">{{ typeLabel }}</span>
        <span class="meta-separator">·</span>
        <span class="meta-chunks">{{ chunks }} 块</span>
        <span class="meta-separator">·</span>
        <span class="meta-size">{{ formattedSize }}</span>
      </span>
    </div>

    <!-- 右侧删除按钮 -->
    <button
      class="doc-item-delete"
      :class="{ 'doc-item-delete--visible': isHovered }"
      @click.stop="$emit('delete', source)"
      title="删除文档"
      aria-label="删除文档"
    >
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
        <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    </button>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  source: {
    type: String,
    required: true
  },
  fileType: {
    type: String,
    default: ''
  },
  chunks: {
    type: Number,
    default: 0
  },
  fileSize: {
    type: Number,
    default: 0
  }
})

defineEmits(['delete'])

const isHovered = ref(false)

const TYPE_MAP = {
  pdf:  'pdf',
  docx: 'docx',
  doc:  'docx',
  txt:  'txt',
  md:   'md',
  html: 'html',
  htm:  'html',
  png:  'img',
  jpg:  'img',
  jpeg: 'img',
  bmp:  'img',
  tiff: 'img'
}

const TYPE_LABELS = {
  pdf:  'PDF',
  docx: 'DOC',
  txt:  'TXT',
  md:   'MD',
  html: 'HTML',
  img:  'IMG'
}

const typeClass = computed(() => {
  const ext = props.fileType?.toLowerCase() || ''
  return TYPE_MAP[ext] || 'other'
})

const typeLabel = computed(() => {
  const ext = props.fileType?.toLowerCase() || ''
  const cls = TYPE_MAP[ext] || 'other'
  return TYPE_LABELS[cls] || '未知'
})

const formattedSize = computed(() => {
  const size = props.fileSize
  if (size === 0) return '0 B'
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / (1024 * 1024)).toFixed(1)} MB`
})
</script>

<style scoped>
.doc-list-item {
  display: flex;
  align-items: center;
  min-height: 72px;
  padding: 1rem 1.5rem;
  border-radius: var(--radius);
  transition: background 0.2s ease;
  cursor: default;
}

.doc-list-item:hover {
  background: hsl(var(--accent));
}

.doc-list-item:active {
  background: hsl(var(--accent) / 0.8);
  transition-duration: 0.08s;
}

/* 左侧图标 */
.doc-item-icon {
  width: 48px;
  height: 48px;
  border-radius: var(--radius);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: transform 0.2s ease;
}

.doc-item-icon.pdf  { background: hsl(var(--nb-danger-bg)); color: hsl(var(--nb-danger)); }
.doc-item-icon.docx { background: hsl(var(--nb-brand) / 0.1); color: hsl(var(--nb-brand)); }
.doc-item-icon.txt  { background: hsl(var(--muted)); color: hsl(var(--muted-foreground)); }
.doc-item-icon.md   { background: hsl(var(--muted)); color: hsl(var(--muted-foreground)); }
.doc-item-icon.html { background: hsl(var(--nb-warning-bg)); color: hsl(var(--nb-warning)); }
.doc-item-icon.img  { background: hsl(var(--nb-success-bg)); color: hsl(var(--nb-success)); }
.doc-item-icon.other { background: hsl(var(--muted)); color: hsl(var(--muted-foreground)); }

.doc-list-item:hover .doc-item-icon {
  transform: scale(1.05);
}

.type-label {
  font-size: var(--nb-font-xs);
  font-weight: 500;
  line-height: 1;
}

/* 中间文本组 */
.doc-item-text {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0 1.5rem;
}

.doc-item-name {
  font-size: var(--nb-font-lg);
  font-weight: 500;
  line-height: 22px;
  color: hsl(var(--foreground));
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.doc-item-meta {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-size: var(--nb-font-base);
  color: hsl(var(--muted-foreground) / 0.7);
}

.meta-type {
  padding: 0.25rem 0.75rem;
  border-radius: var(--radius);
  font-size: var(--nb-font-xs);
  font-weight: 500;
  line-height: 1.2;
}

.meta-type.pdf  { background: hsl(var(--nb-danger-bg)); color: hsl(var(--nb-danger)); }
.meta-type.docx { background: hsl(var(--nb-brand) / 0.1); color: hsl(var(--nb-brand)); }
.meta-type.txt  { background: hsl(var(--muted)); color: hsl(var(--muted-foreground)); }
.meta-type.md   { background: hsl(var(--muted)); color: hsl(var(--muted-foreground)); }
.meta-type.html { background: hsl(var(--nb-warning-bg)); color: hsl(var(--nb-warning)); }
.meta-type.img  { background: hsl(var(--nb-success-bg)); color: hsl(var(--nb-success)); }
.meta-type.other { background: hsl(var(--muted)); color: hsl(var(--muted-foreground)); }

.meta-separator {
  color: hsl(var(--muted-foreground) / 0.4);
}

/* 右侧删除按钮 */
.doc-item-delete {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  border-radius: var(--radius);
  color: hsl(var(--muted-foreground) / 0.7);
  cursor: pointer;
  opacity: 0;
  transition: all 0.2s ease;
}

.doc-item-delete--visible {
  opacity: 1;
}

.doc-item-delete:hover {
  background: hsl(var(--nb-danger-bg));
  color: hsl(var(--nb-danger));
}

.doc-item-delete:active {
  background: hsl(var(--nb-danger-bg));
  transition-duration: 0.08s;
}
</style>
