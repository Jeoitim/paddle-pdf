<script setup lang="ts">
import { onMounted } from 'vue'
import { NIcon, NTag, NSpin, NButton, NSpace } from 'naive-ui'
import {
  HardwareChipOutline,
  CheckmarkCircleOutline,
  CloseCircleOutline,
  RefreshOutline,
} from '@vicons/ionicons5'
import { useModels } from '@/composables/useModels'

defineProps<{ showDetails?: boolean }>()

const { gpuInfo, fetchGpuInfo } = useModels()

onMounted(() => {
  if (!gpuInfo.value) fetchGpuInfo()
})
</script>

<template>
  <div class="flex items-center gap-2">
    <NIcon :component="HardwareChipOutline" :size="18" />
    <span class="text-sm font-medium">GPU:</span>
    <NSpin v-if="!gpuInfo" :size="16" />
    <template v-else>
      <NTag v-if="gpuInfo.available" type="success" size="small">
        <template #icon><NIcon :component="CheckmarkCircleOutline" /></template>
        Available · {{ gpuInfo.device_count }} device(s)
      </NTag>
      <NTag v-else type="warning" size="small">
        <template #icon><NIcon :component="CloseCircleOutline" /></template>
        CPU mode
      </NTag>
    </template>
    <NButton v-if="showDetails" quaternary size="tiny" circle @click="fetchGpuInfo">
      <template #icon><NIcon :component="RefreshOutline" :size="14" /></template>
    </NButton>
  </div>

  <!-- Detailed view for settings page -->
  <div v-if="showDetails && gpuInfo" class="mt-3 text-sm space-y-2">
    <div class="grid grid-cols-2 gap-2">
      <div>
        <span class="opacity-60">CUDA version:</span>
        <span class="ml-1 font-mono">{{ gpuInfo.cuda_version || 'Not detected' }}</span>
      </div>
      <div>
        <span class="opacity-60">CUDA root:</span>
        <span class="ml-1 font-mono text-xs">{{ gpuInfo.cuda_root || 'N/A' }}</span>
      </div>
      <div>
        <span class="opacity-60">GPU devices:</span>
        <span class="ml-1">{{ gpuInfo.device_count }}</span>
      </div>
      <div>
        <span class="opacity-60">Status:</span>
        <span :class="gpuInfo.available ? 'text-green-500' : 'text-orange-500'">
          {{ gpuInfo.available ? 'Ready' : 'Not available' }}
        </span>
      </div>
    </div>
    <div v-if="gpuInfo.error" class="mt-2 p-2 bg-orange-50 dark:bg-orange-900/20 rounded text-xs text-orange-600 dark:text-orange-400">
      <span class="font-medium">Note:</span> {{ gpuInfo.error }}
    </div>
  </div>
</template>
