/**
 * IPC communication layer — wraps pytauri's pyInvoke() and Tauri listen().
 *
 * pytauri routes ALL IPC through a single "pyfunc" Tauri command.
 * We must use `pyInvoke` from `tauri-plugin-pytauri-api`, NOT raw `invoke`.
 */
import { pyInvoke } from 'tauri-plugin-pytauri-api'
import { listen, type UnlistenFn } from '@tauri-apps/api/event'

/**
 * Call a Python command via pytauri IPC.
 * The `args` object is JSON-serialized and passed as `body` to the Python command.
 * The Python command receives it as a Pydantic BaseModel.
 */
export async function ipcInvoke<T>(command: string, args?: Record<string, unknown>): Promise<T> {
  return pyInvoke<T>(command, args ?? {})
}

/** Listen for events emitted by Python backend via Emitter.emit() */
export function ipcListen<T>(event: string, handler: (payload: T) => void): Promise<UnlistenFn> {
  return listen<T>(event, (e) => handler(e.payload))
}

/** Listen for Tauri native drag-drop events */
export function onDragDrop(handler: (paths: string[]) => void): Promise<UnlistenFn> {
  return listen<{ paths: string[]; position: { x: number; y: number } }>(
    'tauri://drag-drop',
    (e) => {
      if (e.payload.paths?.length) {
        handler(e.payload.paths)
      }
    },
  )
}

/** Listen for Tauri drag-drop hover events */
export function onDragEnter(handler: () => void): Promise<UnlistenFn> {
  return listen('tauri://drag-enter', () => handler())
}

/** Listen for Tauri drag-drop leave events */
export function onDragLeave(handler: () => void): Promise<UnlistenFn> {
  return listen('tauri://drag-leave', () => handler())
}
