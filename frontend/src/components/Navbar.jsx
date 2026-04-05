import { useState, useRef, useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { MdAccountCircle, MdNotifications, MdLightMode, MdDarkMode, MdLogout, MdPerson, MdSettings, MdAdminPanelSettings } from 'react-icons/md'
import theme from '../styles/theme'
import useRealtime from '../hooks/useRealtime'
import { logout } from '../services/api'
import { useTheme } from '../context/ThemeContext'
import { useToast } from '../context/ToastContext'

const PAGE_TITLES = {
  '/':           'Dashboard',
  '/campaigns':  'Campaigns',
  '/accounts':   'Accounts',
  '/analytics':  'Analytics',
  '/settings':   'Settings',
  '/profile':    'Profile',
  '/admin':      'Admin Panel',
}

function useClickOutside(ref, handler) {
  useEffect(() => {
    const listener = (e) => {
      if (!ref.current || ref.current.contains(e.target)) return
      handler()
    }
    document.addEventListener('mousedown', listener)
    return () => document.removeEventListener('mousedown', listener)
  }, [ref, handler])
}

export default function Navbar() {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const { connected } = useRealtime('ping')
  const { mode, toggleTheme } = useTheme()
  const { addToast } = useToast()

  const [userMenuOpen, setUserMenuOpen] = useState(false)
  const [notifOpen, setNotifOpen] = useState(false)
  const userMenuRef = useRef(null)
  const notifRef = useRef(null)

  useClickOutside(userMenuRef, () => setUserMenuOpen(false))
  useClickOutside(notifRef, () => setNotifOpen(false))

  const title = PAGE_TITLES[pathname] ?? 'TG PRO QUANTUM'

  const user = (() => {
    try { return JSON.parse(localStorage.getItem('user') ?? 'null') } catch { return null }
  })()
  const isAdmin = user?.role === 'admin' || user?.is_admin === true
  const userName = user?.name ?? user?.email ?? 'User'
  const userInitial = userName[0]?.toUpperCase() ?? '?'

  const notifCount = 3 // placeholder — replace with real data

  const handleLogout = async () => {
    try {
      await logout()
      addToast('Logged out successfully', 'success')
    } catch {
      // Silently ignore API errors — clear session and redirect anyway
    }
    localStorage.removeItem('auth_token')
    localStorage.removeItem('user')
    navigate('/login')
  }

  const styles = {
    navbar: {
      height: 60,
      background: theme.bgMedium,
      borderBottom: `1px solid ${theme.bgLight}`,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0 24px',
      flexShrink: 0,
      position: 'relative',
      zIndex: 100,
    },
    title: {
      fontSize: 18,
      fontWeight: 600,
      color: theme.text,
    },
    right: {
      display: 'flex',
      alignItems: 'center',
      gap: 8,
    },
    iconBtn: {
      width: 36,
      height: 36,
      borderRadius: 8,
      border: `1px solid ${theme.bgLight}`,
      background: 'transparent',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      cursor: 'pointer',
      color: theme.textMuted,
      position: 'relative',
      transition: 'border-color 0.2s, color 0.2s',
    },
    statusLabel: {
      fontSize: 12,
      color: theme.textMuted,
      display: 'flex',
      alignItems: 'center',
      gap: 6,
      marginRight: 8,
    },
    statusDot: (ok) => ({
      width: 8,
      height: 8,
      borderRadius: '50%',
      background: ok ? theme.success : theme.error,
      display: 'inline-block',
      animation: ok ? 'none' : 'pulse 1.5s infinite',
    }),
    badge: {
      position: 'absolute',
      top: 4,
      right: 4,
      width: 16,
      height: 16,
      borderRadius: '50%',
      background: theme.error,
      color: '#fff',
      fontSize: 9,
      fontWeight: 700,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      pointerEvents: 'none',
    },
    avatar: {
      width: 30,
      height: 30,
      borderRadius: '50%',
      background: `${theme.primary}22`,
      border: `1.5px solid ${theme.primary}`,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontSize: 13,
      fontWeight: 700,
      color: theme.primary,
    },
    userBtn: {
      display: 'flex',
      alignItems: 'center',
      gap: 8,
      padding: '6px 10px',
      borderRadius: 8,
      border: `1px solid ${theme.bgLight}`,
      background: 'transparent',
      cursor: 'pointer',
      color: theme.text,
      fontSize: 13,
      fontWeight: 500,
      transition: 'border-color 0.2s',
    },
    dropdown: {
      position: 'absolute',
      top: 'calc(100% + 8px)',
      right: 0,
      background: theme.bgMedium,
      border: `1px solid ${theme.bgLight}`,
      borderRadius: 10,
      minWidth: 200,
      boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
      overflow: 'hidden',
      animation: 'fadeIn 0.15s ease forwards',
      zIndex: 200,
    },
    dropdownItem: {
      display: 'flex',
      alignItems: 'center',
      gap: 10,
      padding: '11px 16px',
      fontSize: 13,
      color: theme.text,
      cursor: 'pointer',
      transition: 'background 0.15s',
      border: 'none',
      background: 'transparent',
      width: '100%',
      textAlign: 'left',
    },
    dropdownDivider: {
      height: 1,
      background: theme.bgLight,
      margin: '4px 0',
    },
  }

  return (
    <header style={styles.navbar}>
      <span style={styles.title}>{title}</span>

      <div style={styles.right}>
        {/* Connection status */}
        <span style={styles.statusLabel} className="hide-mobile">
          <span style={styles.statusDot(connected)} />
          {connected ? 'Connected' : 'Offline'}
        </span>

        {/* Theme toggle */}
        <button
          style={styles.iconBtn}
          onClick={toggleTheme}
          title={mode === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
          onMouseEnter={(e) => { e.currentTarget.style.borderColor = theme.primary; e.currentTarget.style.color = theme.primary }}
          onMouseLeave={(e) => { e.currentTarget.style.borderColor = theme.bgLight; e.currentTarget.style.color = theme.textMuted }}
        >
          {mode === 'dark' ? <MdLightMode size={18} /> : <MdDarkMode size={18} />}
        </button>

        {/* Notification bell */}
        <div ref={notifRef} style={{ position: 'relative' }}>
          <button
            style={styles.iconBtn}
            onClick={() => { setNotifOpen((p) => !p); setUserMenuOpen(false) }}
            title="Notifications"
            onMouseEnter={(e) => { e.currentTarget.style.borderColor = theme.primary; e.currentTarget.style.color = theme.primary }}
            onMouseLeave={(e) => { e.currentTarget.style.borderColor = theme.bgLight; e.currentTarget.style.color = theme.textMuted }}
          >
            <MdNotifications size={18} />
            {notifCount > 0 && <span style={styles.badge}>{notifCount}</span>}
          </button>
          {notifOpen && (
            <div style={{ ...styles.dropdown, minWidth: 280 }}>
              <div style={{ padding: '12px 16px', borderBottom: `1px solid ${theme.bgLight}` }}>
                <span style={{ fontSize: 13, fontWeight: 700, color: theme.text }}>Notifications</span>
              </div>
              {[
                { id: 1, text: 'Campaign "Summer Sale" completed', time: '2 min ago' },
                { id: 2, text: '250 messages sent to batch #12', time: '10 min ago' },
                { id: 3, text: 'Account rate limit warning', time: '1 hr ago' },
              ].map((n) => (
                <div key={n.id} style={{ padding: '11px 16px', borderBottom: `1px solid ${theme.bgLight}22`, cursor: 'pointer' }}
                  onMouseEnter={(e) => e.currentTarget.style.background = `${theme.bgLight}55`}
                  onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                >
                  <div style={{ fontSize: 13, color: theme.text, lineHeight: 1.4 }}>{n.text}</div>
                  <div style={{ fontSize: 11, color: theme.textMuted, marginTop: 3 }}>{n.time}</div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* User menu */}
        <div ref={userMenuRef} style={{ position: 'relative' }}>
          <button
            style={styles.userBtn}
            onClick={() => { setUserMenuOpen((p) => !p); setNotifOpen(false) }}
            onMouseEnter={(e) => e.currentTarget.style.borderColor = theme.primary}
            onMouseLeave={(e) => e.currentTarget.style.borderColor = theme.bgLight}
          >
            <div style={styles.avatar}>{userInitial}</div>
            <span className="hide-mobile">{userName}</span>
          </button>

          {userMenuOpen && (
            <div style={styles.dropdown}>
              {/* User info */}
              <div style={{ padding: '12px 16px', borderBottom: `1px solid ${theme.bgLight}` }}>
                <div style={{ fontSize: 13, fontWeight: 700, color: theme.text }}>{userName}</div>
                {user?.email && <div style={{ fontSize: 11, color: theme.textMuted, marginTop: 2 }}>{user.email}</div>}
                {user?.role && (
                  <span style={{ marginTop: 4, display: 'inline-block', fontSize: 10, background: `${theme.primary}22`, color: theme.primary, borderRadius: 4, padding: '1px 6px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: 0.5 }}>
                    {user.role}
                  </span>
                )}
              </div>

              {/* Menu items */}
              {[
                { label: 'Profile',  icon: MdPerson,              path: '/profile' },
                { label: 'Settings', icon: MdSettings,            path: '/settings' },
                ...(isAdmin ? [{ label: 'Admin Panel', icon: MdAdminPanelSettings, path: '/admin' }] : []),
              ].map(({ label, icon: Icon, path }) => (
                <button
                  key={path}
                  style={styles.dropdownItem}
                  onClick={() => { navigate(path); setUserMenuOpen(false) }}
                  onMouseEnter={(e) => e.currentTarget.style.background = `${theme.bgLight}88`}
                  onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                >
                  <Icon size={16} color={theme.textMuted} />
                  {label}
                </button>
              ))}

              <div style={styles.dropdownDivider} />

              <button
                style={{ ...styles.dropdownItem, color: theme.error }}
                onClick={handleLogout}
                onMouseEnter={(e) => e.currentTarget.style.background = `${theme.error}11`}
                onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
              >
                <MdLogout size={16} color={theme.error} />
                Logout
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
