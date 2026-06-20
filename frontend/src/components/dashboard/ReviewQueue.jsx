import { motion } from 'framer-motion'
import { ChevronRight, Inbox } from 'lucide-react'
import { formatViolationTypes } from '../../constants'
import { annotatedUrl } from '../../api'
import { confidencePercent, timeAgo } from '../../utils/format'
import { PriorityBadge } from '../ui/StatusBadge'
import { EmptyState } from '../ui/EmptyState'

export function ReviewQueue({ items, onSelect, onViewAll }) {
  const pending = (items || []).filter(
    (e) => e.review_status === 'pending_review' && e.violation_type !== 'none',
  ).slice(0, 6)

  if (!pending.length) {
    return (
      <EmptyState
        icon={Inbox}
        title="Queue clear"
        description="No violations pending officer review."
      />
    )
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs text-slate-500">{pending.length} pending</span>
        <button onClick={onViewAll} className="text-xs text-brand-700 hover:text-brand-800 font-medium flex items-center gap-0.5">
          View all <ChevronRight className="w-3 h-3" />
        </button>
      </div>
      {pending.map((ev, i) => (
        <motion.button
          key={ev.evidence_id}
          initial={{ opacity: 0, x: -8 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: i * 0.05 }}
          onClick={() => onSelect(ev)}
          className="w-full flex items-center gap-3 p-3 rounded-xl bg-green-50 border border-surface-border hover:border-brand-500 hover:bg-green-100/60 transition-all text-left group"
        >
          <div className="w-12 h-12 rounded-lg bg-surface border border-surface-border overflow-hidden shrink-0">
            {ev.annotated_path ? (
              <img
                src={annotatedUrl(ev.annotated_path)}
                alt=""
                className="w-full h-full object-cover"
                onError={(e) => { e.target.style.display = 'none' }}
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center text-slate-600 text-[10px]">N/A</div>
            )}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-sm font-medium text-brand-900 truncate">
                {formatViolationTypes(ev.violation_type)}
              </span>
              <PriorityBadge violationType={ev.violation_type} />
            </div>
            <p className="text-xs text-slate-500 truncate mt-0.5">
              {ev.plate_normalized || 'No plate'} · {ev.camera_id}
            </p>
          </div>
          <div className="text-right shrink-0">
            <p className="text-xs font-mono text-brand-700 font-semibold">{confidencePercent(ev.confidence)}</p>
            <p className="text-[10px] text-slate-600">{timeAgo(ev.created_at)}</p>
          </div>
          <ChevronRight className="w-4 h-4 text-slate-600 group-hover:text-brand-400 shrink-0" />
        </motion.button>
      ))}
    </div>
  )
}
