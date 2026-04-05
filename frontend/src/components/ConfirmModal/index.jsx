import { useState } from 'react'

export default function ConfirmModal({
  isOpen,
  onConfirm,
  onCancel,
  title = 'Confirm Action',
  message = 'Are you sure you want to proceed?',
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  requireConfirmCheckbox = false,
}) {
  const [checked, setChecked] = useState(false)

  if (!isOpen) return null

  const canConfirm = !requireConfirmCheckbox || checked

  const handleConfirm = () => {
    if (canConfirm) {
      setChecked(false)
      onConfirm()
    }
  }

  const handleCancel = () => {
    setChecked(false)
    onCancel()
  }

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.65)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 9000,
        backdropFilter: 'blur(4px)',
      }}
      onClick={handleCancel}
    >
      <div
        style={{
          background: '#1A1F3A',
          border: '1px solid #252D4A',
          borderRadius: 14,
          padding: '28px 32px',
          maxWidth: 460,
          width: '90%',
          animation: 'fadeIn 0.2s ease forwards',
          boxShadow: '0 20px 60px rgba(0,0,0,0.5)',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Icon */}
        <div style={{ textAlign: 'center', marginBottom: 16 }}>
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: 52,
              height: 52,
              borderRadius: '50%',
              background: '#FF006E22',
              fontSize: 24,
            }}
          >
            ⚠️
          </span>
        </div>

        {/* Title */}
        <h3
          style={{
            textAlign: 'center',
            fontSize: 18,
            fontWeight: 700,
            color: '#E0E0FF',
            marginBottom: 10,
          }}
        >
          {title}
        </h3>

        {/* Message */}
        <p
          style={{
            textAlign: 'center',
            fontSize: 14,
            color: '#9099B7',
            lineHeight: 1.6,
            marginBottom: requireConfirmCheckbox ? 20 : 28,
          }}
        >
          {message}
        </p>

        {/* Checkbox */}
        {requireConfirmCheckbox && (
          <label
            style={{
              display: 'flex',
              alignItems: 'flex-start',
              gap: 10,
              marginBottom: 24,
              cursor: 'pointer',
              background: '#252D4A',
              borderRadius: 8,
              padding: '12px 14px',
            }}
          >
            <input
              type="checkbox"
              checked={checked}
              onChange={(e) => setChecked(e.target.checked)}
              style={{ marginTop: 2, accentColor: '#FF006E', flexShrink: 0 }}
            />
            <span style={{ fontSize: 13, color: '#E0E0FF', lineHeight: 1.5 }}>
              I understand this action is irreversible
            </span>
          </label>
        )}

        {/* Buttons */}
        <div style={{ display: 'flex', gap: 12 }}>
          <button
            onClick={handleCancel}
            style={{
              flex: 1,
              padding: '11px 0',
              borderRadius: 8,
              border: '1px solid #252D4A',
              background: 'transparent',
              color: '#9099B7',
              fontSize: 14,
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'border-color 0.2s, color 0.2s',
            }}
            onMouseEnter={(e) => { e.currentTarget.style.borderColor = '#9099B7'; e.currentTarget.style.color = '#E0E0FF' }}
            onMouseLeave={(e) => { e.currentTarget.style.borderColor = '#252D4A'; e.currentTarget.style.color = '#9099B7' }}
          >
            {cancelText}
          </button>
          <button
            onClick={handleConfirm}
            disabled={!canConfirm}
            style={{
              flex: 1,
              padding: '11px 0',
              borderRadius: 8,
              border: 'none',
              background: canConfirm ? '#FF006E' : '#FF006E44',
              color: '#fff',
              fontSize: 14,
              fontWeight: 600,
              cursor: canConfirm ? 'pointer' : 'not-allowed',
              transition: 'opacity 0.2s',
            }}
            onMouseEnter={(e) => { if (canConfirm) e.currentTarget.style.opacity = '0.85' }}
            onMouseLeave={(e) => { e.currentTarget.style.opacity = '1' }}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  )
}
