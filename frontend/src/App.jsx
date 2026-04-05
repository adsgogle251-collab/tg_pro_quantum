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
import { ThemeProvider, useTheme } from './context/ThemeContext'
import { ToastProvider } from './context/ToastContext'
import { I18nProvider } from './context/I18nContext'
import './styles/globals.css'

function RequireAuth({ children }) {
  const token = localStorage.getItem('auth_token')
  if (!token) return <Navigate to="/login" replace />
  return children
}

function AppShell() {
  const { theme } = useTheme()
  return (
    <BrowserRouter>
      <Routes>
        {/* Public */}
        <Route path="/login" element={<Login />} />

        {/* Protected — wrap all dashboard routes */}
        <Route
          path="/*"
          element={
            <RequireAuth>
              <div style={{ display: 'flex', height: '100vh', background: theme.bgDark, overflow: 'hidden' }}>
                <Sidebar />
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
                  <Navbar />
                  <main style={{ flex: 1, overflowY: 'auto', overflowX: 'hidden' }}>
                    <Routes>
                      <Route path="/"           element={<Dashboard />}  />
                      <Route path="/campaigns"  element={<Campaigns />}  />
                      <Route path="/accounts"   element={<Accounts />}   />
                      <Route path="/analytics"  element={<Analytics />}  />
                      <Route path="/settings"   element={<Settings />}   />
                      <Route path="/profile"    element={<Profile />}    />
                      <Route path="/admin"      element={<Admin />}      />
                    </Routes>
                  </main>
                </div>
              </div>
            </RequireAuth>
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
          <AppShell />
        </ToastProvider>
      </ThemeProvider>
    </I18nProvider>
  )
}
