/**
 * Task operations — composable for managing OCR tasks.
 */
import { useTaskStore } from '@/stores/task'
import { ipcInvoke, ipcListen } from './useIpc'
import type { OcrOptions, TaskProgress, TaskResult } from '@/types'

export function useTask() {
  const store = useTaskStore()

  /** Start processing a file */
  async function startTask(filePath: string, options: OcrOptions) {
    const id = store.addTask(filePath, options)

    // Listen for progress events
    const unlisten = await ipcListen<TaskProgress>('task://progress', (progress) => {
      store.updateProgress(id, progress)
    })

    try {
      const res = await ipcInvoke<{ success: boolean; result?: TaskResult; error?: string }>(
        'process_task',
        { input_path: filePath, options },
      )

      if (res.success && res.result) {
        store.completeTask(id, res.result)
      } else {
        store.failTask(id, res.error || 'Unknown error')
      }
    } catch (e: any) {
      store.failTask(id, e.toString())
    } finally {
      unlisten()
    }
  }

  /** Cancel the active task */
  async function cancelTask() {
    await ipcInvoke('cancel_task')
  }

  /** Open a file or folder in the system file manager */
  async function openPath(path: string) {
    await ipcInvoke('open_path', { path })
  }

  return { startTask, cancelTask, openPath }
}
