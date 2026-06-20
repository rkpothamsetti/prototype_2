import { Users } from 'lucide-react'
import { EmptyState } from '../ui/EmptyState'

export function RepeatOffenders({ offenders }) {
  const list = offenders || []

  if (!list.length) {
    return (
      <EmptyState
        icon={Users}
        title="No repeat offenders"
        description="Vehicles with multiple violations will appear here."
      />
    )
  }

  return (
    <>
      {/* Desktop table */}
      <div className="hidden md:block overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-slate-500 text-xs uppercase tracking-wide border-b border-surface-border">
              <th className="text-left py-3 font-medium">Plate</th>
              <th className="text-left py-3 font-medium">Total</th>
              <th className="text-left py-3 font-medium">Last 30d</th>
              <th className="text-left py-3 font-medium">Serious</th>
              <th className="text-left py-3 font-medium">Risk</th>
            </tr>
          </thead>
          <tbody>
            {list.map((o) => (
              <tr key={o.plate} className="border-b border-surface-border/50 hover:bg-surface-overlay/30 transition-colors">
                <td className="py-3 font-mono text-brand-900">{o.plate}</td>
                <td className="py-3 text-gray-700">{o.total_violations}</td>
                <td className="py-3 text-gray-700">{o.violations_last_30d}</td>
                <td className="py-3 text-gray-700">{o.serious_violations}</td>
                <td className="py-3">
                  <span
                    className={`font-semibold ${
                      o.risk_score > 10 ? 'text-red-600' : o.risk_score > 5 ? 'text-amber-600' : 'text-gray-500'
                    }`}
                  >
                    {o.risk_score}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Mobile cards */}
      <div className="md:hidden space-y-3">
        {list.map((o) => (
          <div key={o.plate} className="card-sm flex items-center justify-between">
            <div>
              <p className="font-mono font-medium text-brand-900">{o.plate}</p>
              <p className="text-xs text-slate-500 mt-1">
                {o.total_violations} total · {o.violations_last_30d} last 30d
              </p>
            </div>
            <div className="text-right">
              <p className={`text-lg font-bold ${o.risk_score > 10 ? 'text-red-600' : 'text-amber-600'}`}>
                {o.risk_score}
              </p>
              <p className="text-[10px] text-slate-500">risk score</p>
            </div>
          </div>
        ))}
      </div>
    </>
  )
}
