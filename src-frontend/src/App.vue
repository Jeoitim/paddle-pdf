<script setup lang="ts">
import { NConfigProvider, NMessageProvider, NDialogProvider, darkTheme } from 'naive-ui'
import { useAppStore } from '@/stores/app'
import { computed } from 'vue'

const appStore = useAppStore()
const theme = computed(() => appStore.darkMode ? darkTheme : null)
</script>

<template>
  <NConfigProvider :theme="theme">
    <NMessageProvider>
      <NDialogProvider>
        <div :class="['min-h-screen', appStore.darkMode ? 'dark' : '']">
          <RouterView />
        </div>
      </NDialogProvider>
    </NMessageProvider>
  </NConfigProvider>
</template>
