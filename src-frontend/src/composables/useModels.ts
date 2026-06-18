/**
 * Model management composable.
 */
import { ref } from 'vue'
import { ipcInvoke } from './useIpc'
import type { ModelInfo, GpuInfo } from '@/types'

const models = ref<ModelInfo[]>([])
const gpuInfo = ref<GpuInfo | null>(null)
const loading = ref(false)

export function useModels() {
  async function fetchModels() {
    loading.value = true
    try {
      models.value = await ipcInvoke<ModelInfo[]>('list_models')
    } finally {
      loading.value = false
    }
  }

  async function fetchGpuInfo() {
    gpuInfo.value = await ipcInvoke<GpuInfo>('check_gpu')
  }

  async function downloadModel(name: string) {
    return ipcInvoke<{ success: boolean }>('download_model', { name })
  }

  return { models, gpuInfo, loading, fetchModels, fetchGpuInfo, downloadModel }
}
