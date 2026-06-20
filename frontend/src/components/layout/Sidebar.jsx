import { LayoutDashboard, Upload, FileSearch, Circle, Map } from 'lucide-react'
import { NAV_ITEMS, APP_NAME } from '../../constants'
import { CITY } from '../../config/city'
import { Logo } from '../ui/Logo'

const ICONS = { LayoutDashboard, Upload, FileSearch, Map }

export function Sidebar({ tab, setTab, pendingCount, backendOk, modelsReady }) {
  return (
    <aside className="hidden lg:flex flex-col w-64 shrink-0 border-r border-surface-border bg-white h-screen sticky top-0 shadow-sm">
      <div className="p-5 border-b border-surface-border bg-gradient-to-b from-green-50 to-white">
        <div className="flex items-center gap-3">
          <Logo size="lg" />
          <div>
            <h1 className="font-bold text-brand-900 text-sm leading-tight">{APP_NAME}</h1>
            <p className="text-[11px] text-gray-500">Enforcement Platform</p>
          </div>
        </div>
      </div>

      <nav className="flex-1 p-3 space-y-1">
        {NAV_ITEMS.map((item) => {
          const Icon = ICONS[item.icon]
          const active = tab === item.id
          return (
            <button
              key={item.id}
              onClick={() => setTab(item.id)}
              className={`nav-item w-full ${active ? 'nav-item-active' : ''}`}
            >
              <Icon className="w-4 h-4" />
              <span>{item.label}</span>
              {item.id === 'evidence' && pendingCount > 0 && (
                <span className="ml-auto bg-brand-600 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full min-w-[18px]">
                  {pendingCount}
                </span>
              )}
            </button>
          )
        })}
      </nav>

      <div className="p-4 border-t border-surface-border bg-green-50/50">
        <div className="flex items-center gap-2 text-xs text-gray-600">
          <Circle
            className={`w-2 h-2 fill-current ${
              backendOk && modelsReady ? 'text-green-500' : backendOk ? 'text-amber-500' : 'text-red-500'
            }`}
          />
          <span>
            {backendOk && modelsReady
              ? 'System online'
              : backendOk
                ? 'Loading AI models…'
                : backendOk === false
                  ? 'Backend offline'
                  : 'Connecting…'}
          </span>
        </div>
        <p className="text-[10px] text-gray-500 mt-1">{CITY.displayName} · {CITY.zone}</p>
      </div>
    </aside>
  )
}
