import { Component } from 'react'
import theme from '../styles/theme'

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, info) {
    console.error('ErrorBoundary caught:', error, info)
  }

  render() {
    if (!this.state.hasError) return this.props.children

    return (
      <div style={{
        minHeight: '100vh',
        background: theme.bgDark,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 24,
        color: theme.text,
      }}>
        <div style={{ fontSize: 64, marginBottom: 16 }}>💥</div>
        <h1 style={{ fontSize: 28, fontWeight: 800, color: theme.error, marginBottom: 8 }}>
          Something went wrong
        </h1>
        <p style={{ fontSize: 14, color: theme.textMuted, marginBottom: 24, maxWidth: 480, textAlign: 'center' }}>
          An unexpected error occurred. Please refresh the page or contact support.
        </p>
        <pre style={{
          background: theme.bgMedium,
          border: `1px solid ${theme.bgLight}`,
          borderRadius: 8,
          padding: '12px 16px',
          fontSize: 12,
          color: theme.error,
          maxWidth: 600,
          overflowX: 'auto',
          marginBottom: 24,
        }}>
          {this.state.error?.message ?? 'Unknown error'}
        </pre>
        <button
          onClick={() => window.location.reload()}
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
          🔄 Reload Page
        </button>
      </div>
    )
  }
}
