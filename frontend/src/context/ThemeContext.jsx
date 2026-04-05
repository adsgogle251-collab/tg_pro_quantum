import { createContext, useContext, useState, useCallback, useEffect } from 'react'

export const darkTheme = {
  primary: '#00D9FF',
  secondary: '#7B2CBF',
  accent: '#FF6B35',
  success: '#00FF41',
  warning: '#FFB800',
  error: '#FF006E',
  bgDark: '#0A0E27',
  bgMedium: '#1A1F3A',
  bgLight: '#252D4A',
  text: '#E0E0FF',
  textMuted: '#9099B7',
}

export const lightTheme = {
  primary: '#0099BB',
  secondary: '#6020AA',
  accent: '#E05520',
  success: '#008A24',
  warning: '#CC9200',
  error: '#CC004A',
  bgDark: '#F0F2FA',
  bgMedium: '#FFFFFF',
  bgLight: '#E4E8F5',
  text: '#1A1D2E',
  textMuted: '#5A6080',
}

const ThemeContext = createContext(null)

export function ThemeProvider({ children }) {
  const [mode, setMode] = useState(
    () => localStorage.getItem('theme') ?? 'dark'
  )

  const theme = mode === 'dark' ? darkTheme : lightTheme

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', mode)
    localStorage.setItem('theme', mode)
  }, [mode])

  const toggleTheme = useCallback(() => {
    setMode((prev) => (prev === 'dark' ? 'light' : 'dark'))
  }, [])

  return (
    <ThemeContext.Provider value={{ theme, mode, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  const ctx = useContext(ThemeContext)
  if (!ctx) throw new Error('useTheme must be used within ThemeProvider')
  return ctx
}

export default ThemeContext
