import { createContext, useContext, useState, useCallback } from 'react'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try { return JSON.parse(localStorage.getItem('user') ?? 'null') } catch { return null }
  })

  const saveSession = useCallback((token, userData) => {
    localStorage.setItem('auth_token', token)
    if (userData) {
      localStorage.setItem('user', JSON.stringify(userData))
      setUser(userData)
    }
  }, [])

  const clearSession = useCallback(() => {
    localStorage.removeItem('auth_token')
    localStorage.removeItem('user')
    setUser(null)
  }, [])

  const isAdmin = user?.is_admin === true || user?.role === 'admin'
  const isAuthenticated = Boolean(localStorage.getItem('auth_token'))

  return (
    <AuthContext.Provider value={{ user, isAdmin, isAuthenticated, saveSession, clearSession }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}

export default AuthContext
