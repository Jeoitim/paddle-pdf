import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

const DARK_KEY = 'paddlepdf-dark-mode'

export const useAppStore = defineStore('app', () => {
  const darkMode = ref(localStorage.getItem(DARK_KEY) === 'true')
  const sidebarCollapsed = ref(false)

  // Persist dark mode preference
  watch(darkMode, (v) => localStorage.setItem(DARK_KEY, String(v)))

  function toggleDark() {
    darkMode.value = !darkMode.value
  }

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  return { darkMode, sidebarCollapsed, toggleDark, toggleSidebar }
})
