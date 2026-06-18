<script setup lang="ts">
import { onMounted } from 'vue'
import { NIcon, NTag, NSpin, NSpace } from 'naive-ui'
import { HardwareChipOutline, CheckmarkCircleOutline, CloseCircleOutline } from '@vicons/ionicons5'
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
        Available
      </NTag>
      <NTag v-else type="warning" size="small">
        <template #icon><NIcon :component="CloseCircleOutline" /></template>
        CPU mode
      </NTag>
    </template>
  </div>

  <!-- Detailed view for settings page -->
  <div v-if="showDetails && gpuInfo" class="mt-3 text-sm space-y-1">
    <p><span class="opacity-60">CUDA version:</span> {{ gpuInfo.cuda_version || 'N/A' }}</p>
    <p><span class="opacity-60">Devices:</span> {{ gpuInfo.device_count }}</p>
    <p v-if="gpuInfo.error" class="text-orange-500">
      <span class="opacity-60">Note:</span> {{ gpuInfo.error }}
    </p>
  </div>
</template>
