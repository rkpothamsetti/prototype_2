import {
  Area,
  AreaChart,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { VIOLATION_COLORS, VIOLATION_LABELS } from '../../constants'
import { THEME } from '../../config/theme'
import { formatDate } from '../../utils/format'

const tooltipStyle = {
  background: THEME.tooltipBg,
  border: `1px solid ${THEME.tooltipBorder}`,
  borderRadius: '12px',
  fontSize: '12px',
  color: THEME.text,
}

export function ViolationsTrendChart({ dailyTrends }) {
  const data = (dailyTrends || []).map((d) => ({
    date: formatDate(d.date),
    count: d.count,
  }))

  if (!data.length) {
    return (
      <div className="flex items-center justify-center h-full text-slate-500 text-sm">
        No trend data yet
      </div>
    )
  }

  return (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
        <defs>
          <linearGradient id="violationGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={THEME.chartPrimary} stopOpacity={0.45} />
            <stop offset="100%" stopColor={THEME.chartPrimary} stopOpacity={0} />
          </linearGradient>
        </defs>
        <XAxis dataKey="date" tick={{ fill: '#6b7280', fontSize: 11 }} axisLine={false} tickLine={false} />
        <YAxis tick={{ fill: '#6b7280', fontSize: 11 }} axisLine={false} tickLine={false} allowDecimals={false} />
        <Tooltip contentStyle={tooltipStyle} />
        <Area
          type="monotone"
          dataKey="count"
          stroke={THEME.chartPrimary}
          strokeWidth={2}
          fill="url(#violationGradient)"
          animationDuration={800}
          animationEasing="ease-out"
        />
      </AreaChart>
    </ResponsiveContainer>
  )
}

export function ViolationDonutChart({ byType }) {
  const data = Object.entries(byType || {})
    .filter(([k]) => k !== 'none')
    .map(([type, count]) => ({
      name: VIOLATION_LABELS[type] || type,
      value: count,
      color: VIOLATION_COLORS[type] || '#64748b',
    }))
    .sort((a, b) => b.value - a.value)

  const total = data.reduce((s, d) => s + d.value, 0)

  if (!data.length) {
    return (
      <div className="flex items-center justify-center h-full text-slate-500 text-sm">
        No violations recorded
      </div>
    )
  }

  return (
    <div className="flex items-center gap-4 h-full">
      <div className="w-1/2 h-full relative">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius="55%"
              outerRadius="80%"
              paddingAngle={3}
              dataKey="value"
              animationDuration={800}
            >
              {data.map((entry, i) => (
                <Cell key={i} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip contentStyle={tooltipStyle} />
          </PieChart>
        </ResponsiveContainer>
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="text-center">
            <p className="text-2xl font-bold text-brand-900">{total}</p>
            <p className="text-[10px] text-gray-500 uppercase">Total</p>
          </div>
        </div>
      </div>
      <div className="flex-1 space-y-2 overflow-y-auto max-h-[220px]">
        {data.map((d) => (
          <div key={d.name} className="flex items-center gap-2 text-xs">
            <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: d.color }} />
            <span className="text-gray-700 flex-1 truncate">{d.name}</span>
            <span className="text-gray-500 font-mono">{d.value}</span>
            <span className="text-gray-400 w-8 text-right">{total ? Math.round((d.value / total) * 100) : 0}%</span>
          </div>
        ))}
      </div>
    </div>
  )
}
