import { createContext, useContext, useState, useCallback } from 'react'
import { createTranslator, DEFAULT_LOCALE, SUPPORTED_LOCALES } from '../i18n'

const I18nContext = createContext(null)

export function I18nProvider({ children }) {
  const [locale, setLocaleState] = useState(
    () => localStorage.getItem('locale') ?? DEFAULT_LOCALE
  )

  const setLocale = useCallback((lang) => {
    if (SUPPORTED_LOCALES.includes(lang)) {
      localStorage.setItem('locale', lang)
      setLocaleState(lang)
    }
  }, [])

  const t = useCallback(createTranslator(locale), [locale])

  return (
    <I18nContext.Provider value={{ t, locale, setLocale }}>
      {children}
    </I18nContext.Provider>
  )
}

export function useI18n() {
  const ctx = useContext(I18nContext)
  if (!ctx) throw new Error('useI18n must be used within I18nProvider')
  return ctx
}

export default I18nContext
