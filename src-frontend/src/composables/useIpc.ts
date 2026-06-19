import { invoke } from '@tauri-apps/api/core'
import { listen, type UnlistenFn } from '@tauri-apps/api/event'

// Mapping of frontend commands to HTTP endpoints and methods
const COMMAND_MAPPING: Record<string, { path: string; method: 'GET' | 'POST' }> = {
  get_app_info: { path: 'app_info', method: 'GET' },
  get_queue_status: { path: 'queue_status', method: 'GET' },
  list_models: { path: 'list_models', method: 'GET' },
  check_gpu: { path: 'check_gpu', method: 'GET' },
  diagnose_system: { path: 'diagnose_system', method: 'GET' },
  
  process_task: { path: 'process_task', method: 'POST' },
  cancel_task: { path: 'cancel_task', method: 'POST' },
  remove_task: { path: 'remove_task', method: 'POST' },
  download_model: { path: 'download_model', method: 'POST' },
  open_path: { path: 'open_path', method: 'POST' },
  reveal_in_explorer: { path: 'reveal_in_explorer', method: 'POST' },
  shutdown: { path: 'shutdown', method: 'POST' },
}

let cachedPort: number | null = null

/**
 * Retrieve the dynamic port our Python backend process is listening on.
 * Retries up to 30 times (6 seconds) to allow the backend to start in dev mode.
 */
async function getBackendPort(): Promise<number> {
  if (cachedPort !== null) {
    return cachedPort
  }
  for (let i = 0; i < 30; i++) {
    try {
      const port = await invoke<number | null>('get_backend_port')
      if (port) {
        cachedPort = port
        return port
      }
    } catch (e) {
      console.warn('[ipc] Error getting backend port, retrying...', e)
    }
    await new Promise((resolve) => setTimeout(resolve, 200))
  }
  throw new Error('Failed to get backend port from Tauri')
}

/**
 * Call a Python command via HTTP.
 */
export async function ipcInvoke<T>(command: string, args?: Record<string, unknown>): Promise<T> {
  const mapping = COMMAND_MAPPING[command]
  const path = mapping ? mapping.path : command
  const method = mapping ? mapping.method : 'POST'
  
  const port = await getBackendPort()
  const url = `http://127.0.0.1:${port}/${path}`
  
  const options: RequestInit = {
    method,
    headers: {
      'Content-Type': 'application/json',
    },
  }
  
  if (method === 'POST') {
    options.body = JSON.stringify(args ?? {})
  }
  
  const response = await fetch(url, options)
  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(`HTTP error! status: ${response.status}, body: ${errorText}`)
  }
  
  return response.json() as Promise<T>
}

// SSE Connection state
let eventSource: EventSource | null = null
const eventListeners = new Map<string, Set<(payload: any) => void>>()

/** Initialize singleton SSE connection */
async function initEventSource() {
  if (eventSource) return
  
  const port = await getBackendPort()
  const url = `http://127.0.0.1:${port}/events`
  console.log(`[ipc] Connecting to SSE event stream at: ${url}`)
  
  eventSource = new EventSource(url)
  
  eventSource.onopen = () => {
    console.log('[ipc] SSE EventSource connected')
  }
  
  eventSource.onerror = (err) => {
    console.error('[ipc] SSE EventSource error:', err)
  }
}

/** Listen for events emitted by Python backend via SSE */
export async function ipcListen<T>(event: string, handler: (payload: T) => void): Promise<UnlistenFn> {
  if (!eventListeners.has(event)) {
    eventListeners.set(event, new Set())
  }
  eventListeners.get(event)!.add(handler)
  
  await initEventSource()
  
  const sseHandler = (e: MessageEvent) => {
    try {
      const parsed = JSON.parse(e.data)
      const payload = parsed.data
      const handlers = eventListeners.get(event)
      if (handlers) {
        for (const h of handlers) {
          h(payload)
        }
      }
    } catch (err) {
      console.error(`[ipc] Failed to parse SSE message for event ${event}:`, err)
    }
  }
  
  eventSource!.addEventListener(event, sseHandler)
  
  return () => {
    const handlers = eventListeners.get(event)
    if (handlers) {
      handlers.delete(handler)
    }
    if (eventSource) {
      eventSource.removeEventListener(event, sseHandler)
    }
  }
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
