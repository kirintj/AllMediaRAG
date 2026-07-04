<template>
  <Teleport to="body">
    <Transition name="drawer">
      <div v-if="modelValue" class="drawer-overlay" @click.self="close">
        <div class="drawer-container" :class="drawerClass">
          <!-- Titlebar -->
          <header class="drawer-titlebar">
            <div class="titlebar-content">
              <div class="titlebar-left">
                <h2 class="titlebar-title">API 配置</h2>
                <span class="titlebar-subtitle">管理系统 API 密钥与 RAG 参数</span>
              </div>
              <button class="titlebar-close" @click="close" title="关闭">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                  <path d="M18 6L6 18M6 6l12 12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                </svg>
              </button>
            </div>
          </header>

          <!-- 内容区：Tab -->
          <div class="drawer-content cus-scroll">
            <div v-if="store.loading" class="settings-loading">加载中...</div>
            <div v-else class="settings-tabs">
              <div class="tab-header">
                <button
                  v-for="tab in tabs"
                  :key="tab.key"
                  class="tab-btn"
                  :class="{ active: activeTab === tab.key }"
                  @click="activeTab = tab.key"
                >
                  {{ tab.label }}
                </button>
              </div>

              <div class="tab-body">
                <div v-for="item in currentTabFields" :key="item.key" class="form-item">
                  <label class="form-label">{{ item.description || item.key }}</label>

                  <!-- select 类型 -->
                  <select
                    v-if="item.type === 'select'"
                    class="form-input"
                    :value="formValues[item.key] ?? item.value"
                    @change="onSelectChange(item.key, $event.target.value)"
                  >
                    <option v-for="opt in item.options" :key="opt" :value="opt">{{ opt }}</option>
                  </select>

                  <!-- password 类型 -->
                  <div v-else-if="item.type === 'password'" class="password-wrapper">
                    <input
                      :type="showKeys[item.key] ? 'text' : 'password'"
                      class="form-input"
                      :value="formValues[item.key] ?? item.value"
                      :placeholder="item.value ? '已设置（留空保持不变）' : '请输入'"
                      @input="formValues[item.key] = $event.target.value"
                    />
                    <button
                      class="eye-btn"
                      type="button"
                      @click="showKeys[item.key] = !showKeys[item.key]"
                    >
                      {{ showKeys[item.key] ? '🙈' : '👁' }}
                    </button>
                  </div>

                  <!-- number 类型 -->
                  <input
                    v-else-if="item.type === 'number'"
                    type="number"
                    class="form-input"
                    :value="formValues[item.key] ?? item.value"
                    @input="formValues[item.key] = $event.target.value"
                  />

                  <!-- text 类型（默认） -->
                  <input
                    v-else
                    type="text"
                    class="form-input"
                    :value="formValues[item.key] ?? item.value"
                    @input="formValues[item.key] = $event.target.value"
                  />
                </div>
              </div>
            </div>
          </div>

          <!-- 底部操作栏 -->
          <footer class="drawer-footer">
            <button class="footer-btn primary" :disabled="store.saving" @click="handleSave">
              {{ store.saving ? '保存中...' : '保存' }}
            </button>
            <button class="footer-btn" @click="close">取消</button>
          </footer>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, reactive, computed, watch, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useSettingsStore } from '../../stores/useSettingsStore.js'

const props = defineProps({
  modelValue: { type: Boolean, default: false }
})
const emit = defineEmits(['update:modelValue'])

const store = useSettingsStore()
const activeTab = ref('llm')
const formValues = reactive({})
const showKeys = reactive({})

const tabs = [
  { key: 'llm',        label: 'LLM API' },
  { key: 'embedding',  label: 'Embedding' },
  { key: 'reranking',  label: 'Reranking' },
  { key: 'rag',        label: 'RAG 参数' },
]

const currentTabFields = computed(() => {
  const fields = store.groups[activeTab.value] || []
  return fields.filter(item => {
    if (!item.show_if) return true
    for (const [condKey, condVal] of Object.entries(item.show_if)) {
      const currentVal = formValues[condKey] ?? fields.find(f => f.key === condKey)?.value
      if (currentVal !== condVal) return false
    }
    return true
  })
})

const windowWidth = ref(window.innerWidth)
const drawerClass = computed(() => {
  if (windowWidth.value < 768) return 'drawer-full'
  if (windowWidth.value < 1024) return 'drawer-medium'
  return 'drawer-wide'
})

function handleResize() { windowWidth.value = window.innerWidth }
function handleEsc(e) { if (e.key === 'Escape' && props.modelValue) close() }
function close() { emit('update:modelValue', false) }
function onSelectChange(key, value) { formValues[key] = value }

watch(
  () => props.modelValue,
  async (open) => {
    if (open) {
      await store.fetchSettings()
      Object.keys(formValues).forEach(k => delete formValues[k])
      for (const [, fields] of Object.entries(store.groups)) {
        for (const f of fields) {
          if (f.type !== 'password') {
            formValues[f.key] = f.value
          }
        }
      }
      document.addEventListener('keydown', handleEsc)
    } else {
      document.removeEventListener('keydown', handleEsc)
      Object.keys(formValues).forEach(k => delete formValues[k])
    }
  },
  { immediate: true }
)

window.addEventListener('resize', handleResize)
onUnmounted(() => {
  document.removeEventListener('keydown', handleEsc)
  window.removeEventListener('resize', handleResize)
})

async function handleSave() {
  try {
    const group = activeTab.value
    const payload = {}
    const fields = store.groups[group] || []
    for (const f of fields) {
      if (formValues[f.key] !== undefined && formValues[f.key] !== f.value) {
        payload[f.key] = String(formValues[f.key])
      }
    }
    if (Object.keys(payload).length === 0) {
      ElMessage.info('没有变更')
      return
    }
    await store.saveSettings(group, payload)
    ElMessage.success('配置已保存')
    close()
  } catch (e) {
    ElMessage.error(e.message || '保存失败')
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

.drawer-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--harmony-background-secondary);
  box-shadow: var(--harmony-shadow-xl);
  overflow: hidden;
}

.drawer-wide  { width: 480px; }
.drawer-medium { width: 400px; }
.drawer-full  { width: 100vw; }

.drawer-titlebar {
  position: sticky;
  top: 0;
  z-index: 10;
  background: var(--harmony-comp-background-primary);
  border-bottom: 1px solid var(--harmony-comp-divider);
  flex-shrink: 0;
}

.titlebar-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--harmony-padding-level8);
}

.titlebar-left { display: flex; flex-direction: column; gap: 2px; }

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

.titlebar-close:hover { background: var(--harmony-interactive-hover); color: var(--harmony-font-primary); }
.titlebar-close:active { background: var(--harmony-interactive-pressed); transition-duration: 0.08s; }

.drawer-content {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  padding: var(--harmony-padding-level6);
}

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

.footer-btn:hover:not(:disabled) { background: var(--harmony-interactive-hover); }
.footer-btn:active:not(:disabled) { background: var(--harmony-interactive-pressed); transition-duration: 0.08s; }
.footer-btn:disabled { opacity: 0.45; cursor: not-allowed; }

.footer-btn.primary {
  background: var(--harmony-brand);
  border-color: var(--harmony-brand);
  color: var(--harmony-font-on-primary);
}

.footer-btn.primary:hover:not(:disabled) { background: var(--harmony-brand-hover); border-color: var(--harmony-brand-hover); }
.footer-btn.primary:active:not(:disabled) { background: var(--harmony-brand-pressed); border-color: var(--harmony-brand-pressed); }

/* ── Tab 样式 ── */
.settings-tabs { display: flex; flex-direction: column; gap: var(--harmony-padding-level6); }

.tab-header {
  display: flex;
  gap: 4px;
  background: var(--harmony-comp-background-tertiary);
  border-radius: var(--harmony-corner-radius-level8);
  padding: 4px;
}

.tab-btn {
  flex: 1;
  padding: 8px 12px;
  font-size: var(--harmony-font-size-body-s);
  font-weight: var(--harmony-font-weight-body-m);
  border: none;
  border-radius: var(--harmony-corner-radius-level6);
  background: transparent;
  color: var(--harmony-font-secondary);
  cursor: pointer;
  transition: all 0.2s var(--harmony-ease-out);
}

.tab-btn.active {
  background: var(--harmony-comp-background-primary);
  color: var(--harmony-font-primary);
  box-shadow: var(--harmony-shadow-sm);
}

.tab-btn:hover:not(.active) { color: var(--harmony-font-primary); }

.tab-body {
  display: flex;
  flex-direction: column;
  gap: var(--harmony-padding-level5);
}

.form-item { display: flex; flex-direction: column; gap: 6px; }

.form-label {
  font-size: var(--harmony-font-size-body-s);
  font-weight: var(--harmony-font-weight-subtitle-s);
  color: var(--harmony-font-secondary);
}

.form-input {
  width: 100%;
  height: var(--harmony-control-height-40);
  padding: 0 var(--harmony-padding-level4);
  font-size: var(--harmony-font-size-body-m);
  border: 1px solid var(--harmony-comp-divider);
  border-radius: var(--harmony-corner-radius-level8);
  background: var(--harmony-comp-background-primary);
  color: var(--harmony-font-primary);
  outline: none;
  transition: border-color 0.2s var(--harmony-ease-out);
  box-sizing: border-box;
}

.form-input:focus { border-color: var(--harmony-brand); }
select.form-input { cursor: pointer; }

.password-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.password-wrapper .form-input { padding-right: 40px; }

.eye-btn {
  position: absolute;
  right: 8px;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 16px;
}

.settings-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: var(--harmony-font-tertiary);
  font-size: var(--harmony-font-size-body-m);
}

/* ── 滑入动画 ── */
.drawer-enter-active { transition: opacity 0.3s ease-out; }
.drawer-enter-active .drawer-container { transition: transform 0.3s ease-out; }
.drawer-leave-active { transition: opacity 0.3s ease-out; }
.drawer-leave-active .drawer-container { transition: transform 0.3s ease-out; }
.drawer-enter-from { opacity: 0; }
.drawer-enter-from .drawer-container { transform: translateX(100%); }
.drawer-leave-to { opacity: 0; }
.drawer-leave-to .drawer-container { transform: translateX(100%); }
</style>
