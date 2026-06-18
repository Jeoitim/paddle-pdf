<script setup lang="ts">
import { NProgress } from 'naive-ui'
import type { TaskProgress } from '@/types'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const props = defineProps<{ progress: TaskProgress }>()

const percentage = computed(() => {
  if (props.progress.total_pages <= 0) return 0
  return Math.round((props.progress.current_page / props.progress.total_pages) * 100)
})

const statusText = computed(() => {
  switch (props.progress.status) {
    case 'extracting': return t('task.extracting')
    case 'ocr_running': return t('task.ocrRunning', { current: props.progress.current_page, total: props.progress.total_pages })
    case 'saving': return t('task.saving')
    default: return props.progress.message || t('common.loading')
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
