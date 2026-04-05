import { useState, useEffect, useContext } from 'react'
import { MdPeople, MdCampaign, MdSend, MdTrendingUp, MdAdd, MdRefresh } from 'react-icons/md'
import { StatCard } from '../components/Cards'
import { LineChart, BarChart } from '../components/Charts'
import { FormButton } from '../components/Forms'
import { getAnalyticsDashboard, getAnalyticsCharts, getAnalyticsTimeline } from '../services/api'
import { AuthContext } from '../contexts/AuthContext'
import theme from '../styles/theme'
import { useNavigate } from 'react-router-dom'

const REFRESH_INTERVAL = 5 * 60 * 1000 // 5 minutes

export default function Dashboard() {
  const { user } = useContext(AuthContext)
  const navigate = useNavigate()
  const [stats, setStats]       = useState(null)
  const [charts, setCharts]     = useState(null)
  const [timeline, setTimeline] = useState([])
  const [loading, setLoading]   = useState(true)
  const [lastRefresh, setLastRefresh] = useState(Date.now())

  const load = () => {
    setLoading(true)
    Promise.allSettled([
      getAnalyticsDashboard(),
      getAnalyticsCharts(),
      getAnalyticsTimeline({ limit: 8 }),
    ]).then(([s, c, t]) => {
      if (s.status === 'fulfilled') setStats(s.value)
      if (c.status === 'fulfilled') setCharts(c.value)
      if (t.status === 'fulfilled') setTimeline(Array.isArray(t.value) ? t.value : (t.value?.items ?? []))
      setLastRefresh(Date.now())
    }).finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
    const timer = setInterval(load, REFRESH_INTERVAL)
    return () => clearInterval(timer)
  }, [])

  const lineData = charts?.line ?? []
  const barData  = charts?.bar  ?? []

  return (
    <div className="fade-in" style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
        <div>
          <h2 style={{ fontSize: 18, fontWeight: 700, margin: 0 }}>Dashboard</h2>
          {user && <p style={{ fontSize: 12, color: theme.textMuted, margin: '4px 0 0' }}>Welcome back, {user.name ?? user.email}</p>}
        </div>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <button onClick={load} title="Refresh" style={{ background: 'none', border: 'none', color: theme.textMuted, cursor: 'pointer', display: 'flex', alignItems: 'center' }}>
            <MdRefresh size={18} />
          </button>
          <FormButton onClick={() => navigate('/campaigns')}>
            <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}><MdAdd size={14} /> New Campaign</span>
          </FormButton>
        </div>
      </div>

      {/* Stat Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 16 }}>
        <StatCard title="Total Campaigns"  value={loading ? '…' : (stats?.total_campaigns ?? 0)} icon={MdCampaign}  color={theme.primary}   change={3.4}  />
        <StatCard title="Active Campaigns" value={loading ? '…' : (stats?.active_campaigns ?? 0)} icon={MdTrendingUp} color={theme.secondary} change={1.2} />
        <StatCard title="Total Accounts"   value={loading ? '…' : (stats?.total_accounts ?? 0)}   icon={MdPeople}    color={theme.accent}    change={5.2}  />
        <StatCard title="Messages Sent"    value={loading ? '…' : (stats?.total_sent ?? 0).toLocaleString()} icon={MdSend} color={theme.success} change={12.1} />
        {user?.is_admin && (
          <StatCard title="Success Rate" value={loading ? '…' : `${stats?.success_rate ?? 0}%`} icon={MdTrendingUp} color={theme.primary} change={0.6} />
        )}
      </div>

      {/* Charts */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(380px, 1fr))', gap: 20 }}>
        <div style={{ background: theme.bgMedium, border: `1px solid ${theme.bgLight}`, borderRadius: 12, padding: 24 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16, color: theme.text }}>Campaign Performance</h3>
          {barData.length > 0
            ? <BarChart data={barData} xKey="name" bars={['sent', 'failed']} />
            : <p style={{ color: theme.textMuted, fontSize: 13 }}>No campaign data yet.</p>}
        </div>
        <div style={{ background: theme.bgMedium, border: `1px solid ${theme.bgLight}`, borderRadius: 12, padding: 24 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16, color: theme.text }}>Messages Trend</h3>
          {lineData.length > 0
            ? <LineChart data={lineData} xKey="name" lines={['sent', 'delivered']} />
            : <p style={{ color: theme.textMuted, fontSize: 13 }}>No trend data yet.</p>}
        </div>
      </div>

      {/* Recent Activity */}
      <div style={{ background: theme.bgMedium, border: `1px solid ${theme.bgLight}`, borderRadius: 12, padding: 24 }}>
        <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16, color: theme.text }}>Recent Activity</h3>
        {timeline.length === 0 ? (
          <p style={{ color: theme.textMuted, fontSize: 13 }}>No recent activity.</p>
        ) : (
          <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 10 }}>
            {timeline.map((item, i) => (
              <li key={item.id ?? i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '9px 14px', background: theme.bgLight, borderRadius: 8, borderLeft: `3px solid ${theme.primary}` }}>
                <span style={{ fontSize: 13, color: theme.text }}>
                  <strong style={{ textTransform: 'capitalize' }}>{item.action}</strong>
                  {item.resource_type ? ` — ${item.resource_type}` : ''}
                  {item.resource_id ? ` #${item.resource_id}` : ''}
                </span>
                <span style={{ fontSize: 11, color: theme.textMuted, whiteSpace: 'nowrap', marginLeft: 12 }}>
                  {item.created_at ? new Date(item.created_at).toLocaleString() : ''}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Quick Actions */}
      <div style={{ background: theme.bgMedium, border: `1px solid ${theme.bgLight}`, borderRadius: 12, padding: 24 }}>
        <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 14, color: theme.text }}>Quick Actions</h3>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          <FormButton onClick={() => navigate('/campaigns')}>+ New Campaign</FormButton>
          <FormButton onClick={() => navigate('/accounts')} variant="ghost">+ Add Account</FormButton>
          <FormButton onClick={() => navigate('/analytics')} variant="ghost">View Analytics</FormButton>
          {user?.is_admin && (
            <FormButton onClick={() => navigate('/admin')} variant="ghost">Admin Panel</FormButton>
          )}
        </div>
      </div>
    </div>
  )
}
