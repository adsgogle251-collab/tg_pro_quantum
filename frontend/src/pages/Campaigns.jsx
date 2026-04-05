import { useState, useEffect, useCallback } from 'react'
import { MdAdd, MdEdit, MdDelete, MdSearch } from 'react-icons/md'
import { getCampaigns, createCampaign, updateCampaign, deleteCampaign } from '../services/api'
import { FormSelect, FormButton, FormInput } from '../components/Forms'
import DataTable from '../components/DataTable'
import ConfirmModal from '../components/ConfirmModal'
import { useToast } from '../context/ToastContext'
import theme from '../styles/theme'

const STATUS_OPTIONS = [
  { value: 'all',       label: 'All Statuses'  },
  { value: 'draft',     label: 'Draft'         },
  { value: 'running',   label: 'Running'       },
  { value: 'paused',    label: 'Paused'        },
  { value: 'completed', label: 'Completed'     },
  { value: 'failed',    label: 'Failed'        },
]

const STATUS_COLORS = {
  draft:     theme.textMuted,
  running:   theme.success,
  paused:    theme.accent,
  scheduled: theme.primary,
  completed: theme.primary,
  failed:    theme.error,
}

const MODE_OPTIONS = [
  { value: 'once',        label: 'Once'        },
  { value: 'round_robin', label: 'Round Robin' },
  { value: 'loop',        label: 'Loop'        },
]

const EMPTY_FORM = {
  name: '',
  message_text: '',
  mode: 'once',
  delay_min: 27,
  delay_max: 33,
  status: 'draft',
}

function Badge({ status }) {
  const color = STATUS_COLORS[status] ?? theme.textMuted
  return (
    <span style={{
      background: `${color}22`,
      color,
      border: `1px solid ${color}55`,
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

function CampaignModal({ campaign, onClose, onSave }) {
  const [form, setForm] = useState(campaign ? {
    name:         campaign.name         ?? '',
    message_text: campaign.message_text ?? '',
    mode:         campaign.mode         ?? 'once',
    delay_min:    campaign.delay_min    ?? 27,
    delay_max:    campaign.delay_max    ?? 33,
  } : EMPTY_FORM)
  const [saving, setSaving] = useState(false)
  const [error, setError]   = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.name.trim()) { setError('Name is required'); return }
    if (!form.message_text.trim()) { setError('Message text is required'); return }
    setSaving(true)
    setError('')
    try {
      await onSave(form)
    } catch (err) {
      setError(err?.response?.data?.detail ?? 'Save failed')
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
    borderRadius: 14, padding: 28, width: '100%', maxWidth: 500,
  }

  return (
    <div style={overlay} onClick={onClose}>
      <div style={modal} onClick={(e) => e.stopPropagation()}>
        <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 20 }}>
          {campaign ? 'Edit Campaign' : 'Create Campaign'}
        </h3>
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <FormInput label="Name" value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} placeholder="Campaign name" required />
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <label style={{ fontSize: 12, color: theme.textMuted, fontWeight: 500 }}>Message Text</label>
            <textarea
              value={form.message_text}
              onChange={(e) => setForm((f) => ({ ...f, message_text: e.target.value }))}
              placeholder="Message content..."
              rows={4}
              style={{ background: theme.bgLight, border: `1px solid ${theme.bgLight}`, borderRadius: 8, color: theme.text, fontSize: 13, padding: '10px 14px', outline: 'none', resize: 'vertical' }}
            />
          </div>
          <FormSelect label="Mode" value={form.mode} onChange={(e) => setForm((f) => ({ ...f, mode: e.target.value }))} options={MODE_OPTIONS} />
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <FormInput label="Delay Min (s)" type="number" value={form.delay_min} onChange={(e) => setForm((f) => ({ ...f, delay_min: +e.target.value }))} min={1} />
            <FormInput label="Delay Max (s)" type="number" value={form.delay_max} onChange={(e) => setForm((f) => ({ ...f, delay_max: +e.target.value }))} min={1} />
          </div>
          {error && <p style={{ color: theme.error, fontSize: 13 }}>{error}</p>}
          <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', marginTop: 4 }}>
            <FormButton variant="ghost" type="button" onClick={onClose}>Cancel</FormButton>
            <FormButton type="submit" disabled={saving}>{saving ? 'Saving…' : 'Save'}</FormButton>
          </div>
        </form>
      </div>
    </div>
  )
}

export default function Campaigns() {
  const { showToast } = useToast()
  const [campaigns, setCampaigns] = useState([])
  const [loading, setLoading]     = useState(true)
  const [filter, setFilter]       = useState('all')
  const [search, setSearch]       = useState('')
  const [modal, setModal]         = useState(null)   // null | 'create' | campaign obj
  const [confirm, setConfirm]     = useState(null)   // campaign to delete

  const load = useCallback(() => {
    setLoading(true)
    getCampaigns()
      .then((data) => setCampaigns(Array.isArray(data) ? data : (data.items ?? [])))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { load() }, [load])

  const visible = campaigns.filter((c) => {
    const matchStatus = filter === 'all' || c.status === filter
    const matchSearch = !search || c.name?.toLowerCase().includes(search.toLowerCase())
    return matchStatus && matchSearch
  })

  const handleSave = async (form) => {
    if (modal && modal !== 'create') {
      await updateCampaign(modal.id, form)
      showToast('Campaign updated', 'success')
    } else {
      await createCampaign(form)
      showToast('Campaign created', 'success')
    }
    setModal(null)
    load()
  }

  const handleDelete = async () => {
    if (!confirm) return
    try {
      await deleteCampaign(confirm.id)
      showToast('Campaign deleted', 'success')
      load()
    } catch {
      showToast('Delete failed', 'error')
    } finally {
      setConfirm(null)
    }
  }

  const columns = [
    { key: 'id',           label: '#',        sortable: true, width: 60 },
    { key: 'name',         label: 'Name',     sortable: true,
      render: (v) => <span style={{ fontWeight: 500 }}>{v}</span> },
    { key: 'status',       label: 'Status',
      render: (v) => <Badge status={v} /> },
    { key: 'mode',         label: 'Mode',     sortable: true },
    { key: 'sent_count',   label: 'Sent',     sortable: true,
      render: (v) => (v ?? 0).toLocaleString() },
    { key: 'failed_count', label: 'Failed',   sortable: true,
      render: (v) => <span style={{ color: theme.error }}>{(v ?? 0).toLocaleString()}</span> },
    { key: 'id', label: 'Actions', width: 110,
      render: (_, row) => (
        <div style={{ display: 'flex', gap: 6 }}>
          <button onClick={() => setModal(row)} title="Edit"
            style={{ background: 'none', border: 'none', color: theme.primary, cursor: 'pointer' }}>
            <MdEdit size={16} />
          </button>
          <button onClick={() => setConfirm(row)} title="Delete"
            style={{ background: 'none', border: 'none', color: theme.error, cursor: 'pointer' }}>
            <MdDelete size={16} />
          </button>
        </div>
      ),
    },
  ]

  return (
    <div className="fade-in" style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 20 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
        <h2 style={{ fontSize: 16, fontWeight: 600 }}>Campaigns</h2>
        <FormButton onClick={() => setModal('create')}>
          <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}><MdAdd size={16} /> New Campaign</span>
        </FormButton>
      </div>

      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
        <div style={{ position: 'relative', flex: 1, minWidth: 180 }}>
          <MdSearch size={16} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: theme.textMuted }} />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search campaigns…"
            style={{ width: '100%', paddingLeft: 32, padding: '8px 12px 8px 32px', background: theme.bgMedium, border: `1px solid ${theme.bgLight}`, borderRadius: 8, color: theme.text, fontSize: 13, outline: 'none' }}
          />
        </div>
        <FormSelect value={filter} onChange={(e) => setFilter(e.target.value)} options={STATUS_OPTIONS} style={{ width: 160 }} />
      </div>

      <div style={{ background: theme.bgMedium, border: `1px solid ${theme.bgLight}`, borderRadius: 12, overflow: 'hidden' }}>
        <DataTable columns={columns} rows={visible} keyField="id" emptyMsg={loading ? 'Loading…' : 'No campaigns found.'} pageSize={10} />
      </div>

      {modal && (
        <CampaignModal
          campaign={modal === 'create' ? null : modal}
          onClose={() => setModal(null)}
          onSave={handleSave}
        />
      )}

      {confirm && (
        <ConfirmModal
          isOpen={true}
          message={`Delete campaign "${confirm.name}"? This cannot be undone.`}
          onConfirm={handleDelete}
          onCancel={() => setConfirm(null)}
        />
      )}
    </div>
  )
}

