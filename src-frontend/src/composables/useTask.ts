/**
 * Task operations — composable for managing OCR task queue.
 *
 * Key changes vs old version:
 * - ``startTask`` submits to the backend queue and returns immediately (non-blocking).
 * - Global listeners for progress, completion, and failure events route by ``task_id``.
 * - ``cancelTask`` targets a specific task by ID.
 */
import { useTaskStore } from '@/stores/task'
import { ipcInvoke, ipcListen } from './useIpc'
import type { OcrOptions, TaskProgress, TaskResult } from '@/types'

let _listenersSetup = false

/** Payload shape for task://completed events */
interface TaskCompletedEvent {
  task_id: string
  input_path: string
  output_pdf_path: string
  output_txt_path: string
  total_pages: number
  total_lines: number
  avg_confidence: number
  elapsed_seconds: number
}

/** Payload shape for task://failed / task://cancelled events */
interface TaskFailedEvent {
  task_id: string
  error: string
}

export function useTask() {
  const store = useTaskStore()

  /** Set up all global event listeners once. */
  async function ensureListeners() {
    if (_listenersSetup) return
    _listenersSetup = true

    // Progress events (per-page updates)
    await ipcListen<TaskProgress>('task://progress', (progress) => {
      store.updateProgress(progress.task_id, progress)
    })

    // Completion events (carries full result data)
    await ipcListen<TaskCompletedEvent>('task://completed', (payload) => {
      const result: TaskResult = {
        success: true,
        input_path: payload.input_path,
        output_pdf_path: payload.output_pdf_path,
        output_txt_path: payload.output_txt_path,
        total_pages: payload.total_pages,
        total_lines: payload.total_lines,
        avg_confidence: payload.avg_confidence,
        elapsed_seconds: payload.elapsed_seconds,
        error: null,
      }
      store.completeTask(payload.task_id, result)
    })

    // Failure events
    await ipcListen<TaskFailedEvent>('task://failed', (payload) => {
      store.failTask(payload.task_id, payload.error)
    })

    // Cancellation events (backend emits on cancel)
    await ipcListen<TaskFailedEvent>('task://cancelled', (payload) => {
      store.cancelTask(payload.task_id)
    })
  }

  /**
   * Submit a file to the backend queue.  Returns the frontend task ID
   * immediately — the actual OCR runs in the background.
   */
  async function startTask(filePath: string, options: OcrOptions): Promise<string> {
    const id = store.addTask(filePath, options)

    // Make sure global listeners are active
    await ensureListeners()

    // Submit to backend queue (returns instantly)
    await ipcInvoke('process_task', {
      task_id: id,
      input_path: filePath,
      model_name: options.model_name,
      use_gpu: options.use_gpu,
      dpi: options.dpi,
      max_pages: options.max_pages,
      angle_cls: options.angle_cls,
      show_confidence: options.show_confidence,
    })

    return id
  }

  /** Cancel a specific task by ID. */
  async function cancelTask(taskId: string) {
    store.cancelTask(taskId)
    try {
      await ipcInvoke('cancel_task', { task_id: taskId })
    } catch (e) {
      console.warn('Cancel failed:', e)
    }
  }

  /** Remove a finished task from the backend queue store. */
  async function removeTask(taskId: string) {
    store.removeTask(taskId)
    try {
      await ipcInvoke('remove_task', { task_id: taskId })
    } catch {
      // ignore — task may already be gone
    }
  }

  /** Open a file or folder in the system file manager */
  async function openPath(path: string) {
    await ipcInvoke('open_path', { path })
  }

  /** Reveal a file in the system file explorer */
  async function revealInExplorer(path: string) {
    await ipcInvoke('reveal_in_explorer', { path })
  }

  /** Get app info from backend */
  async function getAppInfo() {
    return ipcInvoke<{ name: string; version: string; python_version: string; platform: string }>(
      'get_app_info',
      {},
    )
  }

  return { startTask, cancelTask, removeTask, openPath, revealInExplorer, getAppInfo }
}
