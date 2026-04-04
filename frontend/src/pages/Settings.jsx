import { useState } from 'react'
import { FormInput, FormButton } from '../components/Forms'
import theme from '../styles/theme'

function Section({ title, children }) {
  return (
    <div style={{ background: theme.bgMedium, border: `1px solid ${theme.bgLight}`, borderRadius: 12, padding: 24, display: 'flex', flexDirection: 'column', gap: 18 }}>
      <h3 style={{ fontSize: 14, fontWeight: 600, color: theme.primary, borderBottom: `1px solid ${theme.bgLight}`, paddingBottom: 12 }}>{title}</h3>
      {children}
    </div>
  )
}

function Toggle({ label, checked, onChange }) {
  return (
    <label style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }}>
      <span style={{ fontSize: 13, color: theme.text }}>{label}</span>
      <div
        onClick={() => onChange(!checked)}
        style={{
          width: 42, height: 24, borderRadius: 12,
          background: checked ? theme.primary : theme.bgLight,
          position: 'relative', transition: 'background 0.2s',
        }}
      >
        <div style={{
          position: 'absolute', top: 3,
          left: checked ? 20 : 3,
          width: 18, height: 18, borderRadius: '50%',
          background: checked ? theme.bgDark : theme.textMuted,
          transition: 'left 0.2s',
        }} />
      </div>
    </label>
  )
}

export default function Settings() {
  const [apiId, setApiId]     = useState('')
  const [apiHash, setApiHash] = useState('')
  const [notifyCampaign, setNotifyCampaign] = useState(true)
  const [notifyError,    setNotifyError]    = useState(true)
  const [notifyBanned,   setNotifyBanned]   = useState(false)
  const [saved, setSaved] = useState(false)

  const handleSave = (e) => {
    e.preventDefault()
    // Persist to backend in a real implementation
    setSaved(true)
    setTimeout(() => setSaved(false), 2500)
  }

  return (
    <div className="fade-in" style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 20, maxWidth: 640 }}>
      <h2 style={{ fontSize: 16, fontWeight: 600 }}>Settings</h2>

      <form onSubmit={handleSave} style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
        <Section title="Telegram API Configuration">
          <FormInput
            label="API ID"
            placeholder="12345678"
            value={apiId}
            onChange={(e) => setApiId(e.target.value)}
            type="number"
          />
          <FormInput
            label="API Hash"
            placeholder="0123456789abcdef0123456789abcdef"
            value={apiHash}
            onChange={(e) => setApiHash(e.target.value)}
            type="password"
          />
        </Section>

        <Section title="Notifications">
          <Toggle label="Campaign completed"  checked={notifyCampaign} onChange={setNotifyCampaign} />
          <Toggle label="Error alerts"        checked={notifyError}    onChange={setNotifyError}    />
          <Toggle label="Account banned"      checked={notifyBanned}   onChange={setNotifyBanned}   />
        </Section>

        <Section title="Appearance">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: 13, color: theme.text }}>Theme</span>
            <span style={{ fontSize: 12, color: theme.textMuted, background: theme.bgLight, borderRadius: 6, padding: '4px 12px' }}>
              Dark (default)
            </span>
          </div>
        </Section>

        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <FormButton type="submit">Save Settings</FormButton>
          {saved && <span style={{ fontSize: 13, color: theme.success }}>✓ Saved!</span>}
        </div>
      </form>
    </div>
  )
}
