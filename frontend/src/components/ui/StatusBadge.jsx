import { REVIEW_STATUS, VIOLATION_SEVERITY } from '../../constants'
import { PRIORITY_COLORS } from '../../constants'

export function StatusBadge({ status }) {
  const cfg = REVIEW_STATUS[status] || { label: status, color: 'bg-slate-500/20 text-slate-400 border-slate-500/30' }
  return (
    <span className={`badge border ${cfg.color}`}>
      {cfg.label}
    </span>
  )
}

export function PriorityBadge({ violationType }) {
  const severity = VIOLATION_SEVERITY[violationType] || 'low'
  const color = PRIORITY_COLORS[severity] || PRIORITY_COLORS.low
  return (
    <span className={`badge border uppercase text-[10px] tracking-wider ${color}`}>
      {severity}
    </span>
  )
}
