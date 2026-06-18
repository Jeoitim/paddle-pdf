/**
 * Model management composable.
 */
import { ref } from 'vue'
import { ipcInvoke } from './useIpc'
import type { ModelInfo, GpuInfo } from '@/types'

const models = ref<ModelInfo[]>([])
const gpuInfo = ref<GpuInfo | null>(null)
const loading = ref(false)
const downloading = ref<string | null>(null)

export function useModels() {
  async function fetchModels() {
    loading.value = true
    try {
      // list_models returns bytes (JSON encoded)
      const raw = await ipcInvoke<string>('list_models', {})
      models.value = typeof raw === 'string' ? JSON.parse(raw) : raw
    } finally {
      loading.value = false
    }
  }

  async function fetchGpuInfo() {
    try {
      gpuInfo.value = await ipcInvoke<GpuInfo>('check_gpu', {})
    } catch (e) {
      gpuInfo.value = { available: false, cuda_version: null, cuda_root: null, device_count: 0, error: String(e) }
    }
  }

  async function downloadModel(name: string) {
    downloading.value = name
    try {
      const res = await ipcInvoke<{ success: boolean; name: string }>('download_model', { name })
      if (res.success) await fetchModels()
      return res
    } finally {
      downloading.value = null
    }
  }

  async function diagnoseSystem() {
    const raw = await ipcInvoke<string>('diagnose_system', {})
    return typeof raw === 'string' ? JSON.parse(raw) : raw
  }

  return {
    models,
    gpuInfo,
    loading,
    downloading,
    fetchModels,
    fetchGpuInfo,
    downloadModel,
    diagnoseSystem,
  }
}
