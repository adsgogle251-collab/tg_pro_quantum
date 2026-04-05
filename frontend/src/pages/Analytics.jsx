import { useState, useEffect, useCallback } from 'react'
import { MdDownload, MdRefresh } from 'react-icons/md'
import { LineChart, BarChart, PieChart } from '../components/Charts'
import { FormButton, FormSelect } from '../components/Forms'
import { StatCard } from '../components/Cards'
import { MdCampaign, MdPeople, MdSend, MdTrendingUp } from 'react-icons/md'
import { getAnalyticsDashboard, getAnalyticsCharts, getAnalyticsTimeline, getCampaignAnalytics } from '../services/api'
import theme from '../styles/theme'

const RANGE_OPTIONS = [
  { value: '7d',  label: 'Last 7 days'  },
  { value: '30d', label: 'Last 30 days' },
  { value: '90d', label: 'Last 90 days' },
]

function ChartCard({ title, children }) {
  return (
    <div style={{ background: theme.bgMedium, border: `1px solid ${theme.bgLight}`, borderRadius: 12, padding: 24 }}>
      <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16, color: theme.text }}>{title}</h3>
      {children}
    </div>
  )
}

export default function Analytics() {
  const [range, setRange]         = useState('30d')
  const [stats, setStats]         = useState(null)
  const [charts, setCharts]       = useState(null)
  const [timeline, setTimeline]   = useState([])
  const [loading, setLoading]     = useState(true)

  const load = useCallback(() => {
    setLoading(true)
    Promise.allSettled([
      getAnalyticsDashboard(),
      getAnalyticsCharts({ range }),
      getAnalyticsTimeline({ limit: 10 }),
    ]).then(([s, c, t]) => {
      if (s.status === 'fulfilled') setStats(s.value)
      if (c.status === 'fulfilled') setCharts(c.value)
      if (t.status === 'fulfilled') setTimeline(Array.isArray(t.value) ? t.value : (t.value?.items ?? []))
    }).finally(() => setLoading(false))
  }, [range])

  useEffect(() => { load() }, [load])

  const lineData = charts?.line ?? []
  const barData  = charts?.bar  ?? []
  const pieData  = charts?.pie  ?? [
    { name: 'Delivered', value: stats?.success_rate ?? 0 },
    { name: 'Failed',    value: stats ? 100 - stats.success_rate : 0 },
  ]

  return (
    <div className="fade-in" style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 20 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
        <h2 style={{ fontSize: 16, fontWeight: 600 }}>Analytics</h2>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <FormSelect value={range} onChange={(e) => setRange(e.target.value)} options={RANGE_OPTIONS} style={{ width: 150 }} />
          <button onClick={load} title="Refresh" style={{ background: 'none', border: 'none', color: theme.textMuted, cursor: 'pointer', display: 'flex', alignItems: 'center' }}>
            <MdRefresh size={18} />
          </button>
          <FormButton variant="ghost">
            <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}><MdDownload size={16} /> Export</span>
          </FormButton>
        </div>
      </div>

      {/* Stats Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 14 }}>
        <StatCard title="Total Campaigns"  value={loading ? '…' : (stats?.total_campaigns ?? 0)} icon={MdCampaign}  color={theme.primary}   change={3.2}  />
        <StatCard title="Active Campaigns" value={loading ? '…' : (stats?.active_campaigns ?? 0)} icon={MdTrendingUp} color={theme.secondary} change={1.5} />
        <StatCard title="Total Accounts"   value={loading ? '…' : (stats?.total_accounts ?? 0)}   icon={MdPeople}    color={theme.accent}    change={5.1}  />
        <StatCard title="Messages Sent"    value={loading ? '…' : (stats?.total_sent ?? 0).toLocaleString()} icon={MdSend} color={theme.success} change={10.8} />
        <StatCard title="Success Rate"     value={loading ? '…' : `${stats?.success_rate ?? 0}%`} icon={MdTrendingUp} color={theme.primary}  change={0.4}  />
      </div>

      <ChartCard title="Message Trend">
        {lineData.length > 0
          ? <LineChart data={lineData} xKey="name" lines={['sent', 'delivered']} />
          : <p style={{ color: theme.textMuted, fontSize: 13 }}>No trend data for selected range.</p>}
      </ChartCard>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(380px, 1fr))', gap: 20 }}>
        <ChartCard title="Campaigns Comparison">
          {barData.length > 0
            ? <BarChart data={barData} xKey="name" bars={['sent', 'failed']} />
            : <p style={{ color: theme.textMuted, fontSize: 13 }}>No campaign data yet.</p>}
        </ChartCard>
        <ChartCard title="Message Status Distribution">
          <PieChart data={pieData} />
        </ChartCard>
      </div>

      {/* Timeline */}
      {timeline.length > 0 && (
        <ChartCard title="Recent Events">
          <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 8 }}>
            {timeline.map((item, i) => (
              <li key={item.id ?? i} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', background: theme.bgLight, borderRadius: 7, borderLeft: `3px solid ${theme.primary}` }}>
                <span style={{ fontSize: 12, color: theme.text, textTransform: 'capitalize' }}>
                  {item.action}{item.resource_type ? ` — ${item.resource_type}` : ''}
                </span>
                <span style={{ fontSize: 11, color: theme.textMuted }}>
                  {item.created_at ? new Date(item.created_at).toLocaleString() : ''}
                </span>
              </li>
            ))}
          </ul>
        </ChartCard>
      )}
    </div>
  )
}
