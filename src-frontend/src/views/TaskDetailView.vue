<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NButton, NIcon, NSpace, NStatistic, NGrid, NGi } from 'naive-ui'
import { ArrowBackOutline, OpenOutline, DocumentTextOutline } from '@vicons/ionicons5'
import { useTaskStore } from '@/stores/task'
import { useTask } from '@/composables/useTask'
import TaskProgress from '@/components/TaskProgress.vue'

const route = useRoute()
const router = useRouter()
const taskStore = useTaskStore()
const { openPath } = useTask()

const taskId = computed(() => route.params.id as string)
const task = computed(() => taskStore.tasks.find((t) => t.id === taskId.value))
</script>

<template>
  <div class="page">
    <header class="flex items-center gap-3 px-6 py-4 border-b border-gray-200 dark:border-gray-700">
      <NButton quaternary circle @click="router.push('/')">
        <template #icon>
          <NIcon :component="ArrowBackOutline" />
        </template>
      </NButton>
      <h1 class="text-lg font-bold truncate">{{ task?.fileName || 'Task' }}</h1>
    </header>

    <main class="max-w-4xl mx-auto px-6 py-8 space-y-6" v-if="task">
      <!-- Progress (if active) -->
      <TaskProgress v-if="task.progress" :progress="task.progress" />

      <!-- Error -->
      <div v-if="task.error" class="card border-red-300 bg-red-50 dark:bg-red-900/20">
        <p class="text-red-600 dark:text-red-400">{{ task.error }}</p>
      </div>

      <!-- Stats (if completed) -->
      <div v-if="task.result" class="card">
        <h2 class="text-lg font-semibold mb-4">Result</h2>
        <NGrid :cols="4" :x-gap="12" :y-gap="12">
          <NGi>
            <NStatistic label="Pages" :value="task.result.total_pages" />
          </NGi>
          <NGi>
            <NStatistic label="Text lines" :value="task.result.total_lines" />
          </NGi>
          <NGi>
            <NStatistic label="Avg confidence">
              {{ task.result.avg_confidence.toFixed(1) }}%
            </NStatistic>
          </NGi>
          <NGi>
            <NStatistic label="Time">
              {{ task.result.elapsed_seconds.toFixed(1) }}s
            </NStatistic>
          </NGi>
        </NGrid>

        <NSpace class="mt-6">
          <NButton
            v-if="task.result.output_pdf_path"
            type="primary"
            @click="openPath(task.result.output_pdf_path)"
          >
            <template #icon><NIcon :component="DocumentTextOutline" /></template>
            Open Searchable PDF
          </NButton>
          <NButton
            v-if="task.result.output_txt_path"
            @click="openPath(task.result.output_txt_path)"
          >
            <template #icon><NIcon :component="DocumentTextOutline" /></template>
            Open Text File
          </NButton>
          <NButton
            v-if="task.result.output_pdf_path"
            @click="openPath(task.result.output_pdf_path.replace(/[\\/][^\\/]+$/, ''))"
          >
            <template #icon><NIcon :component="OpenOutline" /></template>
            Open Output Folder
          </NButton>
        </NSpace>
      </div>
    </main>
  </div>
</template>
