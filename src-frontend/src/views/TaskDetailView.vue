<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  NButton, NIcon, NSpace, NStatistic, NGrid, NGi,
  NTimeline, NTimelineItem, NCollapse, NCollapseItem, NTag,
} from 'naive-ui'
import {
  ArrowBackOutline, OpenOutline, DocumentTextOutline,
  FolderOpenOutline, CheckmarkCircleOutline,
} from '@vicons/ionicons5'
import { useTaskStore } from '@/stores/task'
import { useTask } from '@/composables/useTask'
import TaskProgress from '@/components/TaskProgress.vue'
import TextPanel from '@/components/TextPanel.vue'

const route = useRoute()
const router = useRouter()
const taskStore = useTaskStore()
const { openPath, revealInExplorer } = useTask()

const taskId = computed(() => route.params.id as string)
const task = computed(() => taskStore.tasks.find((t) => t.id === taskId.value))

const allText = computed(() => {
  if (!task.value?.result) return ''
  // Reconstruct full text from the task's OCR data
  // This would normally come from the text file, but we can build it from the result
  return `Pages: ${task.value.result.total_pages}\nLines: ${task.value.result.total_lines}\nConfidence: ${task.value.result.avg_confidence.toFixed(1)}%`
})

function getParentDir(filePath: string): string {
  return filePath.replace(/[\\/][^\\/]+$/, '')
}
</script>

<template>
  <div class="page">
    <header class="flex items-center gap-3 px-6 py-4 border-b border-gray-200 dark:border-gray-700">
      <NButton quaternary circle @click="router.push('/')">
        <template #icon>
          <NIcon :component="ArrowBackOutline" />
        </template>
      </NButton>
      <div class="min-w-0 flex-1">
        <h1 class="text-lg font-bold truncate">{{ task?.fileName || 'Task' }}</h1>
        <p v-if="task?.filePath" class="text-xs opacity-50 truncate">{{ task.filePath }}</p>
      </div>
      <NTag
        v-if="task"
        :type="task.status === 'completed' ? 'success' : task.status === 'failed' ? 'error' : 'info'"
        size="small"
      >
        {{ task.status }}
      </NTag>
    </header>

    <main class="max-w-4xl mx-auto px-6 py-8 space-y-6" v-if="task">
      <!-- Progress (if active) -->
      <div v-if="task.progress" class="card">
        <TaskProgress :progress="task.progress" />
      </div>

      <!-- Error -->
      <div v-if="task.error" class="card border-red-300 bg-red-50 dark:bg-red-900/20">
        <p class="text-red-600 dark:text-red-400 font-medium">Error</p>
        <p class="text-red-500 dark:text-red-400 text-sm mt-1">{{ task.error }}</p>
      </div>

      <!-- Stats (if completed) -->
      <div v-if="task.result" class="card">
        <h2 class="text-lg font-semibold mb-4">Result Summary</h2>
        <NGrid :cols="4" :x-gap="16" :y-gap="16" responsive="screen" :item-responsive="true">
          <NGi :span="2">
            <NStatistic label="Pages processed" :value="task.result.total_pages">
              <template #prefix>
                <NIcon :component="DocumentTextOutline" />
              </template>
            </NStatistic>
          </NGi>
          <NGi :span="2">
            <NStatistic label="Text lines found" :value="task.result.total_lines" />
          </NGi>
          <NGi :span="2">
            <NStatistic label="Average confidence">
              <template #default>
                <span :class="task.result.avg_confidence >= 80 ? 'text-green-500' : task.result.avg_confidence >= 60 ? 'text-yellow-500' : 'text-red-500'">
                  {{ task.result.avg_confidence.toFixed(1) }}%
                </span>
              </template>
            </NStatistic>
          </NGi>
          <NGi :span="2">
            <NStatistic label="Processing time">
              <template #default>
                {{ task.result.elapsed_seconds.toFixed(1) }}s
              </template>
              <template #suffix>
                <span class="text-xs opacity-50 ml-1">
                  ({{ (task.result.elapsed_seconds / task.result.total_pages).toFixed(1) }}s/page)
                </span>
              </template>
            </NStatistic>
          </NGi>
        </NGrid>
      </div>

      <!-- Output files -->
      <div v-if="task.result" class="card">
        <h2 class="text-lg font-semibold mb-4">Output Files</h2>
        <NSpace vertical :size="12">
          <!-- Searchable PDF -->
          <div
            v-if="task.result.output_pdf_path"
            class="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-900 rounded-lg"
          >
            <div class="flex items-center gap-3 min-w-0">
              <NIcon :component="DocumentTextOutline" :size="24" class="text-blue-500 shrink-0" />
              <div class="min-w-0">
                <p class="font-medium truncate">{{ task.result.output_pdf_path.split(/[\\/]/).pop() }}</p>
                <p class="text-xs opacity-50">Searchable PDF with invisible text layer</p>
              </div>
            </div>
            <NSpace size="small" class="shrink-0">
              <NButton size="small" type="primary" @click="openPath(task.result.output_pdf_path)">
                Open
              </NButton>
              <NButton size="small" quaternary @click="revealInExplorer(task.result.output_pdf_path)">
                <template #icon><NIcon :component="FolderOpenOutline" /></template>
              </NButton>
            </NSpace>
          </div>

          <!-- Text file -->
          <div
            v-if="task.result.output_txt_path"
            class="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-900 rounded-lg"
          >
            <div class="flex items-center gap-3 min-w-0">
              <NIcon :component="DocumentTextOutline" :size="24" class="text-green-500 shrink-0" />
              <div class="min-w-0">
                <p class="font-medium truncate">{{ task.result.output_txt_path.split(/[\\/]/).pop() }}</p>
                <p class="text-xs opacity-50">Plain text with all OCR results</p>
              </div>
            </div>
            <NSpace size="small" class="shrink-0">
              <NButton size="small" @click="openPath(task.result.output_txt_path)">
                Open
              </NButton>
              <NButton size="small" quaternary @click="revealInExplorer(task.result.output_txt_path)">
                <template #icon><NIcon :component="FolderOpenOutline" /></template>
              </NButton>
            </NSpace>
          </div>

          <!-- Output folder -->
          <NButton
            v-if="task.result.output_pdf_path"
            quaternary
            block
            @click="openPath(getParentDir(task.result.output_pdf_path))"
          >
            <template #icon><NIcon :component="FolderOpenOutline" /></template>
            Open Output Folder
          </NButton>
        </NSpace>
      </div>

      <!-- Processing options used -->
      <div v-if="task" class="card">
        <h2 class="text-lg font-semibold mb-3">Processing Options</h2>
        <div class="grid grid-cols-2 gap-2 text-sm">
          <div><span class="opacity-60">Model:</span> {{ task.options.model_name }}</div>
          <div><span class="opacity-60">GPU:</span> {{ task.options.use_gpu ? 'Yes' : 'No' }}</div>
          <div><span class="opacity-60">DPI:</span> {{ task.options.dpi }}</div>
          <div><span class="opacity-60">Angle cls:</span> {{ task.options.angle_cls ? 'On' : 'Off' }}</div>
          <div v-if="task.options.max_pages">
            <span class="opacity-60">Max pages:</span> {{ task.options.max_pages }}
          </div>
          <div>
            <span class="opacity-60">Confidence:</span> {{ task.options.show_confidence ? 'Shown' : 'Hidden' }}
          </div>
        </div>
      </div>
    </main>

    <!-- Task not found -->
    <main v-else class="max-w-4xl mx-auto px-6 py-8">
      <div class="card text-center py-12">
        <p class="text-lg opacity-60">Task not found</p>
        <NButton class="mt-4" @click="router.push('/')">Back to Home</NButton>
      </div>
    </main>
  </div>
</template>
