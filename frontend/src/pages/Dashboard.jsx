import { useState, useEffect } from 'react'
import { MdPeople, MdCampaign, MdSend, MdTrendingUp } from 'react-icons/md'
import { StatCard } from '../components/Cards'
import { LineChart } from '../components/Charts'
import { getAccounts, getCampaigns, getBroadcastStats } from '../services/api'
import theme from '../styles/theme'

const MOCK_MSG_DATA = [
  { name: 'Mon', messages: 1200, failed: 80 },
  { name: 'Tue', messages: 1900, failed: 120 },
  { name: 'Wed', messages: 1600, failed: 95 },
  { name: 'Thu', messages: 2400, failed: 60 },
  { name: 'Fri', messages: 2100, failed: 100 },
  { name: 'Sat', messages: 800,  failed: 30  },
  { name: 'Sun', messages: 600,  failed: 20  },
]

const MOCK_ACTIVITY = [
  { id: 1, text: 'Campaign "Summer Sale" started',       time: '2 min ago',  color: theme.success   },
  { id: 2, text: '250 messages sent to batch #12',       time: '5 min ago',  color: theme.primary   },
  { id: 3, text: 'Account @user123 connected',           time: '12 min ago', color: theme.secondary },
  { id: 4, text: 'Campaign "Promo Q4" completed',        time: '1 hr ago',   color: theme.accent    },
  { id: 5, text: '3 accounts flagged for rate limiting', time: '2 hr ago',   color: theme.error     },
]

export default function Dashboard() {
  const [stats, setStats] = useState({ accounts: 0, campaigns: 0, sent: 0, rate: 0 })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.allSettled([getAccounts(), getCampaigns(), getBroadcastStats()])
      .then(([acc, camp, bcast]) => {
        setStats({
          accounts:  acc.value?.length   ?? 24,
          campaigns: camp.value?.length  ?? 8,
          sent:      bcast.value?.total  ?? 48320,
          rate:      bcast.value?.rate   ?? 97.4,
        })
      })
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="fade-in" style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* Stat Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 16 }}>
        <StatCard title="Total Accounts"    value={loading ? '…' : stats.accounts}             icon={MdPeople}    color={theme.primary}   change={5.2}  />
        <StatCard title="Active Campaigns"  value={loading ? '…' : stats.campaigns}            icon={MdCampaign}  color={theme.secondary} change={-1.3} />
        <StatCard title="Messages Sent"     value={loading ? '…' : stats.sent.toLocaleString()} icon={MdSend}      color={theme.accent}    change={12.1} />
        <StatCard title="Success Rate"      value={loading ? '…' : `${stats.rate}%`}           icon={MdTrendingUp} color={theme.success}  change={0.6}  />
      </div>

      {/* Chart */}
      <div style={{ background: theme.bgMedium, border: `1px solid ${theme.bgLight}`, borderRadius: 12, padding: 24 }}>
        <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 16, color: theme.text }}>Messages Over Time</h3>
        <LineChart data={MOCK_MSG_DATA} xKey="name" lines={['messages', 'failed']} />
      </div>

      {/* Recent Activity */}
      <div style={{ background: theme.bgMedium, border: `1px solid ${theme.bgLight}`, borderRadius: 12, padding: 24 }}>
        <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 16, color: theme.text }}>Recent Activity</h3>
        <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 12 }}>
          {MOCK_ACTIVITY.map((item) => (
            <li key={item.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 14px', background: theme.bgLight, borderRadius: 8, borderLeft: `3px solid ${item.color}` }}>
              <span style={{ fontSize: 13, color: theme.text }}>{item.text}</span>
              <span style={{ fontSize: 11, color: theme.textMuted, whiteSpace: 'nowrap', marginLeft: 12 }}>{item.time}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
