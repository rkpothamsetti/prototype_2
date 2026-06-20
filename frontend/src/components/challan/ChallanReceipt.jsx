import { motion } from 'framer-motion'
import { Download, Printer, X } from 'lucide-react'
import { formatDateTime } from '../../utils/format'
import { challanReceiptUrl } from '../../api'
import { LOGO_SRC, VIOLATION_LABELS } from '../../constants'

function ReceiptRow({ label, value }) {
  return (
    <div className="flex justify-between gap-3 py-1.5 border-b border-dotted border-gray-200 text-xs">
      <span className="text-gray-500 shrink-0">{label}</span>
      <span className="font-semibold text-gray-900 text-right break-all">{value}</span>
    </div>
  )
}

export function ChallanReceipt({ challan, receiptPath, onClose }) {
  if (!challan) return null

  const amount = challan.fine_amount_inr ?? 0
  const channels = (challan.payment_channels || []).join(', ')
  const loc = challan.location || {}
  const coords =
    loc.lat != null && loc.lng != null ? `${Number(loc.lat).toFixed(5)}, ${Number(loc.lng).toFixed(5)}` : '—'
  const offenceLabel =
    challan.violation_label ||
    VIOLATION_LABELS[challan.violation_code] ||
    challan.violation_code ||
    '—'

  function handlePrint() {
    const url = receiptPath ? challanReceiptUrl(receiptPath) : null
    if (url) {
      const w = window.open(url, '_blank', 'noopener,noreferrer,width=480,height=720')
      if (w) w.onload = () => w.print()
      return
    }
    window.print()
  }

  function handleDownload() {
    const url = receiptPath ? challanReceiptUrl(receiptPath) : null
    if (!url) return
    const a = document.createElement('a')
    a.href = url
    a.download = `${challan.challan_number || 'echallan'}_receipt.html`
    a.target = '_blank'
    a.rel = 'noopener'
    document.body.appendChild(a)
    a.click()
    a.remove()
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 overflow-y-auto bg-black/50 print:bg-white print:static print:overflow-visible"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="e-Challan receipt"
    >
      <div className="flex min-h-full items-center justify-center p-4 sm:p-6 print:p-0 print:block">
        <motion.div
          initial={{ scale: 0.96, y: 12 }}
          animate={{ scale: 1, y: 0 }}
          exit={{ scale: 0.96, y: 12 }}
          onClick={(e) => e.stopPropagation()}
          className="relative flex w-full max-w-md max-h-[min(92vh,820px)] flex-col rounded-xl bg-white shadow-2xl overflow-hidden print:max-h-none print:shadow-none print:rounded-none my-4 sm:my-6"
          id="challan-receipt"
        >
          {/* Header — always visible */}
          <div className="relative z-20 shrink-0 bg-gradient-to-br from-slate-800 to-teal-700 text-white text-center px-4 pt-5 pb-4">
            <button
              type="button"
              onClick={onClose}
              className="absolute right-3 top-3 p-1.5 rounded-lg hover:bg-white/10 print:hidden"
              aria-label="Close"
            >
              <X className="w-5 h-5" />
            </button>
            <p className="text-[10px] tracking-widest font-bold opacity-90 px-6">GOVERNMENT OF INDIA · MORTH</p>
            <h2 className="text-lg font-extrabold mt-1">E-CHALLAN RECEIPT</h2>
            <p className="text-[11px] opacity-90 mt-1">Integrated Traffic Enforcement · Nigha AI</p>
            <span className="inline-block mt-2 px-2 py-0.5 border border-dashed border-white/60 text-[9px] tracking-widest">
              OFFICER CONFIRMED DRAFT
            </span>
          </div>

          {/* Scrollable receipt body */}
          <div className="relative z-10 flex-1 min-h-0 overflow-y-auto overscroll-y-contain">
            <div
              className="absolute inset-0 pointer-events-none"
              style={{
                backgroundImage: `url(${LOGO_SRC})`,
                backgroundRepeat: 'no-repeat',
                backgroundPosition: 'center 38%',
                backgroundSize: '52%',
                opacity: 0.09,
              }}
              aria-hidden
            />

            <div className="relative p-4 sm:p-5 pb-6 text-sm bg-white/92">
              <ReceiptRow label="Challan No." value={challan.challan_number || '—'} />
              <ReceiptRow label="Issued" value={formatDateTime(challan.generated_at)} />
              <ReceiptRow label="Payment due" value={challan.payment_due_date || '—'} />

              <p className="text-[10px] font-bold tracking-wider text-teal-700 mt-4 mb-1 uppercase">Vehicle</p>
              <ReceiptRow label="Registration" value={challan.registration_number || 'UNKNOWN'} />
              <ReceiptRow label="Vehicle ID" value={challan.vehicle_id || '—'} />
              <ReceiptRow label="Class" value={challan.vehicle_class || '—'} />

              <p className="text-[10px] font-bold tracking-wider text-teal-700 mt-4 mb-1 uppercase">Violation</p>
              <ReceiptRow label="Offence" value={offenceLabel} />
              <ReceiptRow label="MV Act Sec." value={challan.violation_section || '—'} />
              <ReceiptRow
                label="AI confidence"
                value={challan.confidence != null ? `${(challan.confidence * 100).toFixed(1)}%` : '—'}
              />

              <p className="text-[10px] font-bold tracking-wider text-teal-700 mt-4 mb-1 uppercase">Location</p>
              <ReceiptRow label="Camera" value={loc.camera_id || '—'} />
              <ReceiptRow label="Coordinates" value={coords} />

              <div className="my-4 border-2 border-gray-900 py-3 text-center bg-white/85 rounded-sm">
                <p className="text-[11px] text-gray-500">PENALTY FOR THIS OFFENCE</p>
                <p className="text-3xl font-extrabold font-mono mt-1 text-gray-900">
                  ₹ {amount.toLocaleString('en-IN')}
                </p>
                <p className="text-[10px] text-gray-500 mt-1 px-2">
                  Sec. {challan.violation_section || '—'} · {offenceLabel}
                </p>
              </div>

              <div
                className="h-10 my-3 opacity-80 rounded-sm"
                style={{
                  background:
                    'repeating-linear-gradient(90deg, #111 0 2px, #fff 2px 4px, #111 4px 5px, #fff 5px 8px)',
                }}
                aria-hidden
              />

              <ReceiptRow label="Evidence ref" value={challan.evidence_id || '—'} />
              <ReceiptRow label="Issuing officer" value={challan.officer_id || '—'} />

              <div className="mt-4 pt-3 border-t-2 border-dashed border-gray-300 text-[10px] text-gray-500 leading-relaxed pb-1">
                <p>
                  <strong className="text-gray-700">Payment:</strong> {channels}
                </p>
                <p className="mt-1">
                  <strong className="text-gray-700">Pay / dispute:</strong> {challan.dispute_url}
                </p>
                <p className="mt-2">
                  System-generated draft for officer review. Sync with the official Parivahan e-Challan portal before
                  prosecution.
                </p>
              </div>
            </div>
          </div>

          {/* Footer actions — always visible */}
          <div className="relative z-20 shrink-0 flex gap-2 border-t border-gray-200 bg-gray-50 p-4 print:hidden">
            <button
              type="button"
              className="btn-secondary flex-1 flex items-center justify-center gap-2"
              onClick={handlePrint}
            >
              <Printer className="w-4 h-4" />
              Print / PDF
            </button>
            <button
              type="button"
              className="btn-primary flex-1 flex items-center justify-center gap-2"
              onClick={handleDownload}
              disabled={!receiptPath}
            >
              <Download className="w-4 h-4" />
              Download
            </button>
          </div>
        </motion.div>
      </div>
    </motion.div>
  )
}
