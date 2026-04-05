import { useState, useEffect, useCallback } from 'react'
import {
  getLicenses,
  createLicense,
  updateLicense,
  getClients,
  updateClient,
} from '../services/api'
import { useToast } from '../context/ToastContext'
import useForm from '../hooks/useForm'
import Pagination from '../components/Pagination'
import ConfirmModal from '../components/ConfirmModal'
import { Spinner } from '../components/Loading'
import theme from '../styles/theme'

// ─── Shared helpers ──────────────────────────────────────────────────────────
const card = {
  background: theme.bgMedium,
  border: `1px solid ${theme.bgLight}`,
  borderRadius: 12,
  padding: 24,
}

const sectionTitle = {
  fontSize: 16,
  fontWeight: 700,
  color: theme.text,
  marginBottom: 20,
  paddingBottom: 12,
  borderBottom: `1px solid ${theme.bgLight}`,
}

const thStyle = {
  textAlign: 'left',
  padding: '10px 14px',
  fontSize: 12,
  fontWeight: 600,
  color: theme.textMuted,
  textTransform: 'uppercase',
  letterSpacing: 0.5,
  borderBottom: `1px solid ${theme.bgLight}`,
}

const tdStyle = {
  padding: '12px 14px',
  fontSize: 13,
  color: theme.text,
  borderBottom: `1px solid ${theme.bgLight}22`,
}

function StatusBadge({ status }) {
  const colors = {
    active:    { bg: `${theme.success}22`, text: theme.success },
    inactive:  { bg: `${theme.textMuted}22`, text: theme.textMuted },
    revoked:   { bg: `${theme.error}22`, text: theme.error },
    suspended: { bg: `${theme.error}22`, text: theme.error },
    trial:     { bg: `${theme.warning}22`, text: theme.warning },
  }
  const c = colors[status?.toLowerCase()] ?? { bg: `${theme.textMuted}22`, text: theme.textMuted }
  return (
    <span style={{ ...c, borderRadius: 4, padding: '2px 10px', fontSize: 11, fontWeight: 600, textTransform: 'capitalize' }}>
      {status ?? '—'}
    </span>
  )
}

function ActionBtn({ children, variant = 'ghost', onClick, disabled }) {
  const variantStyles = {
    ghost:   { border: `1px solid ${theme.bgLight}`, color: theme.primary },
    danger:  { border: `1px solid ${theme.error}44`, color: theme.error },
    success: { border: `1px solid ${theme.success}44`, color: theme.success },
  }
  const s = variantStyles[variant] ?? variantStyles.ghost
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        background: 'transparent',
        ...s,
        borderRadius: 6,
        padding: '5px 12px',
        fontSize: 12,
        fontWeight: 600,
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.5 : 1,
        transition: 'opacity 0.15s',
      }}
    >
      {children}
    </button>
  )
}

function Input({ label, error, ...props }) {
  const [focused, setFocused] = useState(false)
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
      {label && <label style={{ fontSize: 12, color: theme.textMuted, fontWeight: 500 }}>{label}</label>}
      <input
        {...props}
        style={{
          background: theme.bgLight,
          border: `1px solid ${focused ? theme.primary : (error ? theme.error : theme.bgLight)}`,
          borderRadius: 7,
          color: theme.text,
          fontSize: 13,
          padding: '8px 12px',
          outline: 'none',
          width: '100%',
          ...(props.style ?? {}),
        }}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
      />
      {error && <span style={{ fontSize: 11, color: theme.error }}>{error}</span>}
    </div>
  )
}

function Select({ label, children, ...props }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
      {label && <label style={{ fontSize: 12, color: theme.textMuted, fontWeight: 500 }}>{label}</label>}
      <select
        {...props}
        style={{
          background: theme.bgLight,
          border: `1px solid ${theme.bgLight}`,
          borderRadius: 7,
          color: theme.text,
          fontSize: 13,
          padding: '8px 12px',
          outline: 'none',
          cursor: 'pointer',
          ...(props.style ?? {}),
        }}
      >
        {children}
      </select>
    </div>
  )
}

// ─── License Management ──────────────────────────────────────────────────────
function LicenseManagement() {
  const { addToast } = useToast()
  const [licenses, setLicenses] = useState([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [total, setTotal] = useState(0)
  const [showCreate, setShowCreate] = useState(false)
  const [revokeTarget, setRevokeTarget] = useState(null)
  const [creating, setCreating] = useState(false)
  const [search, setSearch] = useState('')

  const { values, errors, handleChange, handleSubmit, reset } = useForm(
    { plan: 'starter', duration_days: '30', max_accounts: '10', assigned_email: '' },
    { plan: ['required'], duration_days: ['required'] }
  )

  const fetchLicenses = useCallback(async () => {
    setLoading(true)
    try {
      const data = await getLicenses({ page, page_size: pageSize, search })
      setLicenses(data.items ?? data)
      setTotal(data.total ?? data.length)
    } catch {
      addToast('Failed to load licenses', 'error')
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, search])

  useEffect(() => { fetchLicenses() }, [fetchLicenses])

  const handleCreate = handleSubmit(async (vals) => {
    setCreating(true)
    try {
      await createLicense({ ...vals, duration_days: Number(vals.duration_days), max_accounts: Number(vals.max_accounts) })
      addToast('License created successfully', 'success')
      setShowCreate(false)
      reset()
      fetchLicenses()
    } catch (err) {
      addToast(err?.response?.data?.detail ?? 'Failed to create license', 'error')
    } finally {
      setCreating(false)
    }
  })

  const handleRevoke = async () => {
    try {
      await updateLicense(revokeTarget, { status: 'revoked' })
      addToast('License revoked', 'warning')
      setRevokeTarget(null)
      fetchLicenses()
    } catch {
      addToast('Failed to revoke license', 'error')
    }
  }

  return (
    <section style={card}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h2 style={{ ...sectionTitle, marginBottom: 0, paddingBottom: 0, borderBottom: 'none' }}>License Management</h2>
        <button
          onClick={() => setShowCreate(!showCreate)}
          style={{ background: theme.primary, color: theme.bgDark, border: 'none', borderRadius: 8, padding: '8px 18px', fontSize: 13, fontWeight: 700, cursor: 'pointer' }}
        >
          + Create License
        </button>
      </div>

      {/* Create Form */}
      {showCreate && (
        <div style={{ background: theme.bgLight, borderRadius: 10, padding: 20, marginBottom: 20 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, color: theme.text, marginBottom: 16 }}>New License</h3>
          <form onSubmit={handleCreate}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 14, marginBottom: 16 }}>
              <Select label="Plan" name="plan" value={values.plan} onChange={handleChange}>
                <option value="starter">Starter</option>
                <option value="pro">Pro</option>
                <option value="enterprise">Enterprise</option>
              </Select>
              <Input label="Duration (days)" name="duration_days" type="number" value={values.duration_days} onChange={handleChange} error={errors.duration_days} min="1" />
              <Input label="Max Accounts" name="max_accounts" type="number" value={values.max_accounts} onChange={handleChange} min="1" />
              <Input label="Assign to email (optional)" name="assigned_email" type="email" value={values.assigned_email} onChange={handleChange} />
            </div>
            <div style={{ display: 'flex', gap: 10 }}>
              <button type="submit" disabled={creating} style={{ background: creating ? `${theme.primary}55` : theme.primary, color: theme.bgDark, border: 'none', borderRadius: 7, padding: '8px 20px', fontSize: 13, fontWeight: 700, cursor: creating ? 'not-allowed' : 'pointer', display: 'flex', alignItems: 'center', gap: 8 }}>
                {creating && <Spinner size={13} color={theme.bgDark} />}
                Create
              </button>
              <button type="button" onClick={() => setShowCreate(false)} style={{ background: 'transparent', border: `1px solid ${theme.bgLight}`, color: theme.textMuted, borderRadius: 7, padding: '8px 16px', fontSize: 13, cursor: 'pointer' }}>Cancel</button>
            </div>
          </form>
        </div>
      )}

      {/* Search */}
      <div style={{ marginBottom: 14 }}>
        <input
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1) }}
          placeholder="Search licenses…"
          style={{ background: theme.bgLight, border: `1px solid ${theme.bgLight}`, borderRadius: 8, color: theme.text, fontSize: 13, padding: '8px 14px', outline: 'none', width: 260 }}
        />
      </div>

      {/* Table */}
      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 32 }}><Spinner /></div>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ borderCollapse: 'collapse', width: '100%' }}>
            <thead>
              <tr>
                {['License Key', 'Plan', 'Status', 'Assigned To', 'Expires At', 'Actions'].map((h) => (
                  <th key={h} style={thStyle}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {licenses.length === 0 ? (
                <tr>
                  <td colSpan={6} style={{ ...tdStyle, textAlign: 'center', color: theme.textMuted, padding: '28px 0' }}>No licenses found</td>
                </tr>
              ) : licenses.map((lic) => (
                <tr key={lic.id} style={{ transition: 'background 0.15s' }}
                  onMouseEnter={(e) => e.currentTarget.style.background = `${theme.bgLight}44`}
                  onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                >
                  <td style={tdStyle}>
                    <span style={{ fontFamily: 'monospace', fontSize: 12 }}>{lic.key?.slice(0, 24)}…</span>
                  </td>
                  <td style={tdStyle}><span style={{ textTransform: 'capitalize' }}>{lic.plan}</span></td>
                  <td style={tdStyle}><StatusBadge status={lic.status} /></td>
                  <td style={tdStyle}>{lic.assigned_to ?? '—'}</td>
                  <td style={tdStyle}>{lic.expires_at ? new Date(lic.expires_at).toLocaleDateString() : '—'}</td>
                  <td style={tdStyle}>
                    <div style={{ display: 'flex', gap: 8 }}>
                      {lic.status !== 'revoked' && (
                        <ActionBtn variant="danger" onClick={() => setRevokeTarget(lic.id)}>Revoke</ActionBtn>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Pagination
        currentPage={page}
        totalPages={Math.ceil(total / pageSize)}
        onPageChange={setPage}
        pageSize={pageSize}
        onPageSizeChange={(s) => { setPageSize(s); setPage(1) }}
        totalItems={total}
      />

      <ConfirmModal
        isOpen={revokeTarget !== null}
        title="Revoke License"
        message="This license will be permanently revoked. The assigned user will lose access immediately."
        confirmText="Revoke License"
        requireConfirmCheckbox
        onConfirm={handleRevoke}
        onCancel={() => setRevokeTarget(null)}
      />
    </section>
  )
}

// ─── Client Management ───────────────────────────────────────────────────────
function ClientManagement() {
  const { addToast } = useToast()
  const [clients, setClients] = useState([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [total, setTotal] = useState(0)
  const [editTarget, setEditTarget] = useState(null)
  const [suspendTarget, setSuspendTarget] = useState(null)
  const [search, setSearch] = useState('')

  const fetchClients = useCallback(async () => {
    setLoading(true)
    try {
      const data = await getClients({ page, page_size: pageSize, search })
      setClients(data.items ?? data)
      setTotal(data.total ?? data.length)
    } catch {
      addToast('Failed to load clients', 'error')
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, search])

  useEffect(() => { fetchClients() }, [fetchClients])

  const handleUpdateClient = async (id, payload) => {
    try {
      const updated = await updateClient(id, payload)
      setClients((prev) => prev.map((c) => (c.id === id ? { ...c, ...updated } : c)))
      addToast('Client updated', 'success')
      setEditTarget(null)
    } catch {
      addToast('Failed to update client', 'error')
    }
  }

  const handleSuspend = async () => {
    const c = clients.find((cl) => cl.id === suspendTarget)
    const newStatus = c?.status === 'suspended' ? 'active' : 'suspended'
    await handleUpdateClient(suspendTarget, { status: newStatus })
    setSuspendTarget(null)
  }

  return (
    <section style={card}>
      <h2 style={sectionTitle}>Client Management</h2>

      {/* Search */}
      <div style={{ marginBottom: 14 }}>
        <input
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1) }}
          placeholder="Search clients…"
          style={{ background: theme.bgLight, border: `1px solid ${theme.bgLight}`, borderRadius: 8, color: theme.text, fontSize: 13, padding: '8px 14px', outline: 'none', width: 260 }}
        />
      </div>

      {/* Table */}
      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 32 }}><Spinner /></div>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ borderCollapse: 'collapse', width: '100%' }}>
            <thead>
              <tr>
                {['Name', 'Email', 'Plan', 'Status', 'Joined', 'Actions'].map((h) => (
                  <th key={h} style={thStyle}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {clients.length === 0 ? (
                <tr>
                  <td colSpan={6} style={{ ...tdStyle, textAlign: 'center', color: theme.textMuted, padding: '28px 0' }}>No clients found</td>
                </tr>
              ) : clients.map((client) => (
                <tr key={client.id}
                  onMouseEnter={(e) => e.currentTarget.style.background = `${theme.bgLight}44`}
                  onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                >
                  <td style={tdStyle}>{client.name ?? '—'}</td>
                  <td style={tdStyle}>{client.email}</td>
                  <td style={tdStyle}>
                    {editTarget === client.id ? (
                      <select
                        defaultValue={client.plan}
                        onChange={(e) => handleUpdateClient(client.id, { plan: e.target.value })}
                        style={{ background: theme.bgLight, border: `1px solid ${theme.primary}`, borderRadius: 6, color: theme.text, fontSize: 12, padding: '4px 8px', cursor: 'pointer', outline: 'none' }}
                        autoFocus
                        onBlur={() => setEditTarget(null)}
                      >
                        <option value="starter">Starter</option>
                        <option value="pro">Pro</option>
                        <option value="enterprise">Enterprise</option>
                      </select>
                    ) : (
                      <span style={{ textTransform: 'capitalize' }}>{client.plan ?? '—'}</span>
                    )}
                  </td>
                  <td style={tdStyle}><StatusBadge status={client.status} /></td>
                  <td style={tdStyle}>{client.created_at ? new Date(client.created_at).toLocaleDateString() : '—'}</td>
                  <td style={tdStyle}>
                    <div style={{ display: 'flex', gap: 8 }}>
                      <ActionBtn onClick={() => setEditTarget(client.id === editTarget ? null : client.id)}>
                        {editTarget === client.id ? 'Done' : 'Change Plan'}
                      </ActionBtn>
                      <ActionBtn
                        variant={client.status === 'suspended' ? 'success' : 'danger'}
                        onClick={() => setSuspendTarget(client.id)}
                      >
                        {client.status === 'suspended' ? 'Activate' : 'Suspend'}
                      </ActionBtn>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Pagination
        currentPage={page}
        totalPages={Math.ceil(total / pageSize)}
        onPageChange={setPage}
        pageSize={pageSize}
        onPageSizeChange={(s) => { setPageSize(s); setPage(1) }}
        totalItems={total}
      />

      {suspendTarget !== null && (() => {
        const c = clients.find((cl) => cl.id === suspendTarget)
        const isSuspended = c?.status === 'suspended'
        return (
          <ConfirmModal
            isOpen
            title={isSuspended ? 'Activate Client' : 'Suspend Client'}
            message={isSuspended
              ? `Activate account for ${c?.email}? They will regain access.`
              : `Suspend account for ${c?.email}? They will lose access immediately.`}
            confirmText={isSuspended ? 'Activate' : 'Suspend'}
            requireConfirmCheckbox={!isSuspended}
            onConfirm={handleSuspend}
            onCancel={() => setSuspendTarget(null)}
          />
        )
      })()}
    </section>
  )
}

// ─── Admin Page ───────────────────────────────────────────────────────────────
export default function Admin() {
  const user = (() => {
    try { return JSON.parse(localStorage.getItem('user') ?? 'null') } catch { return null }
  })()

  const isAdmin = user?.role === 'admin' || user?.is_admin === true

  if (!isAdmin) {
    return (
      <div style={{ padding: 48, textAlign: 'center' }}>
        <div style={{ fontSize: 48, marginBottom: 16 }}>🔒</div>
        <h2 style={{ fontSize: 20, color: theme.text, marginBottom: 8 }}>Access Denied</h2>
        <p style={{ color: theme.textMuted, fontSize: 14 }}>You need admin privileges to view this page.</p>
      </div>
    )
  }

  return (
    <div className="fade-in" style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 24 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <span style={{ fontSize: 22, fontWeight: 700, color: theme.text }}>Admin Panel</span>
        <span style={{ fontSize: 11, background: `${theme.error}22`, color: theme.error, borderRadius: 4, padding: '2px 10px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: 0.5 }}>Admin</span>
      </div>
      <LicenseManagement />
      <ClientManagement />
    </div>
  )
}
