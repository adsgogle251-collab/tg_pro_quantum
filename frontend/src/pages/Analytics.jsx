import { useState } from 'react'
import { MdDownload } from 'react-icons/md'
import { LineChart, BarChart, PieChart } from '../components/Charts'
import { FormButton, FormSelect } from '../components/Forms'
import theme from '../styles/theme'

const LINE_DATA = [
  { name: 'Jan', sent: 3200, delivered: 3050 },
  { name: 'Feb', sent: 4100, delivered: 3900 },
  { name: 'Mar', sent: 3800, delivered: 3620 },
  { name: 'Apr', sent: 5200, delivered: 4980 },
  { name: 'May', sent: 4700, delivered: 4500 },
  { name: 'Jun', sent: 6100, delivered: 5900 },
]

const BAR_DATA = [
  { name: 'Summer Sale',   sent: 4200, failed: 130 },
  { name: 'Promo Q4',      sent: 8000, failed: 210 },
  { name: 'Newsletter #5', sent: 1100, failed: 40  },
  { name: 'Re-engagement', sent: 2600, failed: 90  },
]

const PIE_DATA = [
  { name: 'Delivered', value: 68 },
  { name: 'Pending',   value: 18 },
  { name: 'Failed',    value: 9  },
  { name: 'Bounced',   value: 5  },
]

const RANGE_OPTIONS = [
  { value: '7d',  label: 'Last 7 days'  },
  { value: '30d', label: 'Last 30 days' },
  { value: '90d', label: 'Last 90 days' },
]

function ChartCard({ title, children }) {
  return (
    <div style={{ background: theme.bgMedium, border: `1px solid ${theme.bgLight}`, borderRadius: 12, padding: 24 }}>
      <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16, color: theme.text }}>{title}</h3>
      {children}
    </div>
  )
}

export default function Analytics() {
  const [range, setRange] = useState('30d')

  return (
    <div className="fade-in" style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 20 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
        <h2 style={{ fontSize: 16, fontWeight: 600 }}>Analytics</h2>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <FormSelect value={range} onChange={(e) => setRange(e.target.value)} options={RANGE_OPTIONS} style={{ width: 150 }} />
          <FormButton variant="ghost">
            <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <MdDownload size={16} /> Export
            </span>
          </FormButton>
        </div>
      </div>

      <ChartCard title="Messages Over Time">
        <LineChart data={LINE_DATA} xKey="name" lines={['sent', 'delivered']} />
      </ChartCard>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(380px, 1fr))', gap: 20 }}>
        <ChartCard title="Campaigns Comparison">
          <BarChart data={BAR_DATA} xKey="name" bars={['sent', 'failed']} />
        </ChartCard>
        <ChartCard title="Message Status Distribution">
          <PieChart data={PIE_DATA} />
        </ChartCard>
      </div>
    </div>
  )
}
