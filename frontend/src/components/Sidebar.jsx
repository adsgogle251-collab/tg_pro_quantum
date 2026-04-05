import { NavLink } from 'react-router-dom'
import {
  MdDashboard,
  MdCampaign,
  MdPeople,
  MdBarChart,
  MdSettings,
} from 'react-icons/md'
import theme from '../styles/theme'

const navItems = [
  { to: '/',           label: 'Dashboard',  Icon: MdDashboard },
  { to: '/campaigns',  label: 'Campaigns',  Icon: MdCampaign  },
  { to: '/accounts',   label: 'Accounts',   Icon: MdPeople    },
  { to: '/analytics',  label: 'Analytics',  Icon: MdBarChart  },
  { to: '/settings',   label: 'Settings',   Icon: MdSettings  },
]

const styles = {
  sidebar: {
    width: 220,
    height: '100%',
    background: theme.bgMedium,
    borderRight: `1px solid ${theme.bgLight}`,
    display: 'flex',
    flexDirection: 'column',
    padding: '24px 0',
    flexShrink: 0,
    overflowY: 'auto',
  },
  logo: {
    padding: '0 20px 28px',
    fontSize: 18,
    fontWeight: 700,
    letterSpacing: 1,
    color: theme.primary,
    borderBottom: `1px solid ${theme.bgLight}`,
    marginBottom: 12,
  },
  logoSub: {
    fontSize: 10,
    color: theme.textMuted,
    letterSpacing: 2,
    marginTop: 2,
  },
  link: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    padding: '12px 20px',
    color: theme.textMuted,
    fontSize: 14,
    fontWeight: 500,
    transition: 'all 0.2s',
    borderLeft: '3px solid transparent',
  },
  activeLink: {
    color: theme.primary,
    background: `${theme.primary}12`,
    borderLeft: `3px solid ${theme.primary}`,
  },
}

export default function Sidebar() {
  return (
    <aside style={styles.sidebar}>
      <div style={styles.logo}>
        ⚡ TG PRO
        <div style={styles.logoSub}>QUANTUM</div>
      </div>
      <nav>
        {navItems.map(({ to, label, Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            style={({ isActive }) => ({
              ...styles.link,
              ...(isActive ? styles.activeLink : {}),
            })}
          >
            <Icon size={18} />
            {label}
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}
