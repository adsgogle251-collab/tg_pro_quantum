import { useState, useEffect } from 'react'
import { MdAdd, MdDelete } from 'react-icons/md'
import { getAccounts } from '../services/api'
import { FormButton } from '../components/Forms'
import theme from '../styles/theme'

const MOCK = [
  { id: 1, username: '@alice_bot',   phone: '+1 555 0101', status: 'active',   sessions: 3 },
  { id: 2, username: '@bob_sender',  phone: '+1 555 0102', status: 'active',   sessions: 1 },
  { id: 3, username: '@charlie_tg',  phone: '+1 555 0103', status: 'banned',   sessions: 0 },
  { id: 4, username: '@delta_proxy', phone: '+1 555 0104', status: 'inactive', sessions: 0 },
  { id: 5, username: '@echo_main',   phone: '+1 555 0105', status: 'active',   sessions: 5 },
]

const STATUS_COLORS = {
  active:   theme.success,
  inactive: theme.textMuted,
  banned:   theme.error,
}

function StatusBadge({ status }) {
  return (
    <span style={{
      background: `${STATUS_COLORS[status] ?? theme.textMuted}22`,
      color: STATUS_COLORS[status] ?? theme.textMuted,
      border: `1px solid ${STATUS_COLORS[status] ?? theme.textMuted}55`,
      borderRadius: 20, padding: '3px 10px',
      fontSize: 11, fontWeight: 600, textTransform: 'capitalize',
    }}>
      {status}
    </span>
  )
}

export default function Accounts() {
  const [accounts, setAccounts] = useState(MOCK)

  useEffect(() => {
    getAccounts().then(setAccounts).catch(() => {})
  }, [])

  const remove = (id) => setAccounts((prev) => prev.filter((a) => a.id !== id))

  const th = { padding: '12px 16px', textAlign: 'left', fontSize: 12, color: theme.textMuted, fontWeight: 600, borderBottom: `1px solid ${theme.bgLight}` }
  const td = { padding: '14px 16px', fontSize: 13, color: theme.text, borderBottom: `1px solid ${theme.bgLight}22` }

  return (
    <div className="fade-in" style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 20 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2 style={{ fontSize: 16, fontWeight: 600 }}>Accounts</h2>
        <FormButton>
          <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <MdAdd size={16} /> Add Account
          </span>
        </FormButton>
      </div>

      <div style={{ background: theme.bgMedium, border: `1px solid ${theme.bgLight}`, borderRadius: 12, overflow: 'hidden' }}>
        <table>
          <thead>
            <tr>
              <th style={th}>#</th>
              <th style={th}>Username</th>
              <th style={th}>Phone</th>
              <th style={th}>Status</th>
              <th style={th}>Sessions</th>
              <th style={th}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {accounts.map((a) => (
              <tr key={a.id}>
                <td style={td}>{a.id}</td>
                <td style={{ ...td, fontWeight: 500, color: theme.primary }}>{a.username}</td>
                <td style={td}>{a.phone}</td>
                <td style={td}><StatusBadge status={a.status} /></td>
                <td style={td}>{a.sessions}</td>
                <td style={td}>
                  <button
                    onClick={() => remove(a.id)}
                    style={{ background: 'none', border: 'none', color: theme.error, cursor: 'pointer', display: 'flex', alignItems: 'center' }}
                    title="Remove"
                  >
                    <MdDelete size={18} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {accounts.length === 0 && (
          <p style={{ textAlign: 'center', padding: 40, color: theme.textMuted }}>No accounts found.</p>
        )}
      </div>
    </div>
  )
}
