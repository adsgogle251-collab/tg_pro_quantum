import { createContext, useContext, useState, useCallback } from 'react'

const ToastContext = createContext(null)

let nextId = 0

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])

  const addToast = useCallback((message, type = 'info') => {
    const id = ++nextId
    setToasts((prev) => {
      const updated = [...prev, { id, message, type }]
      return updated.length > 5 ? updated.slice(updated.length - 5) : updated
    })
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id))
    }, 4000)
  }, [])

  const removeToast = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  return (
    <ToastContext.Provider value={{ addToast }}>
      {children}
      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </ToastContext.Provider>
  )
}

export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used within ToastProvider')
  return ctx
}

const TOAST_COLORS = {
  success: { bg: '#00FF41', text: '#0A0E27', icon: '✓' },
  error:   { bg: '#FF006E', text: '#fff',    icon: '✕' },
  warning: { bg: '#FFB800', text: '#0A0E27', icon: '⚠' },
  info:    { bg: '#00D9FF', text: '#0A0E27', icon: 'ℹ' },
}

function ToastContainer({ toasts, onRemove }) {
  return (
    <div
      style={{
        position: 'fixed',
        top: 16,
        right: 16,
        zIndex: 9999,
        display: 'flex',
        flexDirection: 'column',
        gap: 10,
        pointerEvents: 'none',
      }}
    >
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onRemove={onRemove} />
      ))}
    </div>
  )
}

function ToastItem({ toast, onRemove }) {
  const colors = TOAST_COLORS[toast.type] ?? TOAST_COLORS.info

  return (
    <div
      className="toast-slide-in"
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        padding: '12px 16px',
        borderRadius: 10,
        background: '#1A1F3A',
        border: `1px solid ${colors.bg}44`,
        boxShadow: `0 4px 20px ${colors.bg}22`,
        minWidth: 280,
        maxWidth: 400,
        pointerEvents: 'all',
        cursor: 'pointer',
        animation: 'toastIn 0.3s ease forwards',
      }}
      onClick={() => onRemove(toast.id)}
      role="alert"
    >
      <span
        style={{
          width: 24,
          height: 24,
          borderRadius: '50%',
          background: colors.bg,
          color: colors.text,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 13,
          fontWeight: 700,
          flexShrink: 0,
        }}
      >
        {colors.icon}
      </span>
      <span style={{ fontSize: 13, color: '#E0E0FF', lineHeight: 1.4, flex: 1 }}>
        {toast.message}
      </span>
      <span style={{ fontSize: 16, color: '#9099B7', flexShrink: 0 }}>×</span>
    </div>
  )
}

export default ToastContext
