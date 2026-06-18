import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { OcrOptions } from '@/types'

const STORAGE_KEY = 'paddlepdf-settings'

function loadDefaults(): OcrOptions {
  const saved = localStorage.getItem(STORAGE_KEY)
  if (saved) {
    try { return JSON.parse(saved) } catch { /* ignore */ }
  }
  return {
    model_name: 'ch',
    use_gpu: false,
    dpi: 300,
    angle_cls: true,
    show_confidence: false,
  }
}

export const useSettingsStore = defineStore('settings', () => {
  const options = ref<OcrOptions>(loadDefaults())

  function update(partial: Partial<OcrOptions>) {
    Object.assign(options.value, partial)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(options.value))
  }

  function reset() {
    options.value = {
      model_name: 'ch',
      use_gpu: false,
      dpi: 300,
      angle_cls: true,
      show_confidence: false,
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(options.value))
  }

  return { options, update, reset }
})
