import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import Navbar  from './components/Navbar'
import Dashboard  from './pages/Dashboard'
import Campaigns  from './pages/Campaigns'
import Accounts   from './pages/Accounts'
import Analytics  from './pages/Analytics'
import Settings   from './pages/Settings'
import theme from './styles/theme'
import './styles/globals.css'

export default function App() {
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
            </Routes>
          </main>
        </div>
      </div>
    </BrowserRouter>
  )
}
