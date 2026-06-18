<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { NIcon } from 'naive-ui'
import { CloudUploadOutline } from '@vicons/ionicons5'
import { open } from '@tauri-apps/plugin-dialog'
import { onDragDrop, onDragEnter, onDragLeave } from '@/composables/useIpc'

const props = defineProps<{ disabled?: boolean }>()
const emit = defineEmits<{ 'files-selected': [paths: string[]] }>()
const dragging = ref(false)
const unlisteners: (() => void)[] = []

onMounted(async () => {
  // Tauri native drag-drop — works across the whole window
  unlisteners.push(
    await onDragDrop((paths) => {
      if (props.disabled) return
      const pdfs = paths.filter((p) => p.toLowerCase().endsWith('.pdf'))
      if (pdfs.length > 0) emit('files-selected', pdfs)
      dragging.value = false
    }),
  )
  unlisteners.push(await onDragEnter(() => { if (!props.disabled) dragging.value = true }))
  unlisteners.push(await onDragLeave(() => { dragging.value = false }))
})

onUnmounted(() => unlisteners.forEach((u) => u()))

async function openFile() {
  if (props.disabled) return
  const selected = await open({
    multiple: true,
    filters: [{ name: 'PDF', extensions: ['pdf'] }],
  })
  if (selected) {
    const paths = Array.isArray(selected) ? selected : [selected]
    emit('files-selected', paths)
  }
}
</script>

<template>
  <div
    class="card flex flex-col items-center justify-center gap-4 py-12 cursor-pointer transition-all duration-200 border-2 border-dashed select-none"
    :class="[
      dragging
        ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20 scale-[1.01]'
        : 'border-gray-300 dark:border-gray-600 hover:border-blue-400',
      disabled ? 'opacity-50 cursor-not-allowed' : '',
    ]"
    @click="openFile"
  >
    <NIcon
      :component="CloudUploadOutline"
      :size="48"
      :class="dragging ? 'text-blue-500' : 'text-gray-400'"
      class="transition-colors"
    />
    <div class="text-center">
      <p class="text-lg font-medium">
        {{ dragging ? 'Release to add PDF' : 'Drop PDF files here or click to browse' }}
      </p>
      <p class="text-sm opacity-60 mt-1">Supports .pdf files · Multiple files allowed</p>
    </div>
  </div>
</template>
