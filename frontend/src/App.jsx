import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import Navbar  from './components/Navbar'
import Dashboard  from './pages/Dashboard'
import Campaigns  from './pages/Campaigns'
import Accounts   from './pages/Accounts'
import Analytics  from './pages/Analytics'
import Settings   from './pages/Settings'
import Profile    from './pages/Profile'
import Admin      from './pages/Admin'
import Login      from './pages/Login'
import Register   from './pages/Register'
import NotFound   from './pages/NotFound'
import Forbidden  from './pages/Forbidden'
import { ProtectedRoute, AdminRoute } from './components/ProtectedRoute'
import ErrorBoundary from './components/ErrorBoundary'
import { ThemeProvider, useTheme } from './context/ThemeContext'
import { ToastProvider } from './context/ToastContext'
import { I18nProvider } from './context/I18nContext'
import { AuthProvider } from './contexts/AuthContext'
import './styles/globals.css'

function AppShell() {
  const { theme } = useTheme()
  return (
    <BrowserRouter>
      <Routes>
        {/* Public */}
        <Route path="/login"    element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/forbidden" element={<Forbidden />} />

        {/* Protected — wrap all dashboard routes */}
        <Route
          path="/*"
          element={
            <ProtectedRoute>
              <div style={{ display: 'flex', height: '100vh', background: theme.bgDark, overflow: 'hidden' }}>
                <Sidebar />
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
                  <Navbar />
                  <main style={{ flex: 1, overflowY: 'auto', overflowX: 'hidden' }}>
                    <ErrorBoundary>
                      <Routes>
                        <Route path="/"           element={<Dashboard />}  />
                        <Route path="/campaigns"  element={<Campaigns />}  />
                        <Route path="/accounts"   element={<Accounts />}   />
                        <Route path="/analytics"  element={<Analytics />}  />
                        <Route path="/settings"   element={<Settings />}   />
                        <Route path="/profile"    element={<Profile />}    />
                        <Route path="/admin"      element={<AdminRoute><Admin /></AdminRoute>} />
                        <Route path="*"           element={<NotFound />}   />
                      </Routes>
                    </ErrorBoundary>
                  </main>
                </div>
              </div>
            </ProtectedRoute>
          }
        />
      </Routes>
    </BrowserRouter>
  )
}

export default function App() {
  return (
    <I18nProvider>
      <ThemeProvider>
        <ToastProvider>
          <AuthProvider>
            <AppShell />
          </AuthProvider>
        </ToastProvider>
      </ThemeProvider>
    </I18nProvider>
  )
}
