<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { NSelect, NSpin } from 'naive-ui'
import { useSettingsStore } from '@/stores/settings'
import { useModels } from '@/composables/useModels'

const settings = useSettingsStore()
const { models, loading, fetchModels } = useModels()

onMounted(() => {
  if (models.value.length === 0) fetchModels()
})

const options = computed(() =>
  models.value.map((m) => ({
    label: `${m.name}${m.cached ? ' ✓' : ''}`,
    value: m.name,
  })),
)

function onChange(value: string) {
  settings.update({ model_name: value })
}
</script>

<template>
  <div class="flex items-center gap-2">
    <span class="text-sm font-medium whitespace-nowrap">Model:</span>
    <NSpin v-if="loading" :size="18" />
    <NSelect
      v-else
      :value="settings.options.model_name"
      :options="options"
      size="small"
      style="width: 220px"
      @update-value="onChange"
    />
  </div>
</template>
