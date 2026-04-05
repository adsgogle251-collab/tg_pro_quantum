import theme from '../../styles/theme'

export function StatCard({ title, value, icon: Icon, color, change }) {
  const isPositive = change >= 0

  return (
    <div
      className="fade-in"
      style={{
        background: theme.bgMedium,
        border: `1px solid ${theme.bgLight}`,
        borderRadius: 12,
        padding: '20px 24px',
        display: 'flex',
        flexDirection: 'column',
        gap: 12,
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* accent glow */}
      <div
        style={{
          position: 'absolute',
          top: -20,
          right: -20,
          width: 80,
          height: 80,
          borderRadius: '50%',
          background: `${color ?? theme.primary}22`,
          filter: 'blur(20px)',
        }}
      />
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <span style={{ fontSize: 13, color: theme.textMuted, fontWeight: 500 }}>{title}</span>
        {Icon && (
          <span style={{ color: color ?? theme.primary, fontSize: 22 }}>
            <Icon />
          </span>
        )}
      </div>
      <div style={{ fontSize: 28, fontWeight: 700, color: theme.text }}>{value}</div>
      {change !== undefined && (
        <div style={{ fontSize: 12, color: isPositive ? theme.success : theme.error }}>
          {isPositive ? '▲' : '▼'} {Math.abs(change)}% vs last period
        </div>
      )}
    </div>
  )
}
