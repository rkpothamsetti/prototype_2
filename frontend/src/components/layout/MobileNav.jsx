import { LayoutDashboard, Upload, FileSearch, Map } from 'lucide-react'
import { NAV_ITEMS } from '../../constants'

const ICONS = { LayoutDashboard, Upload, FileSearch, Map }

export function MobileNav({ tab, setTab, pendingCount }) {
  return (
    <nav className="lg:hidden fixed bottom-0 inset-x-0 z-50 bg-white/95 backdrop-blur-lg border-t border-surface-border shadow-[0_-4px_16px_rgba(0,0,0,0.06)]">
      <div className="flex items-center justify-around px-2 py-2">
        {NAV_ITEMS.map((item) => {
          const Icon = ICONS[item.icon]
          const active = tab === item.id
          return (
            <button
              key={item.id}
              onClick={() => setTab(item.id)}
              className={`flex flex-col items-center gap-0.5 px-4 py-2 rounded-xl transition-all min-w-[72px] ${
                active ? 'text-brand-700 bg-green-50' : 'text-gray-400'
              }`}
            >
              <div className="relative">
                <Icon className="w-5 h-5" />
                {item.id === 'evidence' && pendingCount > 0 && (
                  <span className="absolute -top-1.5 -right-2 bg-brand-600 text-white text-[9px] font-bold w-4 h-4 rounded-full flex items-center justify-center">
                    {pendingCount > 9 ? '9+' : pendingCount}
                  </span>
                )}
              </div>
              <span className="text-[10px] font-medium capitalize">{item.label}</span>
            </button>
          )
        })}
      </div>
    </nav>
  )
}
