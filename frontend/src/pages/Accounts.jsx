import { useState, useEffect, useCallback } from 'react'
import { MdAdd, MdEdit, MdDelete, MdSearch, MdFileUpload, MdSecurity } from 'react-icons/md'
import { getAccounts, createAccount, deleteAccount } from '../services/api'
import { FormButton, FormInput, FormSelect } from '../components/Forms'
import DataTable from '../components/DataTable'
import ConfirmModal from '../components/ConfirmModal'
import ImportModal from '../components/ImportModal'
import OTPSetup from '../components/OTPSetup'
import { useToast } from '../context/ToastContext'
import { useRealTimeSync } from '../hooks/useRealTimeSync'
import theme from '../styles/theme'

const STATUS_COLORS = {
  active:      theme.success,
  inactive:    theme.textMuted,
  banned:      theme.error,
  flood_wait:  theme.accent,
  unverified:  theme.primary,
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

function AddAccountModal({ onClose, onSave }) {
  const [form, setForm] = useState({ name: '', phone: '', api_id: '', api_hash: '' })
  const [saving, setSaving] = useState(false)
  const [error, setError]   = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.phone.trim()) { setError('Phone is required'); return }
    setSaving(true)
    setError('')
    try {
      await onSave(form)
    } catch (err) {
      setError(err?.response?.data?.detail ?? 'Add failed')
    } finally {
      setSaving(false)
    }
  }

  const overlay = {
    position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.65)',
    display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
  }
  const modal = {
    background: theme.bgMedium, border: `1px solid ${theme.bgLight}`,
    borderRadius: 14, padding: 28, width: '100%', maxWidth: 460,
  }

  return (
    <div style={overlay} onClick={onClose}>
      <div style={modal} onClick={(e) => e.stopPropagation()}>
        <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 20 }}>Add Account</h3>
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <FormInput label="Display Name" value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} placeholder="Account name" />
          <FormInput label="Phone Number *" value={form.phone} onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))} placeholder="+1234567890" required />
          <FormInput label="API ID" type="number" value={form.api_id} onChange={(e) => setForm((f) => ({ ...f, api_id: e.target.value }))} placeholder="12345678" />
          <FormInput label="API Hash" value={form.api_hash} onChange={(e) => setForm((f) => ({ ...f, api_hash: e.target.value }))} placeholder="0123456789abcdef..." />
          {error && <p style={{ color: theme.error, fontSize: 13 }}>{error}</p>}
          <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', marginTop: 4 }}>
            <FormButton variant="ghost" type="button" onClick={onClose}>Cancel</FormButton>
            <FormButton type="submit" disabled={saving}>{saving ? 'Adding…' : 'Add Account'}</FormButton>
          </div>
        </form>
      </div>
    </div>
  )
}

const STATUS_FILTER_OPTIONS = [
  { value: 'all',        label: 'All Statuses' },
  { value: 'active',     label: 'Active'       },
  { value: 'inactive',   label: 'Inactive'     },
  { value: 'banned',     label: 'Banned'       },
  { value: 'flood_wait', label: 'Flood Wait'   },
]

export default function Accounts() {
  const { showToast } = useToast()
  const [accounts, setAccounts] = useState([])
  const [loading, setLoading]   = useState(true)
  const [search, setSearch]     = useState('')
  const [filter, setFilter]     = useState('all')
  const [showAdd, setShowAdd]   = useState(false)
  const [showImport, setShowImport] = useState(false)
  const [otpAccount, setOtpAccount] = useState(null)  // account to setup OTP for
  const [confirm, setConfirm]   = useState(null)

  // Get clientId from stored user info for real-time sync
  const clientId = (() => { try { return JSON.parse(localStorage.getItem('user') || '{}').id } catch { return null } })()

  const load = useCallback(() => {
    setLoading(true)
    getAccounts()
      .then((data) => setAccounts(Array.isArray(data) ? data : (data.items ?? [])))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { load() }, [load])

  // Real-time sync: auto-refresh on account events from any source (web/desktop)
  useRealTimeSync(clientId, (event) => {
    const accountEvents = [
      'account.imported', 'account.bulk_created', 'account.file_imported',
      'account.updated', 'account.deleted',
    ]
    if (accountEvents.includes(event.event)) {
      load()
      showToast(`Accounts updated (${event.event})`, 'info')
    }
  })

  const visible = accounts.filter((a) => {
    const matchStatus = filter === 'all' || a.status === filter
    const matchSearch = !search ||
      a.name?.toLowerCase().includes(search.toLowerCase()) ||
      a.phone?.includes(search)
    return matchStatus && matchSearch
  })

  const handleAdd = async (form) => {
    await createAccount(form)
    showToast('Account added', 'success')
    setShowAdd(false)
    load()
  }

  const handleDelete = async () => {
    if (!confirm) return
    try {
      await deleteAccount(confirm.id)
      showToast('Account removed', 'success')
      load()
    } catch {
      showToast('Delete failed', 'error')
    } finally {
      setConfirm(null)
    }
  }

  const columns = [
    { key: 'id',     label: '#',        sortable: true, width: 60 },
    { key: 'name',   label: 'Name',     sortable: true,
      render: (v) => <span style={{ fontWeight: 500 }}>{v ?? '—'}</span> },
    { key: 'phone',  label: 'Phone',    sortable: true },
    { key: 'status', label: 'Status',
      render: (v) => <StatusBadge status={v} /> },
    { key: 'health_score', label: 'Health', sortable: true,
      render: (v) => {
        const score = v ?? 0
        const color = score >= 80 ? theme.success : score >= 50 ? theme.accent : theme.error
        return <span style={{ color, fontWeight: 600 }}>{score}%</span>
      },
    },
    { key: 'id', label: 'Actions', width: 110,
      render: (_, row) => (
        <div style={{ display: 'flex', gap: 6 }}>
          <button onClick={() => setOtpAccount(row)} title="Setup 2FA"
            style={{ background: 'none', border: 'none', cursor: 'pointer',
              color: row.otp_enabled ? theme.success : theme.textMuted }}>
            <MdSecurity size={18} />
          </button>
          <button onClick={() => setConfirm(row)} title="Remove"
            style={{ background: 'none', border: 'none', color: theme.error, cursor: 'pointer' }}>
            <MdDelete size={18} />
          </button>
        </div>
      ),
    },
  ]

  return (
    <div className="fade-in" style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 20 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2 style={{ fontSize: 16, fontWeight: 600 }}>Accounts</h2>
        <div style={{ display: 'flex', gap: 10 }}>
          <FormButton variant="ghost" onClick={() => setShowImport(true)}>
            <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}><MdFileUpload size={16} /> Import</span>
          </FormButton>
          <FormButton onClick={() => setShowAdd(true)}>
            <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}><MdAdd size={16} /> Add Account</span>
          </FormButton>
        </div>
      </div>

      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
        <div style={{ position: 'relative', flex: 1, minWidth: 180 }}>
          <MdSearch size={16} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: theme.textMuted }} />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by name or phone…"
            style={{ width: '100%', paddingLeft: 32, padding: '8px 12px 8px 32px', background: theme.bgMedium, border: `1px solid ${theme.bgLight}`, borderRadius: 8, color: theme.text, fontSize: 13, outline: 'none' }}
          />
        </div>
        <FormSelect value={filter} onChange={(e) => setFilter(e.target.value)} options={STATUS_FILTER_OPTIONS} style={{ width: 150 }} />
      </div>

      <div style={{ background: theme.bgMedium, border: `1px solid ${theme.bgLight}`, borderRadius: 12, overflow: 'hidden' }}>
        <DataTable columns={columns} rows={visible} keyField="id" emptyMsg={loading ? 'Loading…' : 'No accounts found.'} pageSize={10} />
      </div>

      {showAdd && <AddAccountModal onClose={() => setShowAdd(false)} onSave={handleAdd} />}
      {showImport && (
        <ImportModal
          onClose={() => setShowImport(false)}
          onImported={() => { load(); showToast('Import complete', 'success') }}
        />
      )}
      {otpAccount && (
        <OTPSetup
          accountId={otpAccount.id}
          onClose={() => setOtpAccount(null)}
          onEnabled={() => { load(); showToast('2FA enabled', 'success') }}
        />
      )}
      {confirm && (
        <ConfirmModal
          isOpen={true}
          message={`Remove account "${confirm.name ?? confirm.phone}"? This cannot be undone.`}
          onConfirm={handleDelete}
          onCancel={() => setConfirm(null)}
        />
      )}
    </div>
  )
}

