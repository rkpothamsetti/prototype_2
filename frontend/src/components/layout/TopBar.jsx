import { Calendar, RefreshCw } from 'lucide-react'
import { CITY } from '../../config/city'
import { Logo } from '../ui/Logo'

const TAB_TITLES = {
  dashboard: { title: 'City Operations', sub: `${CITY.displayName} (${CITY.name}) enforcement overview` },
  mobility: { title: 'Mobility Intelligence', sub: 'Congestion × violations — deployment priorities' },
  upload: { title: 'Upload Media', sub: 'Analyze traffic footage' },
  evidence: { title: 'Evidence Review', sub: 'Officer decision queue' },
}

export function TopBar({ tab, onRefresh, lastUpdated, loading }) {
  const meta = TAB_TITLES[tab] || TAB_TITLES.dashboard

  return (
    <header className="sticky top-0 z-40 bg-white/90 backdrop-blur-lg border-b border-surface-border shadow-sm">
      <div className="px-4 lg:px-8 py-4 flex items-center justify-between gap-4">
        <div className="min-w-0">
          <div className="lg:hidden flex items-center gap-2 mb-1">
            <Logo size="sm" showText />
          </div>
          <h2 className="text-lg lg:text-xl font-semibold text-brand-900 truncate">{meta.title}</h2>
          <p className="text-xs text-gray-500 truncate hidden sm:block">{meta.sub}</p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <div className="hidden md:flex items-center gap-2 text-xs text-gray-600 bg-green-50 border border-surface-border rounded-xl px-3 py-2">
            <Calendar className="w-3.5 h-3.5 text-brand-600" />
            <span>Last 7 days</span>
          </div>
          <button
            onClick={onRefresh}
            disabled={loading}
            className="btn-ghost flex items-center gap-1.5 text-brand-700"
            title="Refresh data"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            <span className="hidden sm:inline">Refresh</span>
          </button>
          {lastUpdated && (
            <span className="text-[10px] text-gray-400 hidden lg:inline">
              Updated {lastUpdated}
            </span>
          )}
        </div>
      </div>
    </header>
  )
}
