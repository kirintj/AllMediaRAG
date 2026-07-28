<template>
  <div class="flex flex-col h-full overflow-hidden">
    <!-- Header bar -->
    <ChatHeader @open-docs="$emit('open-docs')" @open-eval="$emit('open-eval')" />

    <!-- Scrollable message area -->
    <div class="flex-1 overflow-y-auto overflow-x-hidden min-h-0 relative" ref="viewportRef">
      <div class="mx-auto max-w-[64rem] px-4 sm:px-6">
        <!-- Empty state: centered hero -->
        <div v-if="chatStore.messages.length === 0" class="flex flex-col items-center justify-center min-h-full py-16">
          <div class="w-full max-w-[58rem] mx-auto text-center">
            <h2 class="text-2xl font-semibold text-foreground mb-2">开始你的智能问答之旅</h2>
            <p class="text-muted-foreground mb-6">基于 RAG 检索增强，精准回答知识库问题</p>
            <div class="flex flex-wrap gap-2 justify-center mb-8">
              <button
                v-for="q in suggestions"
                :key="q"
                class="px-4 h-9 rounded-full border border-border bg-background text-sm text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
                @click="quickAsk(q)"
              >
                {{ q }}
              </button>
            </div>
            <ChatComposer hero @send="handleSend" />
          </div>
        </div>

        <!-- Messages -->
        <div v-else class="py-6 max-w-[49.5rem] mx-auto">
          <MessageBubble
            v-for="(msg, index) in chatStore.messages"
            :key="index"
            :message="msg"
            :index="index"
          />
          <!-- bottom spacer so last message isn't hidden behind composer -->
          <div class="h-4" />
        </div>
      </div>

      <!-- Scroll to bottom FAB: relative inside scroll container -->
      <button
        v-if="showScrollButton"
        class="sticky bottom-4 left-1/2 -translate-x-1/2 z-20 h-8 w-8 rounded-full bg-background border border-border shadow-md flex items-center justify-center hover:bg-accent transition-colors"
        @click="scrollToBottom"
      >
        <ChevronDown class="h-4 w-4" />
      </button>
    </div>

    <!-- Composer: pinned to bottom, safe-area padding for iPhone (desktop only, mobile handled by bottom nav) -->
    <div v-if="chatStore.messages.length > 0" class="flex-shrink-0 bg-background px-4 sm:px-6 pt-3 pb-3 lg:pb-[calc(0.75rem+env(safe-area-inset-bottom,0px))]">
      <div class="mx-auto max-w-[49.5rem]">
        <ChatComposer @send="handleSend" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, watch, onMounted, onUnmounted } from 'vue'
import { ChevronDown } from 'lucide-vue-next'
import { useChatStore } from '../../stores/useChatStore.js'
import ChatHeader from './ChatHeader.vue'
import MessageBubble from './MessageBubble.vue'
import ChatComposer from './ChatComposer.vue'

defineEmits(['open-docs', 'open-eval'])

const chatStore = useChatStore()
const viewportRef = ref(null)
const showScrollButton = ref(false)

const suggestions = [
  '什么是 RAG？',
  '如何使用向量数据库？',
  '如何优化检索效果？',
]

async function handleSend(content) {
  if (!content.trim() || chatStore.loading) return
  await chatStore.sendMessage(content)
  await nextTick()
  scrollToBottom()
}

function quickAsk(q) {
  handleSend(q)
}

function scrollToBottom() {
  if (viewportRef.value) {
    viewportRef.value.scrollTop = viewportRef.value.scrollHeight
  }
}

function checkScroll() {
  if (!viewportRef.value) return
  const { scrollTop, scrollHeight, clientHeight } = viewportRef.value
  showScrollButton.value = scrollHeight - scrollTop - clientHeight > 200
}

// Auto-scroll on new messages
watch(
  () => chatStore.messages.length,
  () => nextTick(scrollToBottom)
)

watch(
  () => {
    const msgs = chatStore.messages
    return msgs.length > 0 ? msgs[msgs.length - 1].content : ''
  },
  () => nextTick(scrollToBottom)
)

onMounted(() => {
  viewportRef.value?.addEventListener('scroll', checkScroll, { passive: true })
})

onUnmounted(() => {
  viewportRef.value?.removeEventListener('scroll', checkScroll)
})
</script>
