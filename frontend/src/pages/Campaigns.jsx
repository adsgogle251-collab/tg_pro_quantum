import { useState, useEffect } from 'react'
import { getCampaigns } from '../services/api'
import { FormSelect, FormButton } from '../components/Forms'
import theme from '../styles/theme'

const STATUS_OPTIONS = [
  { value: 'all',      label: 'All Statuses'  },
  { value: 'active',   label: 'Active'        },
  { value: 'paused',   label: 'Paused'        },
  { value: 'completed',label: 'Completed'     },
  { value: 'failed',   label: 'Failed'        },
]

const MOCK = [
  { id: 1, name: 'Summer Sale',  status: 'active',    sent: 4200, failed: 130, total: 5000 },
  { id: 2, name: 'Promo Q4',     status: 'completed', sent: 8000, failed: 210, total: 8000 },
  { id: 3, name: 'Newsletter #5',status: 'paused',    sent: 1100, failed: 40,  total: 3000 },
  { id: 4, name: 'Re-engagement',status: 'active',    sent: 2600, failed: 90,  total: 4000 },
  { id: 5, name: 'Flash Deal',   status: 'failed',    sent: 300,  failed: 300, total: 1000 },
]

const STATUS_COLORS = {
  active:    theme.success,
  paused:    theme.accent,
  completed: theme.primary,
  failed:    theme.error,
}

function Badge({ status }) {
  return (
    <span style={{
      background: `${STATUS_COLORS[status] ?? theme.textMuted}22`,
      color: STATUS_COLORS[status] ?? theme.textMuted,
      border: `1px solid ${STATUS_COLORS[status] ?? theme.textMuted}55`,
      borderRadius: 20,
      padding: '3px 10px',
      fontSize: 11,
      fontWeight: 600,
      textTransform: 'capitalize',
    }}>
      {status}
    </span>
  )
}

function ProgressBar({ sent, total, failed }) {
  const pct = total > 0 ? Math.round((sent / total) * 100) : 0
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4, minWidth: 120 }}>
      <div style={{ background: theme.bgLight, borderRadius: 4, height: 6, overflow: 'hidden' }}>
        <div style={{ width: `${pct}%`, height: '100%', background: theme.primary, borderRadius: 4, transition: 'width 0.4s' }} />
      </div>
      <span style={{ fontSize: 11, color: theme.textMuted }}>{pct}%</span>
    </div>
  )
}

export default function Campaigns() {
  const [campaigns, setCampaigns] = useState(MOCK)
  const [filter, setFilter] = useState('all')

  useEffect(() => {
    getCampaigns().then(setCampaigns).catch(() => {})
  }, [])

  const visible = filter === 'all' ? campaigns : campaigns.filter((c) => c.status === filter)

  const th = { padding: '12px 16px', textAlign: 'left', fontSize: 12, color: theme.textMuted, fontWeight: 600, borderBottom: `1px solid ${theme.bgLight}` }
  const td = { padding: '14px 16px', fontSize: 13, color: theme.text, borderBottom: `1px solid ${theme.bgLight}22` }

  return (
    <div className="fade-in" style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 20 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
        <h2 style={{ fontSize: 16, fontWeight: 600 }}>Campaigns</h2>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <FormSelect
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            options={STATUS_OPTIONS}
            style={{ width: 160 }}
          />
          <FormButton>+ New Campaign</FormButton>
        </div>
      </div>

      <div style={{ background: theme.bgMedium, border: `1px solid ${theme.bgLight}`, borderRadius: 12, overflow: 'hidden' }}>
        <table>
          <thead>
            <tr>
              <th style={th}>#</th>
              <th style={th}>Name</th>
              <th style={th}>Status</th>
              <th style={th}>Sent</th>
              <th style={th}>Failed</th>
              <th style={th}>Progress</th>
              <th style={th}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((c) => (
              <tr key={c.id}>
                <td style={td}>{c.id}</td>
                <td style={{ ...td, fontWeight: 500 }}>{c.name}</td>
                <td style={td}><Badge status={c.status} /></td>
                <td style={td}>{c.sent.toLocaleString()}</td>
                <td style={{ ...td, color: theme.error }}>{c.failed.toLocaleString()}</td>
                <td style={td}><ProgressBar sent={c.sent} total={c.total} failed={c.failed} /></td>
                <td style={td}>
                  <FormButton variant="ghost" style={{ padding: '5px 12px', fontSize: 12 }}>View</FormButton>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {visible.length === 0 && (
          <p style={{ textAlign: 'center', padding: 40, color: theme.textMuted }}>No campaigns found.</p>
        )}
      </div>
    </div>
  )
}
