<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NIcon, NSpace, NSwitch, NSelect, NInputNumber, NCard } from 'naive-ui'
import { ArrowBackOutline } from '@vicons/ionicons5'
import { useSettingsStore } from '@/stores/settings'
import { useModels } from '@/composables/useModels'
import GpuStatus from '@/components/GpuStatus.vue'

const router = useRouter()
const settings = useSettingsStore()
const { models, fetchModels, downloadModel } = useModels()

onMounted(() => {
  fetchModels()
})

const modelOptions = models.value.map((m) => ({
  label: `${m.name} — ${m.desc}`,
  value: m.name,
  disabled: false,
}))

const dpiOptions = [
  { label: '150 (fast)', value: 150 },
  { label: '200', value: 200 },
  { label: '300 (default)', value: 300 },
  { label: '400 (dense text)', value: 400 },
  { label: '600 (highest)', value: 600 },
]
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
      <!-- Model -->
      <NCard title="OCR Model">
        <NSpace vertical :size="16">
          <div>
            <label class="block text-sm mb-1 opacity-70">Model</label>
            <NSelect
              :value="settings.options.model_name"
              :options="modelOptions"
              @update-value="(v: string) => settings.update({ model_name: v })"
            />
          </div>
          <div>
            <label class="block text-sm mb-1 opacity-70">DPI</label>
            <NSelect
              :value="settings.options.dpi"
              :options="dpiOptions"
              @update-value="(v: number) => settings.update({ dpi: v })"
            />
          </div>
        </NSpace>
      </NCard>

      <!-- Processing -->
      <NCard title="Processing">
        <NSpace vertical :size="16">
          <div class="flex items-center justify-between">
            <span>Use GPU</span>
            <NSwitch
              :value="settings.options.use_gpu"
              @update-value="(v: boolean) => settings.update({ use_gpu: v })"
            />
          </div>
          <div class="flex items-center justify-between">
            <span>Angle classification</span>
            <NSwitch
              :value="settings.options.angle_cls"
              @update-value="(v: boolean) => settings.update({ angle_cls: v })"
            />
          </div>
          <div class="flex items-center justify-between">
            <span>Show confidence scores</span>
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
