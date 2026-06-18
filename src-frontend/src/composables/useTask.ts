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
      // pytauri process_task receives body as JSON
      const res = await ipcInvoke<TaskResult>(
        'process_task',
        {
          input_path: filePath,
          model_name: options.model_name,
          use_gpu: options.use_gpu,
          dpi: options.dpi,
          max_pages: options.max_pages,
          angle_cls: options.angle_cls,
          show_confidence: options.show_confidence,
        },
      )

      if (res.success) {
        store.completeTask(id, res)
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
    try {
      await ipcInvoke('cancel_task', {})
    } catch (e) {
      console.warn('Cancel failed:', e)
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

  /** Test IPC round-trip */
  async function greet(name: string = 'World') {
    return ipcInvoke<{ message: string }>('greet', { name })
  }

  return { startTask, cancelTask, openPath, revealInExplorer, getAppInfo, greet }
}
