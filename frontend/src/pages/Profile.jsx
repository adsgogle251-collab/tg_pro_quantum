import { useState, useEffect } from 'react'
import {
  getProfile,
  updateProfile,
  changePassword,
  setup2FA,
  verify2FA,
  disable2FA,
  getApiKeys,
  createApiKey,
  revokeApiKey,
} from '../services/api'
import { useToast } from '../context/ToastContext'
import useForm from '../hooks/useForm'
import { Spinner } from '../components/Loading'
import ConfirmModal from '../components/ConfirmModal'
import theme from '../styles/theme'

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

const fieldError = {
  fontSize: 12,
  color: theme.error,
  marginTop: 4,
}

function Field({ label, error, children }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      <label style={{ fontSize: 13, color: theme.textMuted, fontWeight: 500 }}>{label}</label>
      {children}
      {error && <span style={fieldError}>{error}</span>}
    </div>
  )
}

function Input({ error, ...props }) {
  const [focused, setFocused] = useState(false)
  return (
    <input
      {...props}
      style={{
        background: theme.bgLight,
        border: `1px solid ${focused ? theme.primary : (error ? theme.error : theme.bgLight)}`,
        borderRadius: 8,
        color: theme.text,
        fontSize: 14,
        padding: '10px 14px',
        outline: 'none',
        width: '100%',
        transition: 'border-color 0.2s',
        ...(props.style ?? {}),
      }}
      onFocus={(e) => { setFocused(true); props.onFocus?.(e) }}
      onBlur={(e) => { setFocused(false); props.onBlur?.(e) }}
    />
  )
}

function Btn({ children, variant = 'primary', disabled, loading, ...props }) {
  const bg = variant === 'danger' ? theme.error : theme.primary
  const color = variant === 'danger' ? '#fff' : theme.bgDark
  return (
    <button
      {...props}
      disabled={disabled || loading}
      style={{
        background: disabled || loading ? `${bg}55` : bg,
        color,
        border: 'none',
        borderRadius: 8,
        padding: '10px 22px',
        fontSize: 14,
        fontWeight: 600,
        cursor: disabled || loading ? 'not-allowed' : 'pointer',
        display: 'inline-flex',
        alignItems: 'center',
        gap: 8,
        transition: 'opacity 0.2s',
        ...(props.style ?? {}),
      }}
    >
      {loading && <Spinner size={14} color={color} />}
      {children}
    </button>
  )
}

// ─── Profile Info Section ───────────────────────────────────────────────────
function ProfileSection({ user, onUpdated }) {
  const { addToast } = useToast()
  const { values, errors, handleChange, handleSubmit, isSubmitting, setValues } = useForm(
    { name: user?.name ?? '', email: user?.email ?? '' },
    { name: ['required'], email: ['required', 'email'] }
  )

  useEffect(() => {
    setValues({ name: user?.name ?? '', email: user?.email ?? '' })
  }, [user])

  const onSubmit = handleSubmit(async (vals) => {
    try {
      const updated = await updateProfile(vals)
      addToast('Profile updated successfully', 'success')
      onUpdated?.(updated)
    } catch {
      addToast('Failed to update profile', 'error')
    }
  })

  return (
    <section style={card}>
      <h2 style={sectionTitle}>Profile Information</h2>
      <form onSubmit={onSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          <Field label="Name" error={errors.name}>
            <Input name="name" value={values.name} onChange={handleChange} error={errors.name} placeholder="Your name" />
          </Field>
          <Field label="Email" error={errors.email}>
            <Input name="email" type="email" value={values.email} onChange={handleChange} error={errors.email} placeholder="you@example.com" />
          </Field>
        </div>
        <div>
          <Btn type="submit" loading={isSubmitting}>Save Changes</Btn>
        </div>
      </form>
    </section>
  )
}

// ─── Change Password Section ─────────────────────────────────────────────────
function PasswordSection() {
  const { addToast } = useToast()
  const { values, errors, handleChange, handleSubmit, isSubmitting, reset } = useForm(
    { currentPassword: '', newPassword: '', confirmPassword: '' },
    {
      currentPassword: ['required'],
      newPassword: ['required', { type: 'minLength', value: 8 }],
      confirmPassword: [
        'required',
        (v) => v !== values.newPassword ? 'Passwords do not match' : null,
      ],
    }
  )

  const onSubmit = handleSubmit(async (vals) => {
    try {
      await changePassword({ currentPassword: vals.currentPassword, newPassword: vals.newPassword })
      addToast('Password changed successfully', 'success')
      reset()
    } catch (err) {
      addToast(err?.response?.data?.detail ?? 'Failed to change password', 'error')
    }
  })

  return (
    <section style={card}>
      <h2 style={sectionTitle}>Change Password</h2>
      <form onSubmit={onSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16, maxWidth: 480 }}>
        <Field label="Current Password" error={errors.currentPassword}>
          <Input name="currentPassword" type="password" value={values.currentPassword} onChange={handleChange} error={errors.currentPassword} />
        </Field>
        <Field label="New Password" error={errors.newPassword}>
          <Input name="newPassword" type="password" value={values.newPassword} onChange={handleChange} error={errors.newPassword} />
        </Field>
        <Field label="Confirm New Password" error={errors.confirmPassword}>
          <Input name="confirmPassword" type="password" value={values.confirmPassword} onChange={handleChange} error={errors.confirmPassword} />
        </Field>
        <div>
          <Btn type="submit" loading={isSubmitting}>Update Password</Btn>
        </div>
      </form>
    </section>
  )
}

// ─── 2FA Section ─────────────────────────────────────────────────────────────
function TwoFASection({ user, onUpdated }) {
  const { addToast } = useToast()
  const [qrData, setQrData] = useState(null)
  const [code, setCode] = useState('')
  const [loading, setLoading] = useState(false)
  const [showDisable, setShowDisable] = useState(false)

  const handleSetup = async () => {
    setLoading(true)
    try {
      const data = await setup2FA()
      setQrData(data)
    } catch {
      addToast('Failed to setup 2FA', 'error')
    } finally {
      setLoading(false)
    }
  }

  const handleVerify = async () => {
    if (!code.trim()) return
    setLoading(true)
    try {
      await verify2FA({ code })
      addToast('2FA enabled successfully', 'success')
      setQrData(null)
      setCode('')
      onUpdated?.({ ...user, twofa_enabled: true })
    } catch {
      addToast('Invalid verification code', 'error')
    } finally {
      setLoading(false)
    }
  }

  const handleDisable = async () => {
    setLoading(true)
    try {
      await disable2FA()
      addToast('2FA disabled', 'warning')
      setShowDisable(false)
      onUpdated?.({ ...user, twofa_enabled: false })
    } catch {
      addToast('Failed to disable 2FA', 'error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <section style={card}>
      <h2 style={sectionTitle}>Two-Factor Authentication (2FA)</h2>
      {user?.twofa_enabled ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ width: 10, height: 10, borderRadius: '50%', background: theme.success, display: 'inline-block' }} />
            <span style={{ fontSize: 14, color: theme.success, fontWeight: 600 }}>2FA is enabled</span>
          </div>
          <Btn variant="danger" onClick={() => setShowDisable(true)} loading={loading}>Disable 2FA</Btn>
          <ConfirmModal
            isOpen={showDisable}
            title="Disable 2FA"
            message="This will remove the extra layer of security from your account."
            confirmText="Disable 2FA"
            requireConfirmCheckbox
            onConfirm={handleDisable}
            onCancel={() => setShowDisable(false)}
          />
        </div>
      ) : qrData ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16, maxWidth: 400 }}>
          <p style={{ fontSize: 13, color: theme.textMuted }}>Scan the QR code with your authenticator app</p>
          {qrData.qr_url && (
            <img src={qrData.qr_url} alt="2FA QR Code" style={{ width: 180, height: 180, borderRadius: 8, background: '#fff', padding: 8 }} />
          )}
          {qrData.secret && (
            <div style={{ background: theme.bgLight, borderRadius: 8, padding: '10px 14px', fontFamily: 'monospace', fontSize: 13, color: theme.text, letterSpacing: 1 }}>
              {qrData.secret}
            </div>
          )}
          <Field label="Verification Code">
            <Input value={code} onChange={(e) => setCode(e.target.value)} placeholder="6-digit code" maxLength={6} />
          </Field>
          <div style={{ display: 'flex', gap: 10 }}>
            <Btn onClick={handleVerify} loading={loading}>Verify & Enable</Btn>
            <button onClick={() => setQrData(null)} style={{ background: 'transparent', border: `1px solid ${theme.bgLight}`, color: theme.textMuted, borderRadius: 8, padding: '10px 16px', cursor: 'pointer', fontSize: 14 }}>Cancel</button>
          </div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <p style={{ fontSize: 13, color: theme.textMuted, lineHeight: 1.6 }}>
            Add an extra layer of security to your account using an authenticator app.
          </p>
          <Btn onClick={handleSetup} loading={loading}>Setup 2FA</Btn>
        </div>
      )}
    </section>
  )
}

// ─── API Keys Section ─────────────────────────────────────────────────────────
function ApiKeysSection() {
  const { addToast } = useToast()
  const [keys, setKeys] = useState([])
  const [loading, setLoading] = useState(true)
  const [revokeTarget, setRevokeTarget] = useState(null)
  const [creating, setCreating] = useState(false)

  useEffect(() => {
    getApiKeys()
      .then(setKeys)
      .catch(() => setKeys([]))
      .finally(() => setLoading(false))
  }, [])

  const handleCreate = async () => {
    setCreating(true)
    try {
      const key = await createApiKey()
      setKeys((prev) => [key, ...prev])
      addToast('API key created', 'success')
    } catch {
      addToast('Failed to create API key', 'error')
    } finally {
      setCreating(false)
    }
  }

  const handleRevoke = async () => {
    try {
      await revokeApiKey(revokeTarget)
      setKeys((prev) => prev.filter((k) => k.id !== revokeTarget))
      addToast('API key revoked', 'warning')
    } catch {
      addToast('Failed to revoke key', 'error')
    } finally {
      setRevokeTarget(null)
    }
  }

  const handleCopy = (key) => {
    navigator.clipboard.writeText(key).then(() => addToast('Copied to clipboard', 'info'))
  }

  return (
    <section style={card}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h2 style={{ ...sectionTitle, marginBottom: 0, paddingBottom: 0, borderBottom: 'none' }}>API Keys</h2>
        <Btn onClick={handleCreate} loading={creating} style={{ padding: '8px 16px', fontSize: 13 }}>+ Generate Key</Btn>
      </div>
      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 24 }}><Spinner /></div>
      ) : keys.length === 0 ? (
        <p style={{ fontSize: 13, color: theme.textMuted, textAlign: 'center', padding: '20px 0' }}>No API keys yet</p>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {keys.map((k) => (
            <div key={k.id} style={{ display: 'flex', alignItems: 'center', gap: 12, background: theme.bgLight, borderRadius: 8, padding: '10px 14px' }}>
              <span style={{ flex: 1, fontFamily: 'monospace', fontSize: 12, color: theme.textMuted, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {k.key_preview ?? '••••••••••••••••••••••••••••••••'}
              </span>
              <span style={{ fontSize: 11, color: theme.textMuted, whiteSpace: 'nowrap' }}>{k.label ?? k.created_at?.slice(0, 10)}</span>
              <button onClick={() => handleCopy(k.key ?? k.key_preview ?? '')} style={{ background: 'transparent', border: `1px solid ${theme.bgLight}`, color: theme.primary, borderRadius: 6, padding: '4px 10px', cursor: 'pointer', fontSize: 12 }}>Copy</button>
              <button onClick={() => setRevokeTarget(k.id)} style={{ background: 'transparent', border: `1px solid ${theme.error}44`, color: theme.error, borderRadius: 6, padding: '4px 10px', cursor: 'pointer', fontSize: 12 }}>Revoke</button>
            </div>
          ))}
        </div>
      )}
      <ConfirmModal
        isOpen={revokeTarget !== null}
        title="Revoke API Key"
        message="This key will stop working immediately. This action cannot be undone."
        confirmText="Revoke Key"
        requireConfirmCheckbox
        onConfirm={handleRevoke}
        onCancel={() => setRevokeTarget(null)}
      />
    </section>
  )
}

// ─── Profile Page ─────────────────────────────────────────────────────────────
export default function Profile() {
  const [user, setUser] = useState(() => {
    try { return JSON.parse(localStorage.getItem('user') ?? 'null') } catch { return null }
  })
  const [loading, setLoading] = useState(!user)

  useEffect(() => {
    getProfile()
      .then((data) => {
        setUser(data)
        localStorage.setItem('user', JSON.stringify(data))
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', padding: 80 }}>
        <Spinner size={40} />
      </div>
    )
  }

  return (
    <div className="fade-in" style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 24, maxWidth: 900 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        <div style={{ width: 64, height: 64, borderRadius: '50%', background: `${theme.primary}22`, border: `2px solid ${theme.primary}`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 26 }}>
          {user?.name?.[0]?.toUpperCase() ?? '?'}
        </div>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: theme.text }}>{user?.name ?? 'User'}</h1>
          <span style={{ fontSize: 13, color: theme.textMuted }}>{user?.email}</span>
          {user?.role && (
            <span style={{ marginLeft: 10, fontSize: 11, background: `${theme.primary}22`, color: theme.primary, borderRadius: 4, padding: '2px 8px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: 0.5 }}>
              {user.role}
            </span>
          )}
        </div>
      </div>

      <ProfileSection user={user} onUpdated={setUser} />
      <PasswordSection />
      <TwoFASection user={user} onUpdated={setUser} />
      <ApiKeysSection />
    </div>
  )
}
