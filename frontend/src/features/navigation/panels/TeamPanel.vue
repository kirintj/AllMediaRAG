<template>
  <div class="flex flex-col h-full">
    <!-- Header -->
    <div class="flex items-center justify-between px-4 h-12 border-b border-border flex-shrink-0">
      <h3 class="text-sm font-semibold text-foreground">团队</h3>
      <button
        class="h-7 w-7 flex items-center justify-center rounded-md hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
        @click="$emit('open-team')"
        title="邀请成员"
      >
        <UserPlus class="h-4 w-4" />
      </button>
    </div>

    <!-- Team content -->
    <div class="flex-1 overflow-y-auto min-h-0 px-2 py-2">
      <!-- Placeholder: show team drawer trigger -->
      <div class="flex flex-col items-center justify-center py-10 px-4 text-center">
        <div class="w-10 h-10 rounded-xl bg-muted flex items-center justify-center mb-3">
          <Users class="h-5 w-5 text-muted-foreground" />
        </div>
        <p class="text-sm text-muted-foreground">团队管理</p>
        <p class="text-[11px] text-muted-foreground/70 mt-0.5">管理成员和权限</p>
        <button
          class="mt-4 px-4 py-1.5 text-xs font-medium rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
          @click="$emit('open-team')"
        >
          打开团队管理
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { Users, UserPlus } from 'lucide-vue-next'

defineEmits(['open-team'])
</script>
