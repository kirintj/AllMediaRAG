<script setup>
import { DialogRoot, DialogPortal, DialogOverlay, DialogContent, DialogTitle, DialogDescription } from 'radix-vue'
import { useConfirmStore } from '@/stores/useConfirmStore'
import Button from '@/components/ui/button.vue'

const store = useConfirmStore()
</script>

<template>
  <DialogRoot :open="store.visible" @update:open="v => { if (!v) store.handleCancel() }">
    <DialogPortal>
      <DialogOverlay class="fixed inset-0 z-[100] bg-black/40 backdrop-blur-sm data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0" />
      <!-- 外层 fixed 容器确保居中定位 -->
      <div class="fixed inset-0 z-[100] flex items-center justify-center pointer-events-none">
        <DialogContent
          class="relative w-full max-w-sm gap-4 border bg-background p-6 shadow-lg duration-200 pointer-events-auto data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 sm:rounded-lg"
        >
          <DialogTitle class="text-lg font-semibold leading-none">
            {{ store.title }}
          </DialogTitle>
          <DialogDescription class="text-sm text-muted-foreground">
            {{ store.message }}
          </DialogDescription>
          <div class="flex justify-end gap-2 mt-4">
            <Button variant="outline" size="sm" @click="store.handleCancel">
              {{ store.cancelText }}
            </Button>
            <Button :variant="store.destructive ? 'destructive' : 'default'" size="sm" @click="store.handleConfirm">
              {{ store.confirmText }}
            </Button>
          </div>
        </DialogContent>
      </div>
    </DialogPortal>
  </DialogRoot>
</template>
