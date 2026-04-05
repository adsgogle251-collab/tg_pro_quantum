/** Circular spinner */
export function Spinner({ size = 32, color = '#00D9FF', style = {} }) {
  return (
    <div
      style={{
        width: size,
        height: size,
        border: `3px solid ${color}33`,
        borderTopColor: color,
        borderRadius: '50%',
        animation: 'spin 0.75s linear infinite',
        flexShrink: 0,
        ...style,
      }}
      role="status"
      aria-label="Loading"
    />
  )
}

/** Animated skeleton placeholder */
export function Skeleton({ width = '100%', height = 16, borderRadius = 6, style = {} }) {
  return (
    <div
      style={{
        width,
        height,
        borderRadius,
        background: 'linear-gradient(90deg, #252D4A 25%, #2e3756 50%, #252D4A 75%)',
        backgroundSize: '200% 100%',
        animation: 'shimmer 1.4s infinite',
        ...style,
      }}
      aria-hidden="true"
    />
  )
}

/** Full-page loading overlay */
export function LoadingOverlay({ message = 'Loading…', visible = true }) {
  if (!visible) return null
  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(10,14,39,0.85)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 18,
        zIndex: 9500,
        backdropFilter: 'blur(4px)',
      }}
      role="status"
    >
      <Spinner size={48} />
      <span style={{ color: '#9099B7', fontSize: 14, letterSpacing: 0.5 }}>{message}</span>
    </div>
  )
}
