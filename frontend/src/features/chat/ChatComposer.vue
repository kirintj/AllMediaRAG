<template>
  <div
    class="mx-auto w-full"
    :class="hero ? 'max-w-[58rem]' : 'max-w-[49.5rem]'"
  >
    <div
      class="relative bg-background border border-border transition-shadow"
      :class="hero
        ? 'rounded-[28px] shadow-[0_20px_55px_rgba(15,23,42,0.08)] px-5 pt-7 pb-3'
        : 'rounded-[22px] shadow-[0_4px_16px_rgba(15,23,42,0.06)] px-4 pt-4 pb-2'
      "
      :style="{ minHeight: hero ? '78px' : '50px' }"
    >
      <!-- Textarea -->
      <textarea
        ref="inputRef"
        v-model="inputMessage"
        class="w-full bg-transparent border-none outline-none resize-none text-base text-foreground placeholder:text-muted-foreground leading-relaxed"
        :style="{ minHeight: hero ? '48px' : '32px' }"
        :placeholder="chatStore.loading ? '正在回答中...' : '输入你的问题...'"
        :disabled="chatStore.loading"
        @keydown.enter.exact.prevent="handleSend"
        @input="autoResize"
      />

      <!-- Toolbar -->
      <div class="flex items-center justify-between mt-1 -mb-1">
        <div class="flex items-center gap-1">
          <!-- Mode toggle -->
          <div class="flex items-center h-9 sm:h-7 rounded-full bg-muted p-0.5">
            <button
              class="h-8 sm:h-6 px-3 sm:px-2.5 rounded-full text-xs sm:text-[11px] font-medium transition-colors"
              :class="chatStore.mode === 'rag'
                ? 'bg-background text-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground'"
              @click="chatStore.mode = 'rag'"
            >
              RAG
            </button>
            <button
              class="h-8 sm:h-6 px-3 sm:px-2.5 rounded-full text-xs sm:text-[11px] font-medium transition-colors"
              :class="chatStore.mode === 'direct'
                ? 'bg-background text-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground'"
              @click="chatStore.mode = 'direct'"
            >
              直接对话
            </button>
          </div>
        </div>

        <!-- Send / Stop button -->
        <button
          v-if="chatStore.loading"
          class="h-10 w-10 sm:h-9 sm:w-9 flex items-center justify-center rounded-full bg-destructive text-destructive-foreground hover:bg-destructive/90 transition-colors"
          @click="handleStop"
          title="停止"
        >
          <Square class="h-4 w-4" />
        </button>
        <button
          v-else
          class="h-10 w-10 sm:h-9 sm:w-9 flex items-center justify-center rounded-full transition-all"
          :class="inputMessage.trim()
            ? 'bg-foreground text-background hover:scale-105'
            : 'bg-muted text-muted-foreground cursor-not-allowed opacity-40'"
          :disabled="!inputMessage.trim()"
          @click="handleSend"
          title="发送"
        >
          <ArrowUp class="h-4 w-4" />
        </button>
      </div>
    </div>

    <!-- Mode hint -->
    <p v-if="hero" class="text-center text-[11px] text-muted-foreground mt-2">
      {{ chatStore.mode === 'rag' ? 'RAG 检索增强模式' : '直接对话模式' }}
    </p>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'
import { ArrowUp, Square } from 'lucide-vue-next'
import { useChatStore } from '../../stores/useChatStore.js'

defineProps({
  hero: { type: Boolean, default: false },
})

const emit = defineEmits(['send'])
const chatStore = useChatStore()
const inputMessage = ref('')
const inputRef = ref(null)

function handleSend() {
  if (!inputMessage.value.trim() || chatStore.loading) return
  emit('send', inputMessage.value)
  inputMessage.value = ''
  nextTick(() => autoResize())
}

function handleStop() {
  // ponytail: no AbortController wired to SSE yet, just let it finish
}

function autoResize() {
  const el = inputRef.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = el.scrollHeight + 'px'
}
</script>
