import {
  defineConfig,
  presetUno,
  presetAttributify,
  presetIcons,
} from 'unocss'

export default defineConfig({
  presets: [
    presetUno(),
    presetAttributify(),
    presetIcons({
      scale: 1.2,
      warn: true,
    }),
  ],
  shortcuts: {
    'btn': 'px-4 py-2 rounded-lg font-medium transition-all duration-200 cursor-pointer',
    'btn-primary': 'btn bg-blue-500 text-white hover:bg-blue-600 active:bg-blue-700',
    'btn-secondary': 'btn bg-gray-200 text-gray-700 hover:bg-gray-300 active:bg-gray-400 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600',
    'card': 'bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-4',
    'page': 'min-h-screen bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-100',
  },
})
