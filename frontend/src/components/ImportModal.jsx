/**
 * ImportModal – Sprint 3 Account Import
 *
 * Three tabs:
 *  1. Session Import  – paste a session string (Ctrl+A)
 *  2. Bulk Create     – paste / type multiple phone numbers
 *  3. File Upload     – upload CSV or Excel file with progress bar
 */
import { useState, useRef } from 'react'
import { importSession, bulkCreateAccounts, importAccountsFile } from '../services/api'
import { FormButton, FormInput } from './Forms'
import theme from '../styles/theme'

const TABS = ['Session Import', 'Bulk Create', 'File Upload']

const overlayStyle = {
  position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)',
  display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1100,
}
const modalStyle = {
  background: theme.bgMedium, border: `1px solid ${theme.bgLight}`,
  borderRadius: 16, padding: 32, width: '100%', maxWidth: 560,
  maxHeight: '90vh', overflowY: 'auto',
}

function ResultBanner({ result }) {
  if (!result) return null
  const ok = result.status === 'completed' || result.imported > 0
  const color = ok ? theme.success : theme.error
  return (
    <div style={{
      background: `${color}18`, border: `1px solid ${color}55`,
      borderRadius: 8, padding: '12px 16px', marginTop: 16, fontSize: 13,
    }}>
      <strong style={{ color }}>
        {ok ? '✅ Import complete' : '⚠️ Import finished with errors'}
      </strong>
      <div style={{ marginTop: 6, lineHeight: 1.6, color: theme.text }}>
        <span>Imported: <b>{result.imported}</b></span>
        {'  ·  '}
        <span>Skipped: <b>{result.skipped}</b></span>
        {'  ·  '}
        <span>Failed: <b>{result.failed_rows}</b></span>
      </div>
      {result.errors?.length > 0 && (
        <ul style={{ marginTop: 8, paddingLeft: 18, color: theme.error, fontSize: 12 }}>
          {result.errors.slice(0, 5).map((e, i) => <li key={i}>{e}</li>)}
          {result.errors.length > 5 && <li>…and {result.errors.length - 5} more</li>}
        </ul>
      )}
    </div>
  )
}

// ── Tab 1: Session Import ────────────────────────────────────────────────────

function SessionTab({ onResult }) {
  const [text, setText] = useState('')
  const [phone, setPhone] = useState('')
  const [name, setName] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!text.trim()) { setError('Paste a session string first'); return }
    setLoading(true); setError('')
    try {
      const res = await importSession({ session_text: text, phone: phone || undefined, name: name || undefined })
      onResult(res)
    } catch (err) {
      setError(err?.response?.data?.detail ?? 'Import failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <p style={{ fontSize: 13, color: theme.textMuted, margin: 0 }}>
        Paste a session string (Ctrl+A in your Telegram client, then copy). Supported formats:
        pipe-separated, colon-separated, JSON, or raw base64 session.
      </p>
      <div>
        <label style={{ display: 'block', fontSize: 12, color: theme.textMuted, marginBottom: 4 }}>
          Session Text *
        </label>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="+123456789|12345678|abc123def456...|BQHa..."
          rows={5}
          style={{
            width: '100%', boxSizing: 'border-box',
            background: theme.bgLight, border: `1px solid ${theme.bgLight}`,
            borderRadius: 8, color: theme.text, padding: '10px 12px',
            fontFamily: 'monospace', fontSize: 12, resize: 'vertical',
          }}
        />
      </div>
      <FormInput label="Phone (override)" value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+1234567890 (optional)" />
      <FormInput label="Display Name (override)" value={name} onChange={(e) => setName(e.target.value)} placeholder="Account name (optional)" />
      {error && <p style={{ color: theme.error, fontSize: 13 }}>{error}</p>}
      <FormButton type="submit" disabled={loading}>{loading ? 'Importing…' : 'Import Session'}</FormButton>
    </form>
  )
}

// ── Tab 2: Bulk Create ───────────────────────────────────────────────────────

function BulkTab({ onResult }) {
  const [text, setText] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    const lines = text.split('\n').map((l) => l.trim()).filter(Boolean)
    if (!lines.length) { setError('Enter at least one phone number'); return }

    const accounts = lines.map((line) => {
      const parts = line.split(/[|,\t]/).map((p) => p.trim())
      return {
        phone: parts[0],
        name: parts[1] || undefined,
        api_id: parts[2] ? parseInt(parts[2], 10) : undefined,
        api_hash: parts[3] || undefined,
      }
    })

    setLoading(true); setError('')
    try {
      const res = await bulkCreateAccounts(accounts)
      onResult(res)
    } catch (err) {
      setError(err?.response?.data?.detail ?? 'Bulk create failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <p style={{ fontSize: 13, color: theme.textMuted, margin: 0 }}>
        Enter one account per line. Format: <code>phone</code> or
        {' '}<code>phone | name | api_id | api_hash</code>
      </p>
      <div>
        <label style={{ display: 'block', fontSize: 12, color: theme.textMuted, marginBottom: 4 }}>
          Accounts (one per line) *
        </label>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={'+1234567890\n+0987654321 | My Account | 12345678 | abc...'}
          rows={8}
          style={{
            width: '100%', boxSizing: 'border-box',
            background: theme.bgLight, border: `1px solid ${theme.bgLight}`,
            borderRadius: 8, color: theme.text, padding: '10px 12px',
            fontFamily: 'monospace', fontSize: 12, resize: 'vertical',
          }}
        />
      </div>
      {error && <p style={{ color: theme.error, fontSize: 13 }}>{error}</p>}
      <FormButton type="submit" disabled={loading}>{loading ? 'Creating…' : 'Bulk Create'}</FormButton>
    </form>
  )
}

// ── Tab 3: File Upload ───────────────────────────────────────────────────────

function FileTab({ onResult }) {
  const [file, setFile] = useState(null)
  const [progress, setProgress] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const fileRef = useRef()

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!file) { setError('Select a file first'); return }
    setLoading(true); setError(''); setProgress(0)
    try {
      const res = await importAccountsFile(file, (evt) => {
        if (evt.total) setProgress(Math.round((evt.loaded / evt.total) * 100))
      })
      onResult(res)
    } catch (err) {
      setError(err?.response?.data?.detail ?? 'File import failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <p style={{ fontSize: 13, color: theme.textMuted, margin: 0 }}>
        Upload a <b>CSV</b> or <b>Excel (.xlsx)</b> file. Required column: <code>phone</code>.
        Optional: <code>name</code>, <code>api_id</code>, <code>api_hash</code>,
        <code>session_string</code>, <code>tags</code>.
      </p>
      <div
        onClick={() => fileRef.current?.click()}
        style={{
          border: `2px dashed ${theme.bgLight}`, borderRadius: 10,
          padding: '24px 16px', textAlign: 'center', cursor: 'pointer',
          color: theme.textMuted, fontSize: 13,
          background: file ? `${theme.primary}10` : 'transparent',
        }}
      >
        {file ? (
          <span style={{ color: theme.primary }}>📄 {file.name} ({(file.size / 1024).toFixed(1)} KB)</span>
        ) : (
          '📁 Click to select CSV or Excel file'
        )}
        <input
          ref={fileRef} type="file"
          accept=".csv,.xlsx,.xls"
          style={{ display: 'none' }}
          onChange={(e) => setFile(e.target.files[0] || null)}
        />
      </div>

      {loading && (
        <div style={{ background: theme.bgLight, borderRadius: 4, height: 6, overflow: 'hidden' }}>
          <div style={{
            width: `${progress}%`, height: '100%',
            background: theme.primary, transition: 'width 0.2s',
          }} />
        </div>
      )}

      {error && <p style={{ color: theme.error, fontSize: 13 }}>{error}</p>}
      <FormButton type="submit" disabled={loading || !file}>
        {loading ? `Uploading… ${progress}%` : 'Import File'}
      </FormButton>
    </form>
  )
}

// ── Main Modal ───────────────────────────────────────────────────────────────

export default function ImportModal({ onClose, onImported }) {
  const [activeTab, setActiveTab] = useState(0)
  const [result, setResult] = useState(null)

  const handleResult = (res) => {
    setResult(res)
    if (onImported) onImported(res)
  }

  return (
    <div style={overlayStyle} onClick={onClose}>
      <div style={modalStyle} onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <h3 style={{ margin: 0, fontSize: 18, fontWeight: 700 }}>📥 Import Accounts</h3>
          <button onClick={onClose} style={{
            background: 'none', border: 'none', color: theme.textMuted,
            fontSize: 20, cursor: 'pointer', lineHeight: 1,
          }}>✕</button>
        </div>

        {/* Tabs */}
        <div style={{ display: 'flex', gap: 4, marginBottom: 24, background: theme.bgLight, borderRadius: 8, padding: 4 }}>
          {TABS.map((tab, i) => (
            <button
              key={tab}
              onClick={() => { setActiveTab(i); setResult(null) }}
              style={{
                flex: 1, padding: '8px 0', borderRadius: 6, border: 'none',
                cursor: 'pointer', fontSize: 13, fontWeight: 600,
                background: activeTab === i ? theme.primary : 'transparent',
                color: activeTab === i ? theme.bgDark : theme.textMuted,
                transition: 'all 0.15s',
              }}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        {activeTab === 0 && <SessionTab onResult={handleResult} />}
        {activeTab === 1 && <BulkTab onResult={handleResult} />}
        {activeTab === 2 && <FileTab onResult={handleResult} />}

        <ResultBanner result={result} />
      </div>
    </div>
  )
}
