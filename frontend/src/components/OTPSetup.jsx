/**
 * OTPSetup – Sprint 3 TOTP / 2FA Setup for Accounts
 *
 * Flow:
 *  1. Call enableAccountOTP → receive secret + provisioning_uri + backup_codes
 *  2. Display QR code (rendered via a free QR service) and manual secret
 *  3. User scans with authenticator app → types first code → verifyAccountOTP
 *  4. On success show backup codes for the user to save
 */
import { useState } from 'react'
import { enableAccountOTP, verifyAccountOTP } from '../services/api'
import { FormButton, FormInput } from './Forms'
import theme from '../styles/theme'

const overlayStyle = {
  position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.75)',
  display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1200,
}
const modalStyle = {
  background: theme.bgMedium, border: `1px solid ${theme.bgLight}`,
  borderRadius: 16, padding: 32, width: '100%', maxWidth: 480,
  maxHeight: '90vh', overflowY: 'auto',
}

function StepSetup({ accountId, onSetupDone }) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const start = async () => {
    setLoading(true); setError('')
    try {
      const data = await enableAccountOTP(accountId)
      onSetupDone(data)
    } catch (err) {
      setError(err?.response?.data?.detail ?? 'Failed to enable OTP')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ textAlign: 'center', padding: '16px 0' }}>
      <div style={{ fontSize: 48, marginBottom: 16 }}>🔐</div>
      <h4 style={{ margin: '0 0 8px', fontSize: 16 }}>Enable Two-Factor Authentication</h4>
      <p style={{ color: theme.textMuted, fontSize: 13, margin: '0 0 24px', lineHeight: 1.6 }}>
        Add an extra layer of security using a TOTP authenticator app
        (Google Authenticator, Authy, etc.).
      </p>
      {error && <p style={{ color: theme.error, fontSize: 13, marginBottom: 12 }}>{error}</p>}
      <FormButton onClick={start} disabled={loading}>
        {loading ? 'Setting up…' : 'Enable 2FA'}
      </FormButton>
    </div>
  )
}

function StepScan({ setupData, onVerified }) {
  const [code, setCode] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [secretCopied, setSecretCopied] = useState(false)

  const copySecret = () => {
    navigator.clipboard.writeText(setupData.secret)
    setSecretCopied(true)
    setTimeout(() => setSecretCopied(false), 2000)
  }

  const verify = async (e) => {
    e.preventDefault()
    if (code.length < 6) { setError('Enter a 6-digit code'); return }
    setLoading(true); setError('')
    try {
      const res = await verifyAccountOTP(setupData.accountId, code)
      if (res.verified) {
        onVerified()
      } else {
        setError('Code is incorrect or expired. Try again.')
      }
    } catch (err) {
      setError(err?.response?.data?.detail ?? 'Verification failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20, alignItems: 'center' }}>
      <h4 style={{ margin: 0, fontSize: 15 }}>Add to Authenticator App</h4>
      <p style={{ margin: 0, fontSize: 13, color: theme.textMuted, textAlign: 'center' }}>
        Open your authenticator app (Google Authenticator, Authy, etc.) and
        add a new account using the secret key below.
      </p>
      {/* Show secret key with copy button – avoids sending URI to third-party services */}
      <div style={{
        background: theme.bgLight, borderRadius: 8, padding: '12px 16px',
        width: '100%', boxSizing: 'border-box',
      }}>
        <div style={{ fontSize: 11, color: theme.textMuted, marginBottom: 6 }}>
          Secret key (enter manually in your app)
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <code style={{
            flex: 1, fontFamily: 'monospace', fontSize: 13,
            letterSpacing: 2, wordBreak: 'break-all', color: theme.primary,
          }}>
            {setupData.secret}
          </code>
          <button
            onClick={copySecret}
            style={{
              background: theme.bgDark, border: `1px solid ${theme.bgLight}`,
              borderRadius: 6, padding: '4px 10px', cursor: 'pointer',
              color: secretCopied ? theme.success : theme.textMuted,
              fontSize: 12, whiteSpace: 'nowrap',
            }}
          >
            {secretCopied ? '✅ Copied' : '📋 Copy'}
          </button>
        </div>
      </div>
      <form onSubmit={verify} style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: 12 }}>
        <FormInput
          label="Verification Code *"
          value={code}
          onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
          placeholder="123456"
          maxLength={6}
        />
        {error && <p style={{ color: theme.error, fontSize: 13, margin: 0 }}>{error}</p>}
        <FormButton type="submit" disabled={loading || code.length < 6}>
          {loading ? 'Verifying…' : 'Verify & Activate'}
        </FormButton>
      </form>
    </div>
  )
}

function StepBackupCodes({ backupCodes, onClose }) {
  const [copied, setCopied] = useState(false)

  const copyAll = () => {
    navigator.clipboard.writeText(backupCodes.join('\n'))
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16, alignItems: 'center' }}>
      <div style={{ fontSize: 40 }}>✅</div>
      <h4 style={{ margin: 0, color: theme.success }}>2FA Enabled Successfully!</h4>
      <div style={{
        background: `${theme.warning}15`, border: `1px solid ${theme.warning}55`,
        borderRadius: 8, padding: '12px 16px', width: '100%',
      }}>
        <p style={{ margin: '0 0 10px', fontSize: 13, color: theme.warning, fontWeight: 600 }}>
          ⚠️ Save these backup codes now – they won't be shown again!
        </p>
        <div style={{
          display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 6,
          fontFamily: 'monospace', fontSize: 13, letterSpacing: 1,
        }}>
          {backupCodes.map((code, i) => (
            <span key={i} style={{
              background: theme.bgLight, borderRadius: 6, padding: '6px 10px',
              textAlign: 'center', color: theme.text,
            }}>
              {code}
            </span>
          ))}
        </div>
      </div>
      <div style={{ display: 'flex', gap: 10, width: '100%' }}>
        <FormButton variant="ghost" onClick={copyAll} style={{ flex: 1 }}>
          {copied ? '✅ Copied!' : '📋 Copy All'}
        </FormButton>
        <FormButton onClick={onClose} style={{ flex: 1 }}>Done</FormButton>
      </div>
    </div>
  )
}

// ── Main Modal ───────────────────────────────────────────────────────────────

export default function OTPSetup({ accountId, onClose, onEnabled }) {
  const [step, setStep] = useState('init')    // 'init' | 'scan' | 'backup'
  const [setupData, setSetupData] = useState(null)

  const handleSetupDone = (data) => {
    setSetupData({ ...data, accountId })
    setStep('scan')
  }

  const handleVerified = () => {
    setStep('backup')
    if (onEnabled) onEnabled(accountId)
  }

  return (
    <div style={overlayStyle} onClick={onClose}>
      <div style={modalStyle} onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
          <h3 style={{ margin: 0, fontSize: 17, fontWeight: 700 }}>🔐 Two-Factor Authentication</h3>
          {step !== 'backup' && (
            <button onClick={onClose} style={{
              background: 'none', border: 'none', color: theme.textMuted,
              fontSize: 20, cursor: 'pointer', lineHeight: 1,
            }}>✕</button>
          )}
        </div>

        {step === 'init' && <StepSetup accountId={accountId} onSetupDone={handleSetupDone} />}
        {step === 'scan' && <StepScan setupData={setupData} onVerified={handleVerified} />}
        {step === 'backup' && (
          <StepBackupCodes backupCodes={setupData?.backup_codes ?? []} onClose={onClose} />
        )}
      </div>
    </div>
  )
}
