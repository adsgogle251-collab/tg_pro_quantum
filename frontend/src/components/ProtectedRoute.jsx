import { Navigate } from 'react-router-dom'

/**
 * Require authentication.
 * If no token is present, redirect to /login.
 */
export function ProtectedRoute({ children }) {
  const token = localStorage.getItem('auth_token')
  if (!token) return <Navigate to="/login" replace />
  return children
}

/**
 * Require admin role.
 * If user is not admin, show 403 page.
 */
export function AdminRoute({ children }) {
  const token = localStorage.getItem('auth_token')
  if (!token) return <Navigate to="/login" replace />

  const user = (() => {
    try { return JSON.parse(localStorage.getItem('user') ?? 'null') } catch { return null }
  })()

  const isAdmin = user?.is_admin === true || user?.role === 'admin'
  if (!isAdmin) return <Navigate to="/forbidden" replace />

  return children
}

export default ProtectedRoute
