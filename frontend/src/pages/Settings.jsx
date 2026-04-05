import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { FormInput, FormButton, FormSelect } from '../components/Forms'
import { useToast } from '../context/ToastContext'
import { getSettings, updateSettings, getPreferences, updatePreferences } from '../services/api'
import theme from '../styles/theme'

const TABS = ['General', 'Notifications', 'Privacy', 'Advanced']

const THEME_OPTIONS = [
  { value: 'dark',  label: 'Dark (default)' },
  { value: 'light', label: 'Light'          },
]

const LANG_OPTIONS = [
  { value: 'en', label: 'English' },
  { value: 'id', label: 'Indonesian' },
]

const TZ_OPTIONS = [
  { value: 'UTC',             label: 'UTC'                    },
  { value: 'Asia/Jakarta',    label: 'Asia/Jakarta (WIB)'     },
  { value: 'America/New_York',label: 'America/New York (EST)' },
  { value: 'Europe/London',   label: 'Europe/London (GMT)'    },
]

const PRIVACY_OPTIONS = [
  { value: 'private',  label: 'Private'  },
  { value: 'public',   label: 'Public'   },
  { value: 'contacts', label: 'Contacts' },
]

function Section({ title, children }) {
  return (
    <div style={{ background: theme.bgMedium, border: `1px solid ${theme.bgLight}`, borderRadius: 12, padding: 24, display: 'flex', flexDirection: 'column', gap: 18 }}>
      <h3 style={{ fontSize: 14, fontWeight: 600, color: theme.primary, borderBottom: `1px solid ${theme.bgLight}`, paddingBottom: 12 }}>{title}</h3>
      {children}
    </div>
  )
}

function Toggle({ label, description, checked, onChange }) {
  return (
    <label style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer', gap: 12 }}>
      <div>
        <span style={{ fontSize: 13, color: theme.text }}>{label}</span>
        {description && <p style={{ fontSize: 11, color: theme.textMuted, margin: '2px 0 0' }}>{description}</p>}
      </div>
      <div
        onClick={() => onChange(!checked)}
        style={{ flexShrink: 0, width: 42, height: 24, borderRadius: 12, background: checked ? theme.primary : theme.bgLight, position: 'relative', transition: 'background 0.2s' }}
      >
        <div style={{ position: 'absolute', top: 3, left: checked ? 20 : 3, width: 18, height: 18, borderRadius: '50%', background: checked ? theme.bgDark : theme.textMuted, transition: 'left 0.2s' }} />
      </div>
    </label>
  )
}

export default function Settings() {
  const { showToast } = useToast()
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState('General')
  const [settings, setSettings]   = useState({})
  const [prefs, setPrefs]         = useState({})
  const [saving, setSaving]       = useState(false)

  useEffect(() => {
    Promise.allSettled([getSettings(), getPreferences()]).then(([s, p]) => {
      if (s.status === 'fulfilled') setSettings(s.value ?? {})
      if (p.status === 'fulfilled') setPrefs(p.value ?? {})
    }).catch(() => {})
  }, [])

  const saveGeneral = async () => {
    setSaving(true)
    try {
      await updateSettings({ theme: settings.theme, language: settings.language, timezone: settings.timezone })
      showToast('Settings saved', 'success')
    } catch {
      showToast('Failed to save settings', 'error')
    } finally {
      setSaving(false)
    }
  }

  const savePrefs = async () => {
    setSaving(true)
    try {
      await updatePreferences(prefs)
      showToast('Preferences saved', 'success')
    } catch {
      showToast('Failed to save preferences', 'error')
    } finally {
      setSaving(false)
    }
  }

  const setNotif  = (key, val) => setPrefs((p) => ({ ...p, notifications: { ...(p.notifications ?? {}), [key]: val } }))
  const setPrivacy = (key, val) => setPrefs((p) => ({ ...p, privacy: { ...(p.privacy ?? {}), [key]: val } }))

  return (
    <div className="fade-in" style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 20, maxWidth: 680 }}>
      <h2 style={{ fontSize: 16, fontWeight: 600 }}>Settings</h2>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 4, borderBottom: `1px solid ${theme.bgLight}`, paddingBottom: 0 }}>
        {TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              background: 'none', border: 'none', cursor: 'pointer',
              padding: '8px 16px', fontSize: 13, fontWeight: 500,
              color: activeTab === tab ? theme.primary : theme.textMuted,
              borderBottom: `2px solid ${activeTab === tab ? theme.primary : 'transparent'}`,
              transition: 'color 0.15s, border-color 0.15s',
            }}
          >
            {tab}
          </button>
        ))}
      </div>

      {activeTab === 'General' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <Section title="Appearance">
            <FormSelect label="Theme" value={settings.theme ?? 'dark'} onChange={(e) => setSettings((s) => ({ ...s, theme: e.target.value }))} options={THEME_OPTIONS} />
          </Section>
          <Section title="Localization">
            <FormSelect label="Language" value={settings.language ?? 'en'} onChange={(e) => setSettings((s) => ({ ...s, language: e.target.value }))} options={LANG_OPTIONS} />
            <FormSelect label="Timezone" value={settings.timezone ?? 'UTC'} onChange={(e) => setSettings((s) => ({ ...s, timezone: e.target.value }))} options={TZ_OPTIONS} />
          </Section>
          <FormButton onClick={saveGeneral} disabled={saving}>{saving ? 'Saving…' : 'Save General Settings'}</FormButton>
        </div>
      )}

      {activeTab === 'Notifications' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <Section title="Notification Preferences">
            <Toggle label="Email notifications" description="Receive important alerts via email" checked={prefs.notifications?.email ?? true} onChange={(v) => setNotif('email', v)} />
            <Toggle label="In-app notifications" description="Show notifications inside the app" checked={prefs.notifications?.in_app ?? true} onChange={(v) => setNotif('in_app', v)} />
            <Toggle label="Campaign completed" description="Notify when a campaign finishes" checked={prefs.notifications?.campaign_completed ?? true} onChange={(v) => setNotif('campaign_completed', v)} />
            <Toggle label="Error alerts" description="Notify on system errors" checked={prefs.notifications?.error_alerts ?? true} onChange={(v) => setNotif('error_alerts', v)} />
            <Toggle label="Account banned" description="Notify when an account gets banned" checked={prefs.notifications?.account_banned ?? false} onChange={(v) => setNotif('account_banned', v)} />
          </Section>
          <FormButton onClick={savePrefs} disabled={saving}>{saving ? 'Saving…' : 'Save Notifications'}</FormButton>
        </div>
      )}

      {activeTab === 'Privacy' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <Section title="Privacy Settings">
            <FormSelect label="Account Visibility" value={prefs.privacy?.account_visibility ?? 'private'} onChange={(e) => setPrivacy('account_visibility', e.target.value)} options={PRIVACY_OPTIONS} />
            <Toggle label="Data sharing" description="Allow anonymous usage analytics" checked={prefs.privacy?.data_sharing ?? false} onChange={(v) => setPrivacy('data_sharing', v)} />
          </Section>
          <FormButton onClick={savePrefs} disabled={saving}>{saving ? 'Saving…' : 'Save Privacy Settings'}</FormButton>
        </div>
      )}

      {activeTab === 'Advanced' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <Section title="API & Integrations">
            <p style={{ fontSize: 13, color: theme.textMuted }}>Advanced API settings are managed through the Profile page API Keys section.</p>
        <FormButton onClick={() => navigate('/profile')} variant="ghost">Go to Profile → API Keys</FormButton>
          </Section>
          <Section title="Telegram API Configuration">
            <FormInput label="Default API ID" placeholder="Leave blank to use per-account API ID" value={settings.default_api_id ?? ''} onChange={(e) => setSettings((s) => ({ ...s, default_api_id: e.target.value }))} type="number" />
            <FormInput label="Default API Hash" placeholder="Leave blank to use per-account API Hash" value={settings.default_api_hash ?? ''} onChange={(e) => setSettings((s) => ({ ...s, default_api_hash: e.target.value }))} type="password" />
          </Section>
          <FormButton onClick={() => updateSettings(settings).then(() => showToast('Saved', 'success')).catch(() => showToast('Failed', 'error'))} disabled={saving}>Save Advanced Settings</FormButton>
        </div>
      )}
    </div>
  )
}
