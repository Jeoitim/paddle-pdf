<script setup lang="ts">
import { NButton, NSpace, NIcon } from 'naive-ui'
import { SettingsOutline, MoonOutline, SunnyOutline } from '@vicons/ionicons5'
import { useAppStore } from '@/stores/app'
import { useSettingsStore } from '@/stores/settings'
import { useTaskStore } from '@/stores/task'
import { useTask } from '@/composables/useTask'
import FileDropZone from '@/components/FileDropZone.vue'
import TaskCard from '@/components/TaskCard.vue'
import ModelSelector from '@/components/ModelSelector.vue'
import GpuStatus from '@/components/GpuStatus.vue'
import { useRouter } from 'vue-router'

const appStore = useAppStore()
const settingsStore = useSettingsStore()
const taskStore = useTaskStore()
const { startTask, cancelTask } = useTask()
const router = useRouter()

async function onFileSelected(paths: string[]) {
  for (const path of paths) {
    await startTask(path, { ...settingsStore.options })
  }
}

function viewTask(id: string) {
  router.push({ name: 'task-detail', params: { id } })
}
</script>

<template>
  <div class="page">
    <!-- Header -->
    <header class="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
      <h1 class="text-xl font-bold">PaddlePDF</h1>
      <NSpace>
        <NButton quaternary circle @click="appStore.toggleDark">
          <template #icon>
            <NIcon :component="appStore.darkMode ? SunnyOutline : MoonOutline" />
          </template>
        </NButton>
        <NButton quaternary circle @click="router.push('/settings')">
          <template #icon>
            <NIcon :component="SettingsOutline" />
          </template>
        </NButton>
      </NSpace>
    </header>

    <!-- Main content -->
    <main class="max-w-4xl mx-auto px-6 py-8 space-y-6">
      <!-- Config bar -->
      <div class="card flex items-center gap-4 flex-wrap">
        <ModelSelector />
        <GpuStatus />
      </div>

      <!-- Drop zone -->
      <FileDropZone
        :disabled="taskStore.hasActiveTask"
        @files-selected="onFileSelected"
      />

      <!-- Active task -->
      <div v-if="taskStore.activeTasks.length > 0" class="space-y-3">
        <h2 class="text-lg font-semibold">Processing</h2>
        <TaskCard
          v-for="task in taskStore.activeTasks"
          :key="task.id"
          :task="task"
          @cancel="cancelTask"
          @click="viewTask(task.id)"
        />
      </div>

      <!-- Completed tasks -->
      <div v-if="taskStore.completedTasks.length > 0" class="space-y-3">
        <div class="flex items-center justify-between">
          <h2 class="text-lg font-semibold">Completed</h2>
          <NButton size="small" quaternary @click="taskStore.clearCompleted">
            Clear all
          </NButton>
        </div>
        <TaskCard
          v-for="task in taskStore.completedTasks"
          :key="task.id"
          :task="task"
          @click="viewTask(task.id)"
        />
      </div>
    </main>
  </div>
</template>
