/**
 * IPC communication layer — wraps Tauri invoke() and listen().
 * This is the ONLY module that imports from @tauri-apps/api.
 */
import { invoke } from '@tauri-apps/api/core'
import { listen, type UnlistenFn } from '@tauri-apps/api/event'

/** Call a Python command via pytauri IPC */
export async function ipcInvoke<T>(command: string, args?: Record<string, unknown>): Promise<T> {
  return invoke<T>(command, args)
}

/** Listen for events emitted by Python backend */
export function ipcListen<T>(event: string, handler: (payload: T) => void): Promise<UnlistenFn> {
  return listen<T>(event, (e) => handler(e.payload))
}
