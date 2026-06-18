<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  NButton, NIcon, NSpace, NSwitch, NSelect, NCard, NTag,
  NSpin, NTooltip, NList, NListItem, NThing,
} from 'naive-ui'
import {
  ArrowBackOutline,
  DownloadOutline,
  CheckmarkCircleOutline,
  CloudOfflineOutline,
  RefreshOutline,
} from '@vicons/ionicons5'
import { useSettingsStore } from '@/stores/settings'
import { useModels } from '@/composables/useModels'
import GpuStatus from '@/components/GpuStatus.vue'

const router = useRouter()
const settings = useSettingsStore()
const {
  models, loading, downloading,
  fetchModels, downloadModel, fetchGpuInfo,
} = useModels()

onMounted(() => {
  fetchModels()
  fetchGpuInfo()
})

const modelOptions = computed(() =>
  models.value.map((m) => ({
    label: `${m.name} — ${m.desc}${m.cached ? ' ✓' : ''}`,
    value: m.name,
  })),
)

const dpiOptions = [
  { label: '150 DPI (fast)', value: 150 },
  { label: '200 DPI', value: 200 },
  { label: '300 DPI (default)', value: 300 },
  { label: '400 DPI (dense text)', value: 400 },
  { label: '600 DPI (highest)', value: 600 },
]

const maxPagesOptions = [
  { label: 'All pages', value: 0 },
  { label: 'First 5 pages', value: 5 },
  { label: 'First 10 pages', value: 10 },
  { label: 'First 20 pages', value: 20 },
  { label: 'First 50 pages', value: 50 },
]

async function handleDownload(name: string) {
  await downloadModel(name)
}
</script>

<template>
  <div class="page">
    <header class="flex items-center gap-3 px-6 py-4 border-b border-gray-200 dark:border-gray-700">
      <NButton quaternary circle @click="router.push('/')">
        <template #icon>
          <NIcon :component="ArrowBackOutline" />
        </template>
      </NButton>
      <h1 class="text-lg font-bold">Settings</h1>
    </header>

    <main class="max-w-2xl mx-auto px-6 py-8 space-y-6">
      <!-- Model selection -->
      <NCard title="OCR Model">
        <NSpace vertical :size="16">
          <div>
            <label class="block text-sm mb-1 opacity-70">Model</label>
            <NSelect
              :value="settings.options.model_name"
              :options="modelOptions"
              :loading="loading"
              @update-value="(v: string) => settings.update({ model_name: v })"
            />
          </div>
        </NSpace>
      </NCard>

      <!-- Model management -->
      <NCard title="Model Management">
        <template #header-extra>
          <NButton quaternary size="small" @click="fetchModels">
            <template #icon><NIcon :component="RefreshOutline" /></template>
          </NButton>
        </template>

        <NSpin :show="loading">
          <NList hoverable clickable>
            <NListItem v-for="m in models" :key="m.name">
              <NThing>
                <template #header>
                  <div class="flex items-center gap-2">
                    <span class="font-medium">{{ m.name }}</span>
                    <NTag v-if="m.name === settings.options.model_name" type="primary" size="small">
                      Selected
                    </NTag>
                  </div>
                </template>
                <template #header-extra>
                  <NButton
                    v-if="m.cached"
                    size="small"
                    quaternary
                    disabled
                  >
                    <template #icon><NIcon :component="CheckmarkCircleOutline" /></template>
                    Cached
                  </NButton>
                  <NButton
                    v-else
                    size="small"
                    type="primary"
                    :loading="downloading === m.name"
                    @click.stop="handleDownload(m.name)"
                  >
                    <template #icon><NIcon :component="DownloadOutline" /></template>
                    Download
                  </NButton>
                </template>
                <template #description>
                  <p class="text-sm opacity-70">{{ m.desc }}</p>
                  <p v-if="m.note" class="text-xs opacity-50 mt-0.5">{{ m.note }}</p>
                </template>
              </NThing>
            </NListItem>
          </NList>
        </NSpin>
      </NCard>

      <!-- Processing options -->
      <NCard title="Processing Options">
        <NSpace vertical :size="16">
          <div>
            <label class="block text-sm mb-1 opacity-70">DPI (rendering resolution)</label>
            <NSelect
              :value="settings.options.dpi"
              :options="dpiOptions"
              @update-value="(v: number) => settings.update({ dpi: v })"
            />
          </div>
          <div>
            <label class="block text-sm mb-1 opacity-70">Max pages (0 = all)</label>
            <NSelect
              :value="settings.options.max_pages || 0"
              :options="maxPagesOptions"
              @update-value="(v: number) => settings.update({ max_pages: v || undefined })"
            />
          </div>
          <div class="flex items-center justify-between">
            <div>
              <span>Use GPU</span>
              <p class="text-xs opacity-50">Requires CUDA-enabled PaddlePaddle</p>
            </div>
            <NSwitch
              :value="settings.options.use_gpu"
              @update-value="(v: boolean) => settings.update({ use_gpu: v })"
            />
          </div>
          <div class="flex items-center justify-between">
            <div>
              <span>Angle classification</span>
              <p class="text-xs opacity-50">Detect rotated text (slower)</p>
            </div>
            <NSwitch
              :value="settings.options.angle_cls"
              @update-value="(v: boolean) => settings.update({ angle_cls: v })"
            />
          </div>
          <div class="flex items-center justify-between">
            <div>
              <span>Show confidence scores</span>
              <p class="text-xs opacity-50">Include in text output</p>
            </div>
            <NSwitch
              :value="settings.options.show_confidence"
              @update-value="(v: boolean) => settings.update({ show_confidence: v })"
            />
          </div>
        </NSpace>
      </NCard>

      <!-- GPU Status -->
      <NCard title="GPU Status">
        <GpuStatus :show-details="true" />
      </NCard>

      <!-- Actions -->
      <NSpace>
        <NButton @click="settings.reset()">Reset to defaults</NButton>
      </NSpace>
    </main>
  </div>
</template>
