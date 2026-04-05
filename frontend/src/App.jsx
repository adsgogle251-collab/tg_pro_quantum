import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import Navbar  from './components/Navbar'
import Dashboard  from './pages/Dashboard'
import Campaigns  from './pages/Campaigns'
import Accounts   from './pages/Accounts'
import Analytics  from './pages/Analytics'
import Settings   from './pages/Settings'
import Profile    from './pages/Profile'
import Admin      from './pages/Admin'
import { ThemeProvider, useTheme } from './context/ThemeContext'
import { ToastProvider } from './context/ToastContext'
import { I18nProvider } from './context/I18nContext'
import './styles/globals.css'

function AppShell() {
  const { theme } = useTheme()
  return (
    <BrowserRouter>
      <div style={{ display: 'flex', minHeight: '100vh', background: theme.bgDark }}>
        <Sidebar />
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <Navbar />
          <main style={{ flex: 1, overflowY: 'auto' }}>
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
