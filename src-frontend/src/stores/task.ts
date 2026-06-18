import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Task, TaskProgress, TaskResult, OcrOptions } from '@/types'

let _nextId = 1

export const useTaskStore = defineStore('task', () => {
  const tasks = ref<Task[]>([])

  // ── Computed slices ──────────────────────────────────────

  const pendingTasks = computed(() =>
    tasks.value.filter((t) => t.status === 'pending'),
  )

  const activeTasks = computed(() =>
    tasks.value.filter((t) =>
      ['extracting', 'ocr_running', 'saving'].includes(t.status),
    ),
  )

  const completedTasks = computed(() =>
    tasks.value.filter((t) => t.status === 'completed'),
  )

  const finishedTasks = computed(() =>
    tasks.value.filter((t) =>
      ['completed', 'failed', 'cancelled'].includes(t.status),
    ),
  )

  /** True when at least one task is running (not just pending). */
  const hasRunningTask = computed(() => activeTasks.value.length > 0)

  // ── Mutations ────────────────────────────────────────────

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

  function cancelTask(id: string) {
    const task = tasks.value.find((t) => t.id === id)
    if (task && ['pending', 'extracting', 'ocr_running', 'saving'].includes(task.status)) {
      task.status = 'cancelled'
      task.progress = null
    }
  }

  function removeTask(id: string) {
    tasks.value = tasks.value.filter((t) => t.id !== id)
  }

  function clearFinished() {
    tasks.value = tasks.value.filter(
      (t) => !['completed', 'failed', 'cancelled'].includes(t.status),
    )
  }

  return {
    tasks,
    pendingTasks,
    activeTasks,
    completedTasks,
    finishedTasks,
    hasRunningTask,
    addTask,
    updateProgress,
    completeTask,
    failTask,
    cancelTask,
    removeTask,
    clearFinished,
  }
})
