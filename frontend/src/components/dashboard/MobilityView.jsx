import { motion } from 'framer-motion'
import { MapPin, TrendingUp, Users, Zap } from 'lucide-react'
import { CONGESTION_COLORS, CONGESTION_LABELS } from '../../constants'
import { StatCard } from '../ui/StatCard'
import { ChartSkeleton, StatCardSkeleton } from '../ui/Skeleton'

export function MobilityView({ mobility, analytics, loading }) {
  if (loading || !mobility) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <StatCardSkeleton key={i} />
          ))}
        </div>
        <ChartSkeleton />
      </div>
    )
  }

  const topZones = mobility.zones?.slice(0, 5) || []
  const peakHours = mobility.peak_hours?.filter((h) => h.violations > 0 || h.congestion_index > 0.3).slice(0, 8) || []

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-brand-900">Mobility Intelligence</h2>
        <p className="text-sm text-gray-500 mt-1">
          Congestion × violations — where to deploy officers in Bengaluru
        </p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          variant="hero"
          label="Correlation"
          value={`${(mobility.congestion_violation_correlation * 100).toFixed(0)}%`}
          sub="congestion ↔ violations"
        />
        <StatCard
          label="Officer Load Reduced"
          value={`${(mobility.officer_load_reduction_pct * 100).toFixed(0)}%`}
          sub="auto-cleared tier"
        />
        <StatCard label="Pending Review" value={mobility.pending_review_count} sub="in queue" />
        <StatCard
          label="Avg Processing"
          value={`${Math.round(mobility.avg_processing_ms)}ms`}
          sub="per job"
        />
      </div>

      <div className="grid lg:grid-cols-2 gap-4">
        <div className="card">
          <h3 className="font-semibold text-brand-900 mb-4 flex items-center gap-2">
            <MapPin className="w-4 h-4" /> Deployment Priority Zones
          </h3>
          <div className="space-y-3">
            {topZones.length === 0 ? (
              <p className="text-sm text-gray-500">Upload traffic media to populate zone intelligence.</p>
            ) : (
              topZones.map((zone) => (
                <div
                  key={zone.camera_id}
                  className="border border-surface-border rounded-xl p-3 bg-white"
                >
                  <div className="flex justify-between items-start gap-2">
                    <div>
                      <p className="font-semibold text-sm">{zone.zone_name}</p>
                      <p className="text-xs text-gray-500">{zone.camera_id}</p>
                    </div>
                    <span
                      className="text-xs font-bold px-2 py-0.5 rounded-full text-white"
                      style={{ backgroundColor: CONGESTION_COLORS[zone.congestion_avg] || '#6b7280' }}
                    >
                      {CONGESTION_LABELS[zone.congestion_avg] || zone.congestion_avg}
                    </span>
                  </div>
                  <div className="mt-2 flex gap-4 text-xs text-gray-600">
                    <span>{zone.violations_total} violations</span>
                    <span>Top: {zone.top_violation?.replace(/_/g, ' ')}</span>
                    <span>Priority: {(zone.priority_score * 100).toFixed(0)}%</span>
                  </div>
                  <p className="text-xs text-brand-700 mt-2 font-medium">{zone.deploy_recommendation}</p>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="card">
          <h3 className="font-semibold text-brand-900 mb-4 flex items-center gap-2">
            <TrendingUp className="w-4 h-4" /> Peak Hours
          </h3>
          <div className="space-y-2 max-h-80 overflow-y-auto">
            {peakHours.length === 0 ? (
              <p className="text-sm text-gray-500">Peak patterns appear after multiple uploads.</p>
            ) : (
              peakHours.map((h) => (
                <div key={h.hour} className="flex items-center gap-3 text-sm">
                  <span className="w-14 text-gray-500">{String(h.hour).padStart(2, '0')}:00</span>
                  <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-brand-500 rounded-full"
                      style={{ width: `${Math.min(100, h.violations * 8)}%` }}
                    />
                  </div>
                  <span className="text-xs w-20 text-right">{h.violations} viol.</span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {analytics?.congestion_summary && Object.keys(analytics.congestion_summary).length > 0 && (
        <div className="card">
          <h3 className="font-semibold text-brand-900 mb-3 flex items-center gap-2">
            <Zap className="w-4 h-4" /> Congestion Distribution
          </h3>
          <div className="flex flex-wrap gap-3">
            {Object.entries(analytics.congestion_summary).map(([level, count]) => (
              <div
                key={level}
                className="px-4 py-2 rounded-xl border text-sm font-medium"
                style={{
                  borderColor: CONGESTION_COLORS[level],
                  color: CONGESTION_COLORS[level],
                }}
              >
                {CONGESTION_LABELS[level]}: {count}
              </div>
            ))}
          </div>
        </div>
      )}
    </motion.div>
  )
}
