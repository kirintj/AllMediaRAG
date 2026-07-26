<template>
  <div
    v-show="expanded"
    class="relative flex-shrink-0 h-full border-r border-border bg-card overflow-hidden transition-[width] duration-300 ease-out"
    :style="{ width: expanded ? width + 'px' : '0px' }"
  >
    <!-- Resize handle -->
    <div
      class="absolute right-0 top-0 bottom-0 w-1 cursor-col-resize z-10 group/handle"
      @mousedown="startResize"
    >
      <div
        class="absolute right-0 top-0 bottom-0 w-[2px] transition-colors group-hover/handle:bg-primary/50"
        :class="resizing ? 'bg-primary/50' : 'bg-transparent'"
      />
    </div>

    <!-- Panel content -->
    <div class="h-full overflow-hidden">
      <ChatPanel
        v-if="navigationStore.activeNav === 'chat'"
        @open-models="$emit('open-models')"
      />
      <KbPanel
        v-else-if="navigationStore.activeNav === 'kb'"
        @open-kb="$emit('open-kb')"
      />
      <TeamPanel
        v-else-if="navigationStore.activeNav === 'team'"
        @open-team="$emit('open-team')"
      />
      <SettingsPanel
        v-else-if="navigationStore.activeNav === 'settings'"
        @open-docs="$emit('open-docs')"
        @open-kb="$emit('open-kb')"
        @open-models="$emit('open-models')"
        @open-tag-kb="$emit('open-tag-kb')"
        @open-settings="$emit('open-settings')"
        @open-graph="$emit('open-graph')"
        @open-team="$emit('open-team')"
        @open-eval="$emit('open-eval')"
        @logout="$emit('logout')"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, onUnmounted } from 'vue'
import { useNavigationStore } from '../../stores/useNavigationStore.js'
import ChatPanel from './panels/ChatPanel.vue'
import KbPanel from './panels/KbPanel.vue'
import TeamPanel from './panels/TeamPanel.vue'
import SettingsPanel from './panels/SettingsPanel.vue'

const props = defineProps({
  width: { type: Number, default: 280 },
  expanded: { type: Boolean, default: true },
})

const emit = defineEmits([
  'update:width',
  'open-docs', 'open-kb', 'open-models', 'open-tag-kb',
  'open-settings', 'open-graph', 'open-team', 'open-eval', 'logout',
])

const navigationStore = useNavigationStore()
const resizing = ref(false)

function startResize(e) {
  e.preventDefault()
  resizing.value = true
  const startX = e.clientX
  const startWidth = props.width

  function onMouseMove(e) {
    const delta = e.clientX - startX
    emit('update:width', Math.min(navigationStore.L2_MAX, Math.max(navigationStore.L2_MIN, startWidth + delta)))
  }

  function onMouseUp() {
    resizing.value = false
    document.removeEventListener('mousemove', onMouseMove)
    document.removeEventListener('mouseup', onMouseUp)
    document.body.style.cursor = ''
    document.body.style.userSelect = ''
  }

  document.addEventListener('mousemove', onMouseMove)
  document.addEventListener('mouseup', onMouseUp)
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'
}

onUnmounted(() => {
  // Clean up any lingering listeners
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
})
</script>
