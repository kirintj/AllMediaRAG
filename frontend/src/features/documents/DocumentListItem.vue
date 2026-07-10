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
  padding: var(--harmony-padding-level4) var(--harmony-padding-level6);
  border-radius: var(--harmony-corner-radius-level10);
  transition: background 0.2s var(--harmony-ease-out);
  cursor: default;
}

.doc-list-item:hover {
  background: var(--harmony-interactive-hover);
}

.doc-list-item:active {
  background: var(--harmony-interactive-pressed);
  transition-duration: 0.08s;
}

/* 左侧图标 */
.doc-item-icon {
  width: 48px;
  height: 48px;
  border-radius: var(--harmony-corner-radius-level6);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: transform 0.2s var(--harmony-ease-out);
}

.doc-item-icon.pdf  { background: var(--harmony-warning-light); color: var(--harmony-warning); }
.doc-item-icon.docx { background: var(--harmony-brand-light); color: var(--harmony-brand); }
.doc-item-icon.txt  { background: var(--harmony-neutral-tint); color: var(--harmony-font-secondary); }
.doc-item-icon.md   { background: var(--harmony-neutral-tint); color: var(--harmony-font-secondary); }
.doc-item-icon.html { background: var(--harmony-alert-light); color: var(--harmony-alert); }
.doc-item-icon.img  { background: var(--harmony-confirm-light); color: var(--harmony-confirm); }
.doc-item-icon.other { background: var(--harmony-comp-background-secondary); color: var(--harmony-font-secondary); }

.doc-list-item:hover .doc-item-icon {
  transform: scale(1.05);
}

.type-label {
  font-size: var(--harmony-font-size-caption-l);
  font-weight: var(--harmony-font-weight-caption-l);
  line-height: 1;
}

/* 中间文本组 */
.doc-item-text {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: var(--harmony-padding-level2);
  padding: 0 var(--harmony-padding-level6);
}

.doc-item-name {
  font-size: var(--harmony-font-size-body-l);
  font-weight: var(--harmony-font-weight-subtitle-m);
  line-height: 22px;
  color: var(--harmony-font-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.doc-item-meta {
  display: flex;
  align-items: center;
  gap: var(--harmony-padding-level3);
  font-size: var(--harmony-font-size-body-m);
  color: var(--harmony-font-tertiary);
}

.meta-type {
  padding: var(--harmony-padding-level1) var(--harmony-padding-level3);
  border-radius: var(--harmony-corner-radius-level4);
  font-size: var(--harmony-font-size-caption-l);
  font-weight: var(--harmony-font-weight-caption-l);
  line-height: 1.2;
}

.meta-type.pdf  { background: var(--harmony-warning-light); color: var(--harmony-warning); }
.meta-type.docx { background: var(--harmony-brand-light); color: var(--harmony-brand); }
.meta-type.txt  { background: var(--harmony-neutral-tint); color: var(--harmony-font-secondary); }
.meta-type.md   { background: var(--harmony-neutral-tint); color: var(--harmony-font-secondary); }
.meta-type.html { background: var(--harmony-alert-light); color: var(--harmony-alert); }
.meta-type.img  { background: var(--harmony-confirm-light); color: var(--harmony-confirm); }
.meta-type.other { background: var(--harmony-comp-background-secondary); color: var(--harmony-font-secondary); }

.meta-separator {
  color: var(--harmony-font-fourth);
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
  border-radius: var(--harmony-corner-radius-level8);
  color: var(--harmony-font-tertiary);
  cursor: pointer;
  opacity: 0;
  transition: all 0.2s var(--harmony-ease-out);
}

.doc-item-delete--visible {
  opacity: 1;
}

.doc-item-delete:hover {
  background: var(--harmony-danger-hover-bg);
  color: var(--harmony-warning);
}

.doc-item-delete:active {
  background: var(--harmony-danger-hover-bg);
  transition-duration: 0.08s;
}
</style>
