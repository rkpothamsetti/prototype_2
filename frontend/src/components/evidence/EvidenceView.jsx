import { useEffect, useMemo, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Search, FileSearch, ImageOff, Receipt } from 'lucide-react'
import { annotatedUrl } from '../../api'
import { formatViolationTypes, primaryViolationType, VIOLATION_LABELS } from '../../constants'
import { confidencePercent, formatDateTime } from '../../utils/format'
import { StatusBadge, PriorityBadge } from '../ui/StatusBadge'
import { EmptyState } from '../ui/EmptyState'
import { ListSkeleton } from '../ui/Skeleton'
import { ChallanReceipt } from '../challan/ChallanReceipt'

const STATUS_CHIPS = [
  { id: '', label: 'All' },
  { id: 'pending_review', label: 'Pending' },
  { id: 'confirmed', label: 'Confirmed' },
  { id: 'rejected', label: 'Rejected' },
  { id: 'auto_cleared', label: 'Cleared' },
]

export function EvidenceView({
  evidence,
  loading,
  filters,
  setFilters,
  onRefresh,
  onReview,
  onExportChallan,
  preselectedId,
}) {
  const [selected, setSelected] = useState(null)
  const [imgError, setImgError] = useState(false)
  const [exportMsg, setExportMsg] = useState('')
  const [challanReceipt, setChallanReceipt] = useState(null)
  const [exportingChallan, setExportingChallan] = useState(false)

  useEffect(() => {
    if (preselectedId && evidence?.length) {
      const found = evidence.find((e) => e.evidence_id === preselectedId)
      if (found) setSelected(found)
    }
  }, [preselectedId, evidence])

  // Keep detail pane in sync after Confirm/Reject refreshes the list
  useEffect(() => {
    if (!selected?.evidence_id || !evidence?.length) return
    const updated = evidence.find((e) => e.evidence_id === selected.evidence_id)
    if (updated) setSelected(updated)
  }, [evidence, selected?.evidence_id])

  useEffect(() => {
    setImgError(false)
    setChallanReceipt(null)
    setExportMsg('')
  }, [selected?.evidence_id])

  const filtered = useMemo(() => {
    return (evidence || []).filter((ev) => {
      if (filters.violation_type) {
        const types = (ev.violation_type || '').split(',').map((t) => t.trim())
        if (!types.includes(filters.violation_type)) return false
      }
      if (filters.review_status && ev.review_status !== filters.review_status) return false
      if (filters.plate && !ev.plate_normalized?.toUpperCase().includes(filters.plate.toUpperCase())) return false
      return true
    })
  }, [evidence, filters])

  async function issueChallan(evidenceId) {
    if (!onExportChallan) return null
    setExportingChallan(true)
    setExportMsg('')
    try {
      const res = await onExportChallan(evidenceId)
      setChallanReceipt({
        challan: res.challan,
        receiptPath: res.receipt_path,
      })
      setExportMsg(`e-Challan ${res.challan?.challan_number} issued`)
      return res
    } catch (err) {
      setExportMsg(err.message)
      return null
    } finally {
      setExportingChallan(false)
    }
  }

  async function handleConfirmAndIssue() {
    if (!selected) return
    try {
      await onReview(selected.evidence_id, 'confirmed')
      await issueChallan(selected.evidence_id)
    } catch (err) {
      setExportMsg(err.message)
    }
  }

  useEffect(() => {
    const handler = (e) => {
      if (!selected || e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return
      if (e.key === 'c' || e.key === 'C') {
        if (selected.review_status === 'pending_review') handleConfirmAndIssue()
        else if (selected.review_status === 'confirmed') issueChallan(selected.evidence_id)
      }
      if (e.key === 'r' || e.key === 'R') onReview(selected.evidence_id, 'rejected')
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [selected, onReview, onExportChallan])

  if (loading && !evidence?.length) {
    return <ListSkeleton rows={6} />
  }

  return (
    <div className="space-y-4">
      {/* Filter chips */}
      <div className="card-sm space-y-3">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
          <input
            className="input pl-10"
            placeholder="Search plate number…"
            value={filters.plate}
            onChange={(e) => setFilters({ ...filters, plate: e.target.value })}
          />
        </div>
        <div className="flex flex-wrap gap-2">
          {STATUS_CHIPS.map((chip) => (
            <button
              key={chip.id}
              onClick={() => setFilters({ ...filters, review_status: chip.id })}
              className={`chip ${filters.review_status === chip.id ? 'chip-active' : 'chip-inactive'}`}
            >
              {chip.label}
            </button>
          ))}
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setFilters({ ...filters, violation_type: '' })}
            className={`chip ${!filters.violation_type ? 'chip-active' : 'chip-inactive'}`}
          >
            All types
          </button>
          {Object.entries(VIOLATION_LABELS)
            .filter(([k]) => k !== 'none')
            .map(([k, v]) => (
              <button
                key={k}
                onClick={() => setFilters({ ...filters, violation_type: k })}
                className={`chip ${filters.violation_type === k ? 'chip-active' : 'chip-inactive'}`}
              >
                {v}
              </button>
            ))}
        </div>
      </div>

      {!filtered.length ? (
        <EmptyState
          icon={FileSearch}
          title="No evidence found"
          description="Try adjusting filters or upload new traffic media."
        />
      ) : (
        <div className="grid lg:grid-cols-[340px_1fr] gap-4 min-h-[500px]">
          {/* List pane */}
          <div className="card p-0 overflow-hidden flex flex-col max-h-[70vh] lg:max-h-[calc(100vh-220px)]">
            <div className="p-3 border-b border-surface-border text-xs text-slate-500">
              {filtered.length} record{filtered.length !== 1 ? 's' : ''}
            </div>
            <div className="flex-1 overflow-y-auto">
              {filtered.map((ev, i) => (
                <motion.button
                  key={ev.evidence_id}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: i * 0.03 }}
                  onClick={() => setSelected(ev)}
                  className={`w-full flex items-start gap-3 p-3 border-b border-surface-border/50 text-left transition-colors ${
                    selected?.evidence_id === ev.evidence_id
                      ? 'bg-green-50 border-l-2 border-l-brand-600'
                      : 'hover:bg-green-50/70'
                  }`}
                >
                  <div className="w-10 h-10 rounded-lg bg-surface border border-surface-border overflow-hidden shrink-0">
                    {ev.annotated_path ? (
                      <img src={annotatedUrl(ev.annotated_path)} alt="" className="w-full h-full object-cover" />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-slate-600 text-[8px]">—</div>
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <span className="text-sm font-medium text-brand-900 truncate">
                        {formatViolationTypes(ev.violation_type)}
                      </span>
                      <StatusBadge status={ev.review_status} />
                      {ev.review_tier === 'fast_track' && (
                        <span className="text-[9px] bg-amber-100 text-amber-800 px-1 rounded">FAST</span>
                      )}
                    </div>
                    <p className="text-xs text-slate-500 truncate mt-0.5">
                      {ev.vehicle_id || '—'} · {ev.plate_normalized || 'No plate'} · {formatDateTime(ev.created_at)}
                    </p>
                    <div className="mt-1.5 h-1 bg-green-100 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-brand-600 rounded-full"
                        style={{ width: `${(ev.confidence || 0) * 100}%` }}
                      />
                    </div>
                  </div>
                </motion.button>
              ))}
            </div>
          </div>

          {/* Detail pane */}
          <div className="card flex flex-col min-h-[400px]">
            <AnimatePresence mode="wait">
              {!selected ? (
                <motion.div
                  key="empty"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="flex-1 flex items-center justify-center"
                >
                  <EmptyState
                    icon={FileSearch}
                    title="Select evidence"
                    description="Choose a record from the list to review details."
                  />
                </motion.div>
              ) : (
                <motion.div
                  key={selected.evidence_id}
                  initial={{ opacity: 0, x: 8 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0 }}
                  className="flex flex-col flex-1"
                >
                  <div className="flex items-start justify-between gap-4 mb-4">
                    <div>
                      <div className="flex items-center gap-2 flex-wrap">
                        <h3 className="text-xl font-semibold text-brand-900">
                          {formatViolationTypes(selected.violation_type)}
                        </h3>
                        <StatusBadge status={selected.review_status} />
                        <PriorityBadge violationType={primaryViolationType(selected.violation_type)} />
                      </div>
                      <p className="text-sm text-gray-600 mt-2">{selected.reason}</p>
                    </div>
                    <span className="text-2xl font-mono font-bold text-brand-700 shrink-0">
                      {confidencePercent(selected.confidence)}
                    </span>
                  </div>

                  {/* Image */}
                  <div className="rounded-xl border border-surface-border overflow-hidden bg-gray-50 mb-4 flex-1 min-h-[200px] max-h-[360px] flex items-center justify-center">
                    {selected.annotated_path && !imgError ? (
                      <img
                        src={annotatedUrl(selected.annotated_path)}
                        alt="Evidence"
                        className="w-full h-full object-contain"
                        onError={() => setImgError(true)}
                      />
                    ) : (
                      <div className="flex flex-col items-center gap-2 text-slate-500 py-12">
                        <ImageOff className="w-10 h-10" />
                        <p className="text-sm">Evidence image unavailable</p>
                      </div>
                    )}
                  </div>

                  {/* Metadata grid */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
                      {[
                      { label: 'Vehicle', value: selected.vehicle_id || '—' },
                      { label: 'Plate', value: selected.plate_normalized || 'N/A' },
                      { label: 'Camera', value: selected.camera_id },
                      { label: 'Quality', value: selected.preprocessing ? `${(selected.preprocessing.quality_score * 100).toFixed(0)}%` : '—' },
                    ].map((m) => (
                      <div key={m.label} className="card-sm py-2.5 px-3">
                        <p className="text-[10px] text-gray-500 uppercase">{m.label}</p>
                        <p className="text-sm font-medium text-brand-900 mt-0.5 font-mono truncate">{m.value}</p>
                      </div>
                    ))}
                  </div>

                  {/* Sticky actions */}
                  <div className="mt-auto pt-4 border-t border-surface-border flex flex-wrap items-center gap-3">
                    {selected.violation_type !== 'none' ? (
                      <>
                        {selected.review_status === 'pending_review' && (
                          <>
                            <button
                              type="button"
                              className="btn-success flex-1 sm:flex-none flex items-center justify-center gap-2"
                              disabled={exportingChallan}
                              onClick={handleConfirmAndIssue}
                            >
                              <Receipt className="w-4 h-4" />
                              {exportingChallan ? 'Issuing…' : 'Confirm & Issue e-Challan'}
                              <span className="hidden sm:inline text-emerald-200/60 text-xs ml-1">C</span>
                            </button>
                            <button
                              type="button"
                              className="btn-danger flex-1 sm:flex-none"
                              disabled={exportingChallan}
                              onClick={() => onReview(selected.evidence_id, 'rejected')}
                            >
                              Reject
                              <span className="hidden sm:inline text-rose-200/60 text-xs ml-2">R</span>
                            </button>
                          </>
                        )}
                        {selected.review_status === 'confirmed' && onExportChallan && (
                          <>
                            <button
                              type="button"
                              className="btn-primary flex-1 sm:flex-none flex items-center justify-center gap-2"
                              disabled={exportingChallan}
                              onClick={() => issueChallan(selected.evidence_id)}
                            >
                              <Receipt className="w-4 h-4" />
                              {exportingChallan ? 'Generating…' : 'View / Download e-Challan'}
                            </button>
                            <p className="text-xs text-green-700 w-full">
                              Violation confirmed — e-Challan can be re-downloaded or printed anytime.
                            </p>
                          </>
                        )}
                        {selected.review_status === 'rejected' && (
                          <p className="text-sm text-gray-600 w-full">
                            This violation was rejected. No e-Challan will be issued.
                          </p>
                        )}
                      </>
                    ) : (
                      <p className="text-sm text-gray-600">
                        Vehicle processed — no violations detected. Auto-cleared; no officer action required.
                      </p>
                    )}
                    {exportMsg && <p className="text-xs text-brand-700 w-full">{exportMsg}</p>}
                    {selected.review_status === 'pending_review' && (
                      <p className="text-[10px] text-slate-600 hidden lg:block ml-auto">
                        Press C to confirm & issue challan · R to reject
                      </p>
                    )}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      )}

      <AnimatePresence>
        {challanReceipt && (
          <ChallanReceipt
            challan={challanReceipt.challan}
            receiptPath={challanReceipt.receiptPath}
            onClose={() => setChallanReceipt(null)}
          />
        )}
      </AnimatePresence>
    </div>
  )
}
