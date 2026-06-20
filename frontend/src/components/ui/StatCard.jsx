import { TrendingDown, TrendingUp } from 'lucide-react'
import { CountUp } from './CountUp'

export function StatCard({ label, value, sub, trend, variant = 'default', alert }) {
  const cls =
    variant === 'hero'
      ? 'card-hero'
      : alert
        ? 'card-sm border-red-300 bg-red-50'
        : 'card-sm'

  return (
    <div className={`${cls} animate-slide-up`}>
      <p className="text-gray-500 text-xs font-medium uppercase tracking-wide">{label}</p>
      <p className={`font-semibold mt-2 text-brand-900 ${variant === 'hero' ? 'text-4xl' : 'text-2xl'} ${alert ? 'text-red-600' : ''}`}>
        {typeof value === 'number' ? <CountUp value={value} /> : value}
      </p>
      {(sub || trend) && (
        <div className="flex items-center gap-2 mt-2">
          {trend != null && (
            <span className={`flex items-center gap-0.5 text-xs font-medium ${trend >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {trend >= 0 ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
              {Math.abs(trend)}%
            </span>
          )}
          {sub && <p className="text-xs text-gray-500">{sub}</p>}
        </div>
      )}
    </div>
  )
}
