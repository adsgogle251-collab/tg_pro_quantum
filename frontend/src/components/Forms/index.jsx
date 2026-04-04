import { useState } from 'react'
import theme from '../../styles/theme'

const inputBase = {
  background: theme.bgLight,
  border: `1px solid ${theme.bgLight}`,
  borderRadius: 8,
  color: theme.text,
  fontSize: 14,
  padding: '10px 14px',
  outline: 'none',
  width: '100%',
  transition: 'border-color 0.2s',
}

export function FormInput({ label, ...props }) {
  const [focused, setFocused] = useState(false)

  return (
    <label style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      {label && (
        <span style={{ fontSize: 13, color: theme.textMuted, fontWeight: 500 }}>{label}</span>
      )}
      <input
        {...props}
        style={{
          ...inputBase,
          borderColor: focused ? theme.primary : theme.bgLight,
          ...(props.style ?? {}),
        }}
        onFocus={(e) => { setFocused(true);  props.onFocus?.(e) }}
        onBlur={(e)  => { setFocused(false); props.onBlur?.(e)  }}
      />
    </label>
  )
}

export function FormSelect({ label, options = [], ...props }) {
  return (
    <label style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      {label && (
        <span style={{ fontSize: 13, color: theme.textMuted, fontWeight: 500 }}>{label}</span>
      )}
      <select
        {...props}
        style={{
          ...inputBase,
          cursor: 'pointer',
          ...(props.style ?? {}),
        }}
      >
        {options.map(({ value, label: lbl }) => (
          <option key={value} value={value} style={{ background: theme.bgMedium }}>
            {lbl}
          </option>
        ))}
      </select>
    </label>
  )
}

export function FormButton({ children, variant = 'primary', ...props }) {
  const colors = {
    primary:  { bg: theme.primary,    text: theme.bgDark },
    secondary:{ bg: theme.secondary,  text: theme.text   },
    danger:   { bg: theme.error,      text: theme.text   },
    ghost:    { bg: 'transparent',    text: theme.primary, border: `1px solid ${theme.primary}` },
  }
  const c = colors[variant] ?? colors.primary

  return (
    <button
      {...props}
      style={{
        background: c.bg,
        color: c.text,
        border: c.border ?? 'none',
        borderRadius: 8,
        padding: '10px 20px',
        fontSize: 14,
        fontWeight: 600,
        transition: 'opacity 0.2s',
        ...(props.style ?? {}),
      }}
      onMouseEnter={(e) => { e.currentTarget.style.opacity = '0.85' }}
      onMouseLeave={(e) => { e.currentTarget.style.opacity = '1'    }}
    >
      {children}
    </button>
  )
}
