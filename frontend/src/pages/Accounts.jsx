import { useState, useEffect } from 'react'
import { MdAdd, MdDelete } from 'react-icons/md'
import { getAccounts } from '../services/api'
import { FormButton } from '../components/Forms'
import DataTable from '../components/DataTable'
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
  const color = STATUS_COLORS[status] ?? theme.textMuted
  return (
    <span style={{
      background: `${color}22`,
      color,
      border: `1px solid ${color}55`,
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

  const columns = [
    { key: 'id',       label: '#',        sortable: true,  width: 60 },
    { key: 'username', label: 'Username', sortable: true,
      render: (v) => <span style={{ fontWeight: 500, color: theme.primary }}>{v}</span> },
    { key: 'phone',    label: 'Phone',    sortable: true },
    { key: 'status',   label: 'Status',
      render: (v) => <StatusBadge status={v} /> },
    { key: 'sessions', label: 'Sessions', sortable: true, width: 100 },
    { key: 'id',       label: 'Actions',  width: 80,
      render: (id) => (
        <button
          onClick={(e) => { e.stopPropagation(); remove(id) }}
          style={{ background: 'none', border: 'none', color: theme.error, cursor: 'pointer', display: 'flex', alignItems: 'center' }}
          title="Remove"
        >
          <MdDelete size={18} />
        </button>
      ) },
  ]

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
        <DataTable columns={columns} rows={accounts} keyField="id" emptyMsg="No accounts found." pageSize={10} />
      </div>
    </div>
  )
}

