import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { MdLock, MdEmail, MdVisibility, MdVisibilityOff } from 'react-icons/md'
import { login } from '../services/api'
import { useToast } from '../context/ToastContext'
import { useTheme } from '../context/ThemeContext'

export default function Login() {
  const navigate = useNavigate()
  const { addToast } = useToast()
  const { theme } = useTheme()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!email || !password) {
      addToast('Email and password are required', 'error')
      return
    }
    setLoading(true)
    try {
      const data = await login({ email, password })
      localStorage.setItem('auth_token', data.access_token)
      // Store minimal user info from the token payload if available
      if (data.user) {
        localStorage.setItem('user', JSON.stringify(data.user))
      }
      addToast('Logged in successfully', 'success')
      navigate('/')
    } catch (err) {
      const detail = err?.response?.data?.detail ?? 'Invalid email or password'
      addToast(detail, 'error')
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
      maxWidth: 400,
      boxShadow: '0 8px 40px rgba(0,0,0,0.4)',
    },
    logo: {
      textAlign: 'center',
      marginBottom: 32,
    },
    logoTitle: {
      fontSize: 26,
      fontWeight: 800,
      color: theme.primary,
      letterSpacing: 1,
    },
    logoSub: {
      fontSize: 13,
      color: theme.textMuted,
      marginTop: 4,
    },
    label: {
      display: 'block',
      fontSize: 13,
      fontWeight: 600,
      color: theme.textMuted,
      marginBottom: 6,
    },
    inputWrap: {
      position: 'relative',
      marginBottom: 20,
    },
    inputIcon: {
      position: 'absolute',
      left: 12,
      top: '50%',
      transform: 'translateY(-50%)',
      color: theme.textMuted,
      pointerEvents: 'none',
    },
    input: {
      width: '100%',
      padding: '11px 40px',
      background: theme.bgLight,
      border: `1px solid ${theme.bgLight}`,
      borderRadius: 8,
      color: theme.text,
      fontSize: 14,
      outline: 'none',
      transition: 'border-color 0.2s',
    },
    eyeBtn: {
      position: 'absolute',
      right: 10,
      top: '50%',
      transform: 'translateY(-50%)',
      background: 'transparent',
      border: 'none',
      cursor: 'pointer',
      color: theme.textMuted,
      display: 'flex',
      alignItems: 'center',
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
  }

  return (
    <div style={s.page}>
      <div style={s.card}>
        <div style={s.logo}>
          <div style={s.logoTitle}>TG PRO QUANTUM</div>
          <div style={s.logoSub}>Enterprise Broadcast System</div>
        </div>

        <form onSubmit={handleSubmit} autoComplete="on">
          <label style={s.label}>Email</label>
          <div style={s.inputWrap}>
            <span style={s.inputIcon}><MdEmail size={18} /></span>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="admin@example.com"
              style={s.input}
              onFocus={(e) => (e.target.style.borderColor = theme.primary)}
              onBlur={(e) => (e.target.style.borderColor = theme.bgLight)}
              autoComplete="email"
              required
            />
          </div>

          <label style={s.label}>Password</label>
          <div style={s.inputWrap}>
            <span style={s.inputIcon}><MdLock size={18} /></span>
            <input
              type={showPassword ? 'text' : 'password'}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              style={s.input}
              onFocus={(e) => (e.target.style.borderColor = theme.primary)}
              onBlur={(e) => (e.target.style.borderColor = theme.bgLight)}
              autoComplete="current-password"
              required
            />
            <button
              type="button"
              style={s.eyeBtn}
              onClick={() => setShowPassword((p) => !p)}
              tabIndex={-1}
            >
              {showPassword ? <MdVisibilityOff size={18} /> : <MdVisibility size={18} />}
            </button>
          </div>

          <button type="submit" style={s.submitBtn} disabled={loading}>
            {loading ? 'Signing in…' : '🔐 Sign In'}
          </button>
        </form>
      </div>
    </div>
  )
}
