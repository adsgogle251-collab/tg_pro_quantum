import {
  LineChart as ReLineChart,
  BarChart as ReBarChart,
  PieChart as RePieChart,
  Line,
  Bar,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import theme from '../../styles/theme'

const CHART_COLORS = [
  theme.primary,
  theme.secondary,
  theme.accent,
  theme.success,
  theme.error,
]

const tooltipStyle = {
  contentStyle: {
    background: theme.bgMedium,
    border: `1px solid ${theme.bgLight}`,
    borderRadius: 8,
    color: theme.text,
    fontSize: 12,
  },
  labelStyle: { color: theme.textMuted },
}

export function LineChart({ data, xKey = 'name', lines = [] }) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <ReLineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke={theme.bgLight} />
        <XAxis dataKey={xKey} stroke={theme.textMuted} tick={{ fontSize: 12 }} />
        <YAxis stroke={theme.textMuted} tick={{ fontSize: 12 }} />
        <Tooltip {...tooltipStyle} />
        <Legend wrapperStyle={{ fontSize: 12, color: theme.textMuted }} />
        {lines.map((key, i) => (
          <Line
            key={key}
            type="monotone"
            dataKey={key}
            stroke={CHART_COLORS[i % CHART_COLORS.length]}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 5 }}
          />
        ))}
      </ReLineChart>
    </ResponsiveContainer>
  )
}

export function BarChart({ data, xKey = 'name', bars = [] }) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <ReBarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke={theme.bgLight} />
        <XAxis dataKey={xKey} stroke={theme.textMuted} tick={{ fontSize: 12 }} />
        <YAxis stroke={theme.textMuted} tick={{ fontSize: 12 }} />
        <Tooltip {...tooltipStyle} />
        <Legend wrapperStyle={{ fontSize: 12, color: theme.textMuted }} />
        {bars.map((key, i) => (
          <Bar key={key} dataKey={key} fill={CHART_COLORS[i % CHART_COLORS.length]} radius={[4, 4, 0, 0]} />
        ))}
      </ReBarChart>
    </ResponsiveContainer>
  )
}

export function PieChart({ data }) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <RePieChart>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          innerRadius={60}
          outerRadius={100}
          paddingAngle={3}
          dataKey="value"
        >
          {data.map((_, i) => (
            <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
          ))}
        </Pie>
        <Tooltip {...tooltipStyle} />
        <Legend wrapperStyle={{ fontSize: 12, color: theme.textMuted }} />
      </RePieChart>
    </ResponsiveContainer>
  )
}
