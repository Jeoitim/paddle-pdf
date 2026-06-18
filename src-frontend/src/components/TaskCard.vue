<script setup lang="ts">
import { NIcon, NButton, NTag } from 'naive-ui'
import { CloseCircleOutline, CheckmarkCircleOutline, AlertCircleOutline, TimeOutline } from '@vicons/ionicons5'
import TaskProgress from './TaskProgress.vue'
import type { Task } from '@/types'
import { computed } from 'vue'

const props = defineProps<{ task: Task }>()
const emit = defineEmits<{ cancel: []; click: [] }>()

const statusConfig = computed(() => {
  switch (props.task.status) {
    case 'completed':
      return { color: 'success', icon: CheckmarkCircleOutline, label: 'Done' }
    case 'failed':
      return { color: 'error', icon: AlertCircleOutline, label: 'Failed' }
    case 'cancelled':
      return { color: 'warning', icon: CloseCircleOutline, label: 'Cancelled' }
    default:
      return { color: 'info', icon: TimeOutline, label: 'Processing' }
  }
})

const elapsedText = computed(() => {
  if (props.task.result) return `${props.task.result.elapsed_seconds.toFixed(1)}s`
  if (props.task.progress) return `${props.task.progress.elapsed.toFixed(1)}s`
  return ''
})
</script>

<template>
  <div
    class="card cursor-pointer hover:shadow-md transition-shadow"
    @click="$emit('click')"
  >
    <div class="flex items-center justify-between mb-2">
      <div class="flex items-center gap-2 min-w-0">
        <NIcon :component="statusConfig.icon" :size="20" />
        <span class="font-medium truncate">{{ task.fileName }}</span>
      </div>
      <div class="flex items-center gap-2">
        <NTag :type="statusConfig.color as any" size="small">{{ statusConfig.label }}</NTag>
        <span v-if="elapsedText" class="text-xs opacity-60">{{ elapsedText }}</span>
        <NButton
          v-if="['pending', 'extracting', 'ocr_running', 'saving'].includes(task.status)"
          size="tiny"
          quaternary
          type="error"
          @click.stop="emit('cancel')"
        >
          Cancel
        </NButton>
      </div>
    </div>

    <TaskProgress v-if="task.progress" :progress="task.progress" />

    <div v-if="task.result" class="text-sm opacity-70 mt-1">
      {{ task.result.total_pages }} pages · {{ task.result.total_lines }} lines ·
      {{ task.result.avg_confidence.toFixed(1) }}% confidence
    </div>

    <div v-if="task.error" class="text-sm text-red-500 mt-1">
      {{ task.error }}
    </div>
  </div>
</template>
