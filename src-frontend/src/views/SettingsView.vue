<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  NButton, NIcon, NSpace, NSwitch, NSelect, NCard, NTag,
  NSpin, NList, NListItem, NThing,
} from 'naive-ui'
import {
  ArrowBackOutline,
  DownloadOutline,
  CheckmarkCircleOutline,
  RefreshOutline,
} from '@vicons/ionicons5'
import { useI18n } from 'vue-i18n'
import { useSettingsStore } from '@/stores/settings'
import { useModels } from '@/composables/useModels'
import GpuStatus from '@/components/GpuStatus.vue'

const { t } = useI18n()
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
    label: `${t('model.' + m.name, m.desc)}${m.cached ? ' ✓' : ''}`,
    value: m.name,
  })),
)

const dpiOptions = [
  { label: '150 DPI', value: 150 },
  { label: '200 DPI', value: 200 },
  { label: '300 DPI (default)', value: 300 },
  { label: '400 DPI', value: 400 },
  { label: '600 DPI', value: 600 },
]

const maxPagesOptions = computed(() => [
  { label: t('settings.allPages'), value: 0 },
  { label: t('settings.firstNPages', { n: 5 }), value: 5 },
  { label: t('settings.firstNPages', { n: 10 }), value: 10 },
  { label: t('settings.firstNPages', { n: 20 }), value: 20 },
  { label: t('settings.firstNPages', { n: 50 }), value: 50 },
])

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
      <h1 class="text-lg font-bold">{{ t('settings.title') }}</h1>
    </header>

    <main class="max-w-2xl mx-auto px-6 py-8 space-y-6">
      <!-- Model selection -->
      <NCard :title="t('settings.modelSection')">
        <NSpace vertical :size="16">
          <div>
            <label class="block text-sm mb-1 opacity-70">{{ t('settings.modelLabel') }}</label>
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
      <NCard :title="t('settings.modelMgmt')">
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
                    <span class="font-medium">{{ t('model.' + m.name, m.desc) }}</span>
                    <NTag v-if="m.name === settings.options.model_name" type="primary" size="small">
                      {{ t('settings.selected') }}
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
                    {{ t('settings.cached') }}
                  </NButton>
                  <NButton
                    v-else
                    size="small"
                    type="primary"
                    :loading="downloading === m.name"
                    @click.stop="handleDownload(m.name)"
                  >
                    <template #icon><NIcon :component="DownloadOutline" /></template>
                    {{ t('settings.download') }}
                  </NButton>
                </template>
                <template #description>
                  <p class="text-sm opacity-70">{{ t('model.' + m.name, m.desc) }}</p>
                  <p v-if="m.note" class="text-xs opacity-50 mt-0.5">{{ m.note }}</p>
                </template>
              </NThing>
            </NListItem>
          </NList>
        </NSpin>
      </NCard>

      <!-- Processing options -->
      <NCard :title="t('settings.options')">
        <NSpace vertical :size="16">
          <div>
            <label class="block text-sm mb-1 opacity-70">{{ t('settings.dpiLabel') }}</label>
            <NSelect
              :value="settings.options.dpi"
              :options="dpiOptions"
              @update-value="(v: number) => settings.update({ dpi: v })"
            />
          </div>
          <div>
            <label class="block text-sm mb-1 opacity-70">{{ t('settings.maxPagesLabel') }}</label>
            <NSelect
              :value="settings.options.max_pages || 0"
              :options="maxPagesOptions"
              @update-value="(v: number) => settings.update({ max_pages: v || undefined })"
            />
          </div>
          <div class="flex items-center justify-between">
            <div>
              <span>{{ t('settings.useGpu') }}</span>
              <p class="text-xs opacity-50">{{ t('settings.useGpuHint') }}</p>
            </div>
            <NSwitch
              :value="settings.options.use_gpu"
              @update-value="(v: boolean) => settings.update({ use_gpu: v })"
            />
          </div>
          <div class="flex items-center justify-between">
            <div>
              <span>{{ t('settings.angleCls') }}</span>
              <p class="text-xs opacity-50">{{ t('settings.angleClsHint') }}</p>
            </div>
            <NSwitch
              :value="settings.options.angle_cls"
              @update-value="(v: boolean) => settings.update({ angle_cls: v })"
            />
          </div>
          <div class="flex items-center justify-between">
            <div>
              <span>{{ t('settings.showConf') }}</span>
              <p class="text-xs opacity-50">{{ t('settings.showConfHint') }}</p>
            </div>
            <NSwitch
              :value="settings.options.show_confidence"
              @update-value="(v: boolean) => settings.update({ show_confidence: v })"
            />
          </div>
        </NSpace>
      </NCard>

      <!-- GPU Status -->
      <NCard :title="t('settings.gpuStatus')">
        <GpuStatus :show-details="true" />
      </NCard>

      <!-- Actions -->
      <NSpace>
        <NButton @click="settings.reset()">{{ t('settings.reset') }}</NButton>
      </NSpace>
    </main>
  </div>
</template>
