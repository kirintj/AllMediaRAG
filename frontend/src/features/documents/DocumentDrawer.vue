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
  background: rgba(0,0,0,0.45);
  z-index: 1000;
  display: flex;
  justify-content: flex-end;
}

/* ── 抽屉容器 ── */
.drawer-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: hsl(var(--background));
  box-shadow: var(--nb-shadow-lg);
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
  background: hsl(var(--background) / 0.8);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid hsl(var(--border));
  flex-shrink: 0;
}

.titlebar-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 2rem 2rem;
}

.titlebar-left {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.titlebar-title {
  font-size: var(--nb-font-xl);
  font-weight: 500;
  color: hsl(var(--foreground));
  line-height: 1.3;
}

.titlebar-subtitle {
  font-size: var(--nb-font-sm);
  color: hsl(var(--muted-foreground) / 0.7);
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
  color: hsl(var(--muted-foreground));
  cursor: pointer;
  transition: background 0.2s ease, color 0.2s ease;
  flex-shrink: 0;
}

.titlebar-close:hover {
  background: hsl(var(--accent));
  color: hsl(var(--foreground));
}

.titlebar-close:active {
  background: hsl(var(--accent) / 0.8);
  transition-duration: 0.08s;
}

/* ── 内容区 ── */
.drawer-content {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  padding: 1.5rem;
}

/* ── 底部操作栏 ── */
.drawer-footer {
  position: sticky;
  bottom: 0;
  z-index: 10;
  display: flex;
  gap: 0.75rem;
  padding: 1.25rem 2rem;
  background: hsl(var(--card));
  border-top: 1px solid hsl(var(--border));
  flex-shrink: 0;
}

.footer-btn {
  flex: 1;
  height: 40px;
  font-size: var(--nb-font-base);
  font-weight: 500;
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius);
  background: hsl(var(--card));
  color: hsl(var(--foreground));
  cursor: pointer;
  transition: all 0.2s ease;
}

.footer-btn:hover:not(:disabled) {
  background: hsl(var(--accent));
}

.footer-btn:active:not(:disabled) {
  background: hsl(var(--accent) / 0.8);
  transition-duration: 0.08s;
}

.footer-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

/* 主按钮：品牌色 */
.footer-btn.primary {
  background: hsl(var(--nb-brand));
  border-color: hsl(var(--nb-brand));
  color: hsl(var(--primary-foreground));
}

.footer-btn.primary:hover:not(:disabled) {
  background: hsl(var(--nb-brand-hover));
  border-color: hsl(var(--nb-brand-hover));
}

.footer-btn.primary:active:not(:disabled) {
  background: hsl(var(--nb-brand-pressed));
  border-color: hsl(var(--nb-brand-pressed));
}

/* 危险按钮：警告色 */
.footer-btn.danger {
  color: hsl(var(--nb-danger));
  border-color: hsl(var(--nb-danger));
}

.footer-btn.danger:hover:not(:disabled) {
  background: hsl(var(--nb-danger-bg));
}

.footer-btn.danger:active:not(:disabled) {
  background: hsl(var(--nb-danger-bg));
}

/* ── 滑入动画 ── */
.drawer-enter-active {
  transition: opacity 0.3s ease;
}

.drawer-enter-active .drawer-container {
  transition: transform 0.3s ease;
}

.drawer-leave-active {
  transition: opacity 0.3s ease;
}

.drawer-leave-active .drawer-container {
  transition: transform 0.3s ease;
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
