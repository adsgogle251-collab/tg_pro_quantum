import { useLocation } from 'react-router-dom'
import { MdAccountCircle } from 'react-icons/md'
import theme from '../styles/theme'
import useRealtime from '../hooks/useRealtime'

const PAGE_TITLES = {
  '/':           'Dashboard',
  '/campaigns':  'Campaigns',
  '/accounts':   'Accounts',
  '/analytics':  'Analytics',
  '/settings':   'Settings',
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
  },
  title: {
    fontSize: 18,
    fontWeight: 600,
    color: theme.text,
  },
  right: {
    display: 'flex',
    alignItems: 'center',
    gap: 16,
  },
  statusDot: (connected) => ({
    width: 10,
    height: 10,
    borderRadius: '50%',
    background: connected ? theme.success : theme.error,
    display: 'inline-block',
    animation: connected ? 'none' : 'pulse 1.5s infinite',
  }),
  statusLabel: {
    fontSize: 12,
    color: theme.textMuted,
    display: 'flex',
    alignItems: 'center',
    gap: 6,
  },
  user: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    color: theme.text,
    fontSize: 14,
  },
}

export default function Navbar() {
  const { pathname } = useLocation()
  const { connected } = useRealtime('ping')
  const title = PAGE_TITLES[pathname] ?? 'TG PRO QUANTUM'

  return (
    <header style={styles.navbar}>
      <span style={styles.title}>{title}</span>
      <div style={styles.right}>
        <span style={styles.statusLabel}>
          <span style={styles.statusDot(connected)} />
          {connected ? 'Connected' : 'Offline'}
        </span>
        <div style={styles.user}>
          <MdAccountCircle size={22} color={theme.primary} />
          Admin
        </div>
      </div>
    </header>
  )
}
