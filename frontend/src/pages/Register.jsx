import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { MdPerson, MdEmail, MdLock, MdVisibility, MdVisibilityOff, MdCheckCircle } from 'react-icons/md'
import { register } from '../services/api'
import { useToast } from '../context/ToastContext'
import { useTheme } from '../context/ThemeContext'

function PasswordStrength({ password }) {
  const checks = [
    { label: 'At least 8 characters', ok: password.length >= 8 },
    { label: 'Uppercase letter (A-Z)', ok: /[A-Z]/.test(password) },
    { label: 'Lowercase letter (a-z)', ok: /[a-z]/.test(password) },
    { label: 'Number (0-9)', ok: /\d/.test(password) },
    { label: 'Special character (!@#$…)', ok: /[!@#$%^&*()_+\-=[\]{}|;':",./<>?]/.test(password) },
  ]
  const score = checks.filter((c) => c.ok).length

  const barColor =
    score <= 1 ? '#FF006E' :
    score <= 2 ? '#FFB800' :
    score <= 3 ? '#00D9FF' :
    '#00FF41'

  if (!password) return null

  return (
    <div style={{ marginTop: 8, marginBottom: 4 }}>
      <div style={{ display: 'flex', gap: 4, marginBottom: 8 }}>
        {checks.map((_, i) => (
          <div key={i} style={{
            flex: 1,
            height: 4,
            borderRadius: 2,
            background: i < score ? barColor : 'rgba(255,255,255,0.1)',
            transition: 'background 0.2s',
          }} />
        ))}
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
        {checks.map(({ label, ok }) => (
          <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11 }}>
            <span style={{ color: ok ? '#00FF41' : 'rgba(255,255,255,0.3)' }}>
              {ok ? '✓' : '○'}
            </span>
            <span style={{ color: ok ? '#00FF41' : 'rgba(255,255,255,0.4)' }}>{label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function Register() {
  const navigate = useNavigate()
  const { addToast } = useToast()
  const { theme } = useTheme()

  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const [loading, setLoading] = useState(false)

  const passwordsMatch = confirmPassword === '' || password === confirmPassword

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!name || !email || !password || !confirmPassword) {
      addToast('All fields are required', 'error')
      return
    }
    if (password !== confirmPassword) {
      addToast('Passwords do not match', 'error')
      return
    }
    setLoading(true)
    try {
      await register({ name, email, password })
      addToast('Account created! Please sign in.', 'success')
      navigate('/login')
    } catch (err) {
      const detail = err?.response?.data?.detail ?? 'Registration failed'
      const msg = Array.isArray(detail)
        ? detail.map((d) => d?.msg ?? d).join(', ')
        : detail
      addToast(msg, 'error')
    } finally {
      setLoading(false)
    }
  }

  const s = {
    page: {
      minHeight: '100vh',
      background: theme.bgDark,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: 24,
    },
    card: {
      background: theme.bgMedium,
      border: `1px solid ${theme.bgLight}`,
      borderRadius: 16,
      padding: '40px 36px',
      width: '100%',
      maxWidth: 440,
      boxShadow: '0 8px 40px rgba(0,0,0,0.4)',
    },
    logo: { textAlign: 'center', marginBottom: 28 },
    logoTitle: { fontSize: 26, fontWeight: 800, color: theme.primary, letterSpacing: 1 },
    logoSub: { fontSize: 13, color: theme.textMuted, marginTop: 4 },
    label: { display: 'block', fontSize: 13, fontWeight: 600, color: theme.textMuted, marginBottom: 6 },
    inputWrap: { position: 'relative', marginBottom: 16 },
    inputIcon: {
      position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)',
      color: theme.textMuted, pointerEvents: 'none',
    },
    input: (invalid) => ({
      width: '100%',
      padding: '11px 40px',
      background: theme.bgLight,
      border: `1px solid ${invalid ? theme.error : theme.bgLight}`,
      borderRadius: 8,
      color: theme.text,
      fontSize: 14,
      outline: 'none',
      transition: 'border-color 0.2s',
      boxSizing: 'border-box',
    }),
    eyeBtn: {
      position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)',
      background: 'transparent', border: 'none', cursor: 'pointer',
      color: theme.textMuted, display: 'flex', alignItems: 'center',
    },
    submitBtn: {
      width: '100%',
      padding: '12px',
      background: loading ? theme.bgLight : theme.primary,
      color: loading ? theme.textMuted : '#000',
      border: 'none',
      borderRadius: 8,
      fontSize: 15,
      fontWeight: 700,
      cursor: loading ? 'not-allowed' : 'pointer',
      transition: 'background 0.2s',
      marginTop: 8,
    },
    footer: { textAlign: 'center', marginTop: 24, fontSize: 13, color: theme.textMuted },
    link: { color: theme.primary, textDecoration: 'none', fontWeight: 600 },
  }

  return (
    <div style={s.page}>
      <div style={s.card}>
        <div style={s.logo}>
          <div style={s.logoTitle}>TG PRO QUANTUM</div>
          <div style={s.logoSub}>Create your account</div>
        </div>

        <form onSubmit={handleSubmit} autoComplete="on">
          {/* Name */}
          <label style={s.label}>Full Name</label>
          <div style={s.inputWrap}>
            <span style={s.inputIcon}><MdPerson size={18} /></span>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="John Doe"
              style={s.input(false)}
              onFocus={(e) => (e.target.style.borderColor = theme.primary)}
              onBlur={(e) => (e.target.style.borderColor = theme.bgLight)}
              autoComplete="name"
              required
            />
          </div>

          {/* Email */}
          <label style={s.label}>Email</label>
          <div style={s.inputWrap}>
            <span style={s.inputIcon}><MdEmail size={18} /></span>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              style={s.input(false)}
              onFocus={(e) => (e.target.style.borderColor = theme.primary)}
              onBlur={(e) => (e.target.style.borderColor = theme.bgLight)}
              autoComplete="email"
              required
            />
          </div>

          {/* Password */}
          <label style={s.label}>Password</label>
          <div style={s.inputWrap}>
            <span style={s.inputIcon}><MdLock size={18} /></span>
            <input
              type={showPassword ? 'text' : 'password'}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              style={s.input(false)}
              onFocus={(e) => (e.target.style.borderColor = theme.primary)}
              onBlur={(e) => (e.target.style.borderColor = theme.bgLight)}
              autoComplete="new-password"
              required
            />
            <button type="button" style={s.eyeBtn} onClick={() => setShowPassword((p) => !p)} tabIndex={-1}>
              {showPassword ? <MdVisibilityOff size={18} /> : <MdVisibility size={18} />}
            </button>
          </div>
          <PasswordStrength password={password} />

          {/* Confirm Password */}
          <label style={{ ...s.label, marginTop: 12 }}>Confirm Password</label>
          <div style={s.inputWrap}>
            <span style={s.inputIcon}><MdLock size={18} /></span>
            <input
              type={showConfirm ? 'text' : 'password'}
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="••••••••"
              style={s.input(!passwordsMatch)}
              onFocus={(e) => (e.target.style.borderColor = passwordsMatch ? theme.primary : theme.error)}
              onBlur={(e) => (e.target.style.borderColor = passwordsMatch ? theme.bgLight : theme.error)}
              autoComplete="new-password"
              required
            />
            <button type="button" style={s.eyeBtn} onClick={() => setShowConfirm((p) => !p)} tabIndex={-1}>
              {showConfirm ? <MdVisibilityOff size={18} /> : <MdVisibility size={18} />}
            </button>
          </div>
          {!passwordsMatch && (
            <div style={{ fontSize: 12, color: theme.error, marginTop: -8, marginBottom: 8 }}>
              Passwords do not match
            </div>
          )}

          <button type="submit" style={s.submitBtn} disabled={loading}>
            {loading ? 'Creating account…' : '🚀 Create Account'}
          </button>
        </form>

        <div style={s.footer}>
          Already have an account?{' '}
          <Link to="/login" style={s.link}>Sign In</Link>
        </div>
      </div>
    </div>
  )
}
