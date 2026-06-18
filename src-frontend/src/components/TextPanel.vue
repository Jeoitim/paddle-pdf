<script setup lang="ts">
import { ref, computed } from 'vue'
import { NButton, NIcon, NInput, NSpace } from 'naive-ui'
import { CopyOutline, DownloadOutline } from '@vicons/ionicons5'

const props = defineProps<{
  text: string
  title?: string
  maxHeight?: string
}>()

const copied = ref(false)

async function copyToClipboard() {
  try {
    await navigator.clipboard.writeText(props.text)
    copied.value = true
    setTimeout(() => (copied.value = false), 2000)
  } catch {
    // Fallback for older browsers
    const ta = document.createElement('textarea')
    ta.value = props.text
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
    copied.value = true
    setTimeout(() => (copied.value = false), 2000)
  }
}

function downloadAsText() {
  const blob = new Blob([props.text], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${props.title || 'text'}.txt`
  a.click()
  URL.revokeObjectURL(url)
}
</script>

<template>
  <div class="card">
    <div v-if="title" class="flex items-center justify-between mb-3">
      <h3 class="font-semibold">{{ title }}</h3>
      <NSpace size="small">
        <NButton size="tiny" quaternary @click="copyToClipboard">
          <template #icon>
            <NIcon :component="CopyOutline" />
          </template>
          {{ copied ? 'Copied!' : 'Copy' }}
        </NButton>
        <NButton size="tiny" quaternary @click="downloadAsText">
          <template #icon>
            <NIcon :component="DownloadOutline" />
          </template>
          Save
        </NButton>
      </NSpace>
    </div>
    <div
      class="bg-gray-50 dark:bg-gray-900 rounded-lg p-3 overflow-auto font-mono text-sm leading-relaxed whitespace-pre-wrap"
      :style="{ maxHeight: maxHeight || '400px' }"
    >{{ text }}</div>
  </div>
</template>
