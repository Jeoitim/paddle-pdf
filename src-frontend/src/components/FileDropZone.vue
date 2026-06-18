<script setup lang="ts">
import { ref } from 'vue'
import { NIcon, NText } from 'naive-ui'
import { CloudUploadOutline, DocumentOutline } from '@vicons/ionicons5'
import { open } from '@tauri-apps/plugin-dialog'

const props = defineProps<{ disabled?: boolean }>()
const emit = defineEmits<{ 'files-selected': [paths: string[]] }>()
const dragging = ref(false)

function onDragOver(e: DragEvent) {
  e.preventDefault()
  if (!props.disabled) dragging.value = true
}

function onDragLeave() {
  dragging.value = false
}

function onDrop(e: DragEvent) {
  e.preventDefault()
  dragging.value = false
  if (props.disabled) return
  // Tauri drag-drop provides file paths
  const paths = e.dataTransfer?.files
  if (paths && paths.length > 0) {
    // In Tauri, we need to use the drag-drop event payload
    // For now, use the native file dialog as primary method
  }
}

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
    class="card flex flex-col items-center justify-center gap-4 py-12 cursor-pointer transition-all duration-200 border-2 border-dashed"
    :class="[
      dragging ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20' : 'border-gray-300 dark:border-gray-600 hover:border-blue-400',
      disabled ? 'opacity-50 cursor-not-allowed' : '',
    ]"
    @dragover="onDragOver"
    @dragleave="onDragLeave"
    @drop="onDrop"
    @click="openFile"
  >
    <NIcon :component="CloudUploadOutline" :size="48" class="text-gray-400" />
    <div class="text-center">
      <p class="text-lg font-medium">
        {{ dragging ? 'Drop PDF here' : 'Drop PDF files or click to select' }}
      </p>
      <p class="text-sm opacity-60 mt-1">Supports .pdf files</p>
    </div>
  </div>
</template>
