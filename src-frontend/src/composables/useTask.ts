/**
 * Task operations — composable for managing OCR task queue.
 *
 * Key changes vs old version:
 * - ``startTask`` submits to the backend queue and returns immediately (non-blocking).
 * - A single global progress listener routes events by ``task_id``.
 * - ``cancelTask`` targets a specific task by ID.
 */
import { useTaskStore } from '@/stores/task'
import { ipcInvoke, ipcListen } from './useIpc'
import type { OcrOptions, TaskProgress } from '@/types'

let _progressUnlisten: (() => void) | null = null

export function useTask() {
  const store = useTaskStore()

  /** Ensure the global progress listener is running. */
  async function ensureProgressListener() {
    if (_progressUnlisten) return
    _progressUnlisten = await ipcListen<TaskProgress>('task://progress', (progress) => {
      store.updateProgress(progress.task_id, progress)
    })
  }

  /**
   * Submit a file to the backend queue.  Returns the frontend task ID
   * immediately — the actual OCR runs in the background.
   */
  async function startTask(filePath: string, options: OcrOptions): Promise<string> {
    const id = store.addTask(filePath, options)

    // Make sure the global listener is active
    await ensureProgressListener()

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
