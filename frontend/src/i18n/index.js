import en from './en'
import id from './id'

const translations = { en, id }

export const SUPPORTED_LOCALES = ['en', 'id']
export const DEFAULT_LOCALE = 'en'

export function getTranslations(locale) {
  return translations[locale] ?? translations[DEFAULT_LOCALE]
}

export function createTranslator(locale) {
  const dict = getTranslations(locale)
  return (key) => dict[key] ?? key
}

export { en, id }
