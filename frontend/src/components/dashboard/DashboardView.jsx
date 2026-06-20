import { motion } from 'framer-motion'
import { AlertTriangle, ArrowRight } from 'lucide-react'
import { StatCard } from '../ui/StatCard'
import { ChartSkeleton, StatCardSkeleton } from '../ui/Skeleton'
import { ViolationsTrendChart, ViolationDonutChart } from './Charts'
import { HotspotMap } from './HotspotMap'
import { ReviewQueue } from './ReviewQueue'
import { RepeatOffenders } from './RepeatOffenders'
import { formatLatency, formatThroughput, isLatencyDegraded } from '../../utils/format'

export function DashboardView({ analytics, metrics, mobility, feedback, evidence, loading, onReviewSelect, onGoEvidence }) {
  if (loading || !analytics) {
    return (
      <div className="space-y-6 animate-fade-in">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => <StatCardSkeleton key={i} />)}
        </div>
        <div className="grid lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2"><ChartSkeleton /></div>
          <ChartSkeleton />
        </div>
      </div>
    )
  }

  const pending = analytics.by_review_status?.pending_review || 0
  const confirmed = analytics.by_review_status?.confirmed || 0
  const autoCleared = analytics.by_review_status?.auto_cleared || 0
  const fastTrack = analytics.by_review_tier?.fast_track || 0
  const gridlockZones = Object.entries(analytics.congestion_summary || {}).find(([k]) => k === 'gridlock')?.[1] || 0
  const p95 = metrics?.latency_p95_ms ?? 0
  const degraded = isLatencyDegraded(p95)

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="space-y-6"
    >
      {/* Pending review CTA */}
      {pending > 0 && (
        <button
          onClick={onGoEvidence}
          className="w-full card-sm flex items-center justify-between gap-4 border-amber-300 bg-amber-50 hover:bg-amber-100/80 transition-colors group"
        >
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-amber-100 flex items-center justify-center">
              <AlertTriangle className="w-5 h-5 text-amber-600" />
            </div>
            <div className="text-left">
              <p className="font-semibold text-amber-800">{pending} violation{pending !== 1 ? 's' : ''} awaiting review</p>
              <p className="text-xs text-slate-500">Officers must confirm or reject before enforcement</p>
            </div>
          </div>
          <ArrowRight className="w-5 h-5 text-amber-600 group-hover:translate-x-1 transition-transform" />
        </button>
      )}

      {/* KPI row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          variant="hero"
          label="Violations"
          value={analytics.total_violations}
          sub="all time in system"
        />
        <StatCard
          label="Congestion Alerts"
          value={gridlockZones}
          sub="gridlock snapshots"
          alert={gridlockZones > 0}
        />
        <StatCard
          label="Pending Review"
          value={pending}
          sub={fastTrack > 0 ? `${fastTrack} fast-track` : pending > 0 ? 'needs action' : 'queue clear'}
          alert={pending > 5}
        />
        <StatCard
          label="Auto-Cleared"
          value={autoCleared}
          sub={`${((analytics.officer_load_reduction_pct || 0) * 100).toFixed(0)}% officer load saved`}
        />
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="card-sm py-3">
          <p className="text-[10px] text-gray-500 uppercase">Confirmed</p>
          <p className="text-lg font-semibold mt-1">{confirmed}</p>
        </div>
        <div className="card-sm py-3">
          <p className="text-[10px] text-gray-500 uppercase">Mobility Correlation</p>
          <p className="text-lg font-semibold mt-1">
            {mobility ? `${(mobility.congestion_violation_correlation * 100).toFixed(0)}%` : '—'}
          </p>
        </div>
        <div className="card-sm py-3">
          <p className="text-[10px] text-gray-500 uppercase">Feedback Queue</p>
          <p className="text-lg font-semibold mt-1">{feedback?.pending_retrain ?? 0}</p>
        </div>
        <div className="card-sm py-3">
          <p className="text-[10px] text-gray-500 uppercase">p95 Latency</p>
          <p className={`text-lg font-semibold mt-1 ${degraded ? 'text-red-600' : ''}`}>
            {formatLatency(p95)}
          </p>
        </div>
      </div>

      {/* Charts row */}
      <div className="grid lg:grid-cols-3 gap-4">
        <div className="card lg:col-span-2 h-80 flex flex-col">
          <h3 className="font-semibold text-brand-900 mb-4">Violations Over Time</h3>
          <div className="flex-1 min-h-0">
            <ViolationsTrendChart dailyTrends={analytics.daily_trends} />
          </div>
        </div>
        <div className="card h-80 flex flex-col">
          <h3 className="font-semibold text-brand-900 mb-4">By Violation Type</h3>
          <div className="flex-1 min-h-0">
            <ViolationDonutChart byType={analytics.by_type} />
          </div>
        </div>
      </div>

      {/* Map + Review queue */}
      <div className="grid lg:grid-cols-2 gap-4">
        <div className="card flex flex-col">
          <h3 className="font-semibold text-brand-900 mb-4">Violation Hotspots</h3>
          <HotspotMap hotspots={analytics.hotspots} />
        </div>
        <div className="card flex flex-col max-h-[400px]">
          <h3 className="font-semibold text-brand-900 mb-4">Officer Review Queue</h3>
          <div className="flex-1 overflow-y-auto min-h-0">
            <ReviewQueue
              items={evidence}
              onSelect={onReviewSelect}
              onViewAll={onGoEvidence}
            />
          </div>
        </div>
      </div>

      {/* Repeat offenders */}
      <div className="card">
        <h3 className="font-semibold text-brand-900 mb-4">Repeat Offenders</h3>
        <RepeatOffenders offenders={analytics.repeat_offenders} />
      </div>
    </motion.div>
  )
}
