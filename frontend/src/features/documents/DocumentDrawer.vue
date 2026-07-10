<template>
  <Teleport to="body">
    <Transition name="drawer">
      <div v-if="modelValue" class="drawer-overlay" @click.self="close">
        <div class="drawer-container" :class="drawerClass">
          <!-- Titlebar -->
          <header class="drawer-titlebar">
            <div class="titlebar-content">
              <div class="titlebar-left">
                <h2 class="titlebar-title">文档管理</h2>
                <span class="titlebar-subtitle">
                  {{ store.stats.source_count }} 个文档 · {{ store.stats.document_count }} 块向量
                </span>
              </div>
              <button class="titlebar-close" @click="close" title="关闭">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                  <path d="M18 6L6 18M6 6l12 12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                </svg>
              </button>
            </div>
          </header>

          <!-- 内容区 -->
          <div class="drawer-content cus-scroll">
            <StatsHeaderCard :stats="store.stats" />
            <UploadArea @uploaded="handleUploaded" />
            <DocumentList ref="docListRef" />
          </div>

          <!-- 底部操作栏 -->
          <footer class="drawer-footer">
            <button
              class="footer-btn primary"
              :disabled="loading"
              @click="handleLoadAll"
            >
              {{ loading ? '加载中...' : '加载本地文档' }}
            </button>
            <button
              class="footer-btn"
              :disabled="syncing"
              @click="handleSync"
            >
              {{ syncing ? '同步中...' : '增量同步' }}
            </button>
            <button
              class="footer-btn danger"
              :disabled="!store.hasDocuments"
              @click="handleClearAll"
            >
              清空
            </button>
          </footer>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useDocumentStore } from '../../stores/useDocumentStore.js'
import StatsHeaderCard from './StatsHeaderCard.vue'
import UploadArea from './UploadArea.vue'
import DocumentList from './DocumentList.vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false }
})

const emit = defineEmits(['update:modelValue'])

const store = useDocumentStore()
const docListRef = ref(null)
const loading = ref(false)
const syncing = ref(false)

// ── 响应式宽度断点 ──
const windowWidth = ref(window.innerWidth)

const drawerClass = computed(() => {
  if (windowWidth.value < 768) return 'drawer-full'
  if (windowWidth.value < 1024) return 'drawer-medium'
  return 'drawer-wide'
})

function handleResize() {
  windowWidth.value = window.innerWidth
}

// ── 键盘 Esc 关闭 ──
function handleEsc(e) {
  if (e.key === 'Escape' && props.modelValue) {
    close()
  }
}

// ── 生命周期 ──
watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      // 打开时加载统计和文档详情
      store.fetchStats()
      store.fetchDocumentDetails()
      document.addEventListener('keydown', handleEsc)
    } else {
      document.removeEventListener('keydown', handleEsc)
    }
  },
  { immediate: true }
)

window.addEventListener('resize', handleResize)

onUnmounted(() => {
  document.removeEventListener('keydown', handleEsc)
  window.removeEventListener('resize', handleResize)
})

// ── 关闭抽屉 ──
function close() {
  emit('update:modelValue', false)
}

// ── 上传完成后刷新数据 ──
function handleUploaded() {
  store.fetchStats()
  docListRef.value?.loadDetails()
}

// ── 加载本地文档 ──
async function handleLoadAll() {
  loading.value = true
  try {
    await store.loadAllDocuments()
    ElMessage.success('本地文档加载完成')
    docListRef.value?.loadDetails()
  } catch (e) {
    ElMessage.error(e.message || '加载本地文档失败')
  } finally {
    loading.value = false
  }
}

// ── 增量同步 ──
async function handleSync() {
  syncing.value = true
  try {
    await store.syncDocuments()
    ElMessage.success('增量同步完成')
    docListRef.value?.loadDetails()
  } catch (e) {
    ElMessage.error(e.message || '增量同步失败')
  } finally {
    syncing.value = false
  }
}

// ── 清空所有文档 ──
async function handleClearAll() {
  try {
    await ElMessageBox.confirm(
      '清空后所有文档的向量数据将被永久删除，无法恢复。确定继续？',
      '确认清空',
      {
        confirmButtonText: '确认清空',
        cancelButtonText: '取消',
        type: 'warning',
        customClass: 'delete-confirm-box'
      }
    )

    await store.removeAllDocuments()
    ElMessage.success('已清空所有文档')
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(e.message || '清空失败')
    }
  }
}
</script>

<style scoped>
/* ── 遮罩层 ── */
.drawer-overlay {
  position: fixed;
  inset: 0;
  background: var(--harmony-overlay);
  z-index: 1000;
  display: flex;
  justify-content: flex-end;
}

/* ── 抽屉容器 ── */
.drawer-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--harmony-background-secondary);
  box-shadow: var(--harmony-shadow-xl);
  overflow: hidden;
}

/* 响应式宽度 */
.drawer-wide  { width: 480px; }
.drawer-medium { width: 400px; }
.drawer-full  { width: 100vw; }

/* ── Titlebar ── */
.drawer-titlebar {
  position: sticky;
  top: 0;
  z-index: 10;
  background: var(--harmony-titlebar-bg);
  backdrop-filter: var(--harmony-titlebar-blur);
  -webkit-backdrop-filter: var(--harmony-titlebar-blur);
  border-bottom: var(--harmony-titlebar-border);
  flex-shrink: 0;
}

.titlebar-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--harmony-padding-level8) var(--harmony-padding-level8);
}

.titlebar-left {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.titlebar-title {
  font-size: var(--harmony-font-size-subtitle-l);
  font-weight: var(--harmony-font-weight-subtitle-l);
  color: var(--harmony-font-primary);
  line-height: 1.3;
}

.titlebar-subtitle {
  font-size: var(--harmony-font-size-body-s);
  color: var(--harmony-font-tertiary);
}

.titlebar-close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: none;
  background: transparent;
  border-radius: 50%;
  color: var(--harmony-font-secondary);
  cursor: pointer;
  transition: background 0.2s var(--harmony-ease-out), color 0.2s var(--harmony-ease-out);
  flex-shrink: 0;
}

.titlebar-close:hover {
  background: var(--harmony-interactive-hover);
  color: var(--harmony-font-primary);
}

.titlebar-close:active {
  background: var(--harmony-interactive-pressed);
  transition-duration: 0.08s;
}

/* ── 内容区 ── */
.drawer-content {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: var(--harmony-padding-level6);
  padding: var(--harmony-padding-level6);
}

/* ── 底部操作栏 ── */
.drawer-footer {
  position: sticky;
  bottom: 0;
  z-index: 10;
  display: flex;
  gap: var(--harmony-padding-level3);
  padding: var(--harmony-padding-level5) var(--harmony-padding-level8);
  background: var(--harmony-comp-background-primary);
  border-top: 1px solid var(--harmony-comp-divider);
  flex-shrink: 0;
}

.footer-btn {
  flex: 1;
  height: var(--harmony-control-height-40);
  font-size: var(--harmony-font-size-body-m);
  font-weight: var(--harmony-font-weight-subtitle-s);
  border: 1px solid var(--harmony-comp-divider);
  border-radius: var(--harmony-corner-radius-level10);
  background: var(--harmony-comp-background-primary);
  color: var(--harmony-font-primary);
  cursor: pointer;
  transition: all 0.2s var(--harmony-ease-out);
}

.footer-btn:hover:not(:disabled) {
  background: var(--harmony-interactive-hover);
}

.footer-btn:active:not(:disabled) {
  background: var(--harmony-interactive-pressed);
  transition-duration: 0.08s;
}

.footer-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

/* 主按钮：品牌色 */
.footer-btn.primary {
  background: var(--harmony-brand);
  border-color: var(--harmony-brand);
  color: var(--harmony-font-on-primary);
}

.footer-btn.primary:hover:not(:disabled) {
  background: var(--harmony-brand-hover);
  border-color: var(--harmony-brand-hover);
}

.footer-btn.primary:active:not(:disabled) {
  background: var(--harmony-brand-pressed);
  border-color: var(--harmony-brand-pressed);
}

/* 危险按钮：警告色 */
.footer-btn.danger {
  color: var(--harmony-warning);
  border-color: var(--harmony-warning);
}

.footer-btn.danger:hover:not(:disabled) {
  background: var(--harmony-danger-hover-bg);
}

.footer-btn.danger:active:not(:disabled) {
  background: var(--harmony-danger-hover-bg);
}

/* ── 滑入动画 ── */
.drawer-enter-active {
  transition: opacity 0.3s var(--harmony-ease-out);
}

.drawer-enter-active .drawer-container {
  transition: transform 0.3s var(--harmony-ease-out);
}

.drawer-leave-active {
  transition: opacity 0.3s var(--harmony-ease-out);
}

.drawer-leave-active .drawer-container {
  transition: transform 0.3s var(--harmony-ease-out);
}

.drawer-enter-from {
  opacity: 0;
}

.drawer-enter-from .drawer-container {
  transform: translateX(100%);
}

.drawer-leave-to {
  opacity: 0;
}

.drawer-leave-to .drawer-container {
  transform: translateX(100%);
}
</style>
