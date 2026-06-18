<script setup lang="ts">
import { onMounted } from 'vue'
import { NIcon, NTag, NSpin, NButton } from 'naive-ui'
import {
  HardwareChipOutline,
  CheckmarkCircleOutline,
  CloseCircleOutline,
  RefreshOutline,
} from '@vicons/ionicons5'
import { useI18n } from 'vue-i18n'
import { useModels } from '@/composables/useModels'

const { t } = useI18n()
defineProps<{ showDetails?: boolean }>()

const { gpuInfo, fetchGpuInfo } = useModels()

onMounted(() => {
  if (!gpuInfo.value) fetchGpuInfo()
})
</script>

<template>
  <div class="flex items-center gap-2">
    <NIcon :component="HardwareChipOutline" :size="18" />
    <span class="text-sm font-medium">{{ t('gpu.label') }}</span>
    <NSpin v-if="!gpuInfo" :size="16" />
    <template v-else>
      <NTag v-if="gpuInfo.available" type="success" size="small">
        <template #icon><NIcon :component="CheckmarkCircleOutline" /></template>
        {{ t('gpu.available', { n: gpuInfo.device_count }) }}
      </NTag>
      <NTag v-else type="warning" size="small">
        <template #icon><NIcon :component="CloseCircleOutline" /></template>
        {{ t('gpu.cpuMode') }}
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
        <span class="opacity-60">{{ t('gpu.cudaVersion') }}:</span>
        <span class="ml-1 font-mono">{{ gpuInfo.cuda_version || 'N/A' }}</span>
      </div>
      <div>
        <span class="opacity-60">{{ t('gpu.cudaRoot') }}:</span>
        <span class="ml-1 font-mono text-xs">{{ gpuInfo.cuda_root || 'N/A' }}</span>
      </div>
      <div>
        <span class="opacity-60">{{ t('gpu.devices') }}:</span>
        <span class="ml-1">{{ gpuInfo.device_count }}</span>
      </div>
      <div>
        <span class="opacity-60">{{ t('gpu.status') }}:</span>
        <span :class="gpuInfo.available ? 'text-green-500' : 'text-orange-500'">
          {{ gpuInfo.available ? t('gpu.ready') : t('gpu.notAvailable') }}
        </span>
      </div>
    </div>
    <div v-if="gpuInfo.error" class="mt-2 p-2 bg-orange-50 dark:bg-orange-900/20 rounded text-xs text-orange-600 dark:text-orange-400">
      <span class="font-medium">{{ t('gpu.note') }}:</span> {{ gpuInfo.error }}
    </div>
  </div>
</template>
