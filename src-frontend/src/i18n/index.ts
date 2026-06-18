import { createI18n } from 'vue-i18n'
import en from './en'
import zh from './zh'

const LOCALE_KEY = 'paddlepdf-locale'

type Locale = 'en' | 'zh'

function getDefaultLocale(): Locale {
  const saved = localStorage.getItem(LOCALE_KEY)
  if (saved === 'en' || saved === 'zh') return saved
  const lang = navigator.language.toLowerCase()
  if (lang.startsWith('zh')) return 'zh'
  return 'en'
}

const i18n = createI18n({
  legacy: false,
  locale: getDefaultLocale(),
  fallbackLocale: 'en',
  messages: { en, zh },
})

export default i18n

export function setLocale(locale: Locale) {
  i18n.global.locale.value = locale
  localStorage.setItem(LOCALE_KEY, locale)
  document.documentElement.lang = locale
}
