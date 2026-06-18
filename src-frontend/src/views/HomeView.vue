<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { NButton, NSpace, NIcon, NEmpty, NText } from 'naive-ui'
import { SettingsOutline, MoonOutline, SunnyOutline, TrashOutline } from '@vicons/ionicons5'
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
const { startTask, cancelTask, getAppInfo } = useTask()
const router = useRouter()
const appVersion = ref('')

onMounted(async () => {
  try {
    const info = await getAppInfo()
    appVersion.value = info.version
  } catch {
    // IPC not available (dev mode without Python)
    appVersion.value = 'dev'
  }
})

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
      <div class="flex items-center gap-3">
        <h1 class="text-xl font-bold">PaddlePDF</h1>
        <span class="text-xs opacity-40">v{{ appVersion }}</span>
      </div>
      <NSpace>
        <NButton quaternary circle @click="appStore.toggleDark" :title="appStore.darkMode ? 'Light mode' : 'Dark mode'">
          <template #icon>
            <NIcon :component="appStore.darkMode ? SunnyOutline : MoonOutline" />
          </template>
        </NButton>
        <NButton quaternary circle @click="router.push('/settings')" title="Settings">
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
        <div class="flex-1" />
        <GpuStatus />
      </div>

      <!-- Drop zone -->
      <FileDropZone
        :disabled="taskStore.hasActiveTask"
        @files-selected="onFileSelected"
      />

      <!-- Active task -->
      <div v-if="taskStore.activeTasks.length > 0" class="space-y-3">
        <h2 class="text-lg font-semibold flex items-center gap-2">
          <span class="inline-block w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
          Processing
        </h2>
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
          <NButton size="small" quaternary type="error" @click="taskStore.clearCompleted">
            <template #icon><NIcon :component="TrashOutline" /></template>
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

      <!-- Empty state -->
      <div
        v-if="taskStore.tasks.length === 0"
        class="card text-center py-16"
      >
        <NEmpty description="No tasks yet. Drop a PDF file above to get started." />
      </div>
    </main>
  </div>
</template>
