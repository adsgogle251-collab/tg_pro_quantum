import { useNavigate } from 'react-router-dom'
import { useTheme } from '../context/ThemeContext'

export default function NotFound() {
  const navigate = useNavigate()
  const { theme } = useTheme()

  return (
    <div style={{
      minHeight: '100vh',
      background: theme.bgDark,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: 24,
    }}>
      <div style={{ fontSize: 96, marginBottom: 8, userSelect: 'none' }}>🔍</div>
      <h1 style={{ fontSize: 72, fontWeight: 900, color: theme.primary, margin: 0 }}>404</h1>
      <h2 style={{ fontSize: 24, fontWeight: 700, color: theme.text, margin: '12px 0 8px' }}>
        Page Not Found
      </h2>
      <p style={{ fontSize: 14, color: theme.textMuted, marginBottom: 32, textAlign: 'center', maxWidth: 360 }}>
        The page you are looking for doesn't exist or has been moved.
      </p>
      <div style={{ display: 'flex', gap: 12 }}>
        <button
          onClick={() => navigate(-1)}
          style={{
            padding: '10px 24px',
            background: 'transparent',
            color: theme.text,
            border: `1px solid ${theme.bgLight}`,
            borderRadius: 8,
            fontSize: 14,
            fontWeight: 600,
            cursor: 'pointer',
          }}
        >
          ← Go Back
        </button>
        <button
          onClick={() => navigate('/')}
          style={{
            padding: '10px 24px',
            background: theme.primary,
            color: '#000',
            border: 'none',
            borderRadius: 8,
            fontSize: 14,
            fontWeight: 700,
            cursor: 'pointer',
          }}
        >
          🏠 Dashboard
        </button>
      </div>
    </div>
  )
}
