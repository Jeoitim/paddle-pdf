<script setup lang="ts">
import { NProgress } from 'naive-ui'
import type { TaskProgress } from '@/types'
import { computed } from 'vue'

const props = defineProps<{ progress: TaskProgress }>()

const percentage = computed(() => {
  if (props.progress.total_pages <= 0) return 0
  return Math.round((props.progress.current_page / props.progress.total_pages) * 100)
})

const statusText = computed(() => {
  switch (props.progress.status) {
    case 'extracting': return 'Extracting pages...'
    case 'ocr_running': return `OCR: page ${props.progress.current_page}/${props.progress.total_pages}`
    case 'saving': return 'Saving output...'
    default: return props.progress.message || 'Processing...'
  }
})
</script>

<template>
  <div class="space-y-1">
    <div class="flex justify-between text-sm">
      <span class="opacity-70">{{ statusText }}</span>
      <span class="opacity-60">{{ percentage }}%</span>
    </div>
    <NProgress
      type="line"
      :percentage="percentage"
      :show-indicator="false"
      :height="8"
      :border-radius="4"
    />
  </div>
</template>
