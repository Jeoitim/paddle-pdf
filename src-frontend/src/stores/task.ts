import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Task, TaskProgress, TaskResult, OcrOptions } from '@/types'

let _nextId = 1

export const useTaskStore = defineStore('task', () => {
  const tasks = ref<Task[]>([])

  const activeTasks = computed(() =>
    tasks.value.filter((t) => ['pending', 'extracting', 'ocr_running', 'saving'].includes(t.status))
  )
  const completedTasks = computed(() =>
    tasks.value.filter((t) => t.status === 'completed')
  )
  const hasActiveTask = computed(() => activeTasks.value.length > 0)

  function addTask(filePath: string, options: OcrOptions): string {
    const id = `task-${_nextId++}`
    const fileName = filePath.split(/[\\/]/).pop() || filePath
    tasks.value.unshift({
      id,
      fileName,
      filePath,
      status: 'pending',
      options,
      progress: null,
      result: null,
      error: null,
      createdAt: Date.now(),
    })
    return id
  }

  function updateProgress(id: string, progress: TaskProgress) {
    const task = tasks.value.find((t) => t.id === id)
    if (task) {
      task.progress = progress
      task.status = progress.status
    }
  }

  function completeTask(id: string, result: TaskResult) {
    const task = tasks.value.find((t) => t.id === id)
    if (task) {
      task.status = 'completed'
      task.result = result
      task.progress = null
    }
  }

  function failTask(id: string, error: string) {
    const task = tasks.value.find((t) => t.id === id)
    if (task) {
      task.status = 'failed'
      task.error = error
      task.progress = null
    }
  }

  function removeTask(id: string) {
    tasks.value = tasks.value.filter((t) => t.id !== id)
  }

  function clearCompleted() {
    tasks.value = tasks.value.filter((t) => t.status !== 'completed')
  }

  return {
    tasks,
    activeTasks,
    completedTasks,
    hasActiveTask,
    addTask,
    updateProgress,
    completeTask,
    failTask,
    removeTask,
    clearCompleted,
  }
})
