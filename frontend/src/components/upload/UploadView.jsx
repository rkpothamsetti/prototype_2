import { useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronDown, Upload as UploadIcon, Loader2, CheckCircle2 } from 'lucide-react'
import { annotatedUrl, annotatedVideoUrl } from '../../api'
import { VIOLATION_LABELS } from '../../constants'

const STEPS = ['Upload', 'Detecting', 'Review']

export function UploadView({ form, setForm, onSubmit, uploading, job, error }) {
  const [advancedOpen, setAdvancedOpen] = useState(false)
  const [selectedFile, setSelectedFile] = useState(null)
  const fileInputRef = useRef(null)
  const step = !job ? 0 : job.status === 'completed' ? 2 : 1

  function openFilePicker() {
    fileInputRef.current?.click()
  }

  function handleFileChange(e) {
    setSelectedFile(e.target.files?.[0] || null)
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="grid lg:grid-cols-2 gap-6"
    >
      <form onSubmit={onSubmit} className="card space-y-5">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-green-100 flex items-center justify-center">
            <UploadIcon className="w-5 h-5 text-brand-700" />
          </div>
          <div>
            <h2 className="font-semibold text-lg text-brand-900">Upload Traffic Media</h2>
            <p className="text-xs text-slate-500">Image or video from city CCTV</p>
          </div>
        </div>

        {/* Progress stepper */}
        <div className="flex items-center gap-2">
          {STEPS.map((s, i) => (
            <div key={s} className="flex items-center gap-2 flex-1">
              <div
                className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold border-2 transition-colors ${
                  i < step
                    ? 'bg-green-100 border-green-500 text-green-700'
                    : i === step
                      ? 'bg-green-50 border-brand-600 text-brand-700'
                      : 'border-gray-200 text-gray-400'
                }`}
              >
                {i < step ? <CheckCircle2 className="w-4 h-4" /> : i + 1}
              </div>
              <span className={`text-xs hidden sm:inline ${i === step ? 'text-brand-900 font-medium' : 'text-gray-400'}`}>
                {s}
              </span>
              {i < STEPS.length - 1 && <div className="flex-1 h-px bg-surface-border" />}
            </div>
          ))}
        </div>

        <div
          className="border-2 border-dashed border-green-200 rounded-xl p-6 text-center hover:border-brand-500 bg-green-50/30 transition-colors cursor-pointer"
          onClick={openFilePicker}
          onKeyDown={(e) => e.key === 'Enter' && openFilePicker()}
          role="button"
          tabIndex={0}
        >
          <input
            ref={fileInputRef}
            type="file"
            name="file"
            accept="image/*,video/*"
            required
            className="sr-only"
            onChange={handleFileChange}
          />
          <UploadIcon className="w-8 h-8 text-brand-600 mx-auto mb-3" />
          <button
            type="button"
            className="btn-primary inline-flex items-center gap-2"
            onClick={(e) => {
              e.stopPropagation()
              openFilePicker()
            }}
          >
            Choose file
          </button>
          <p className="text-sm text-brand-900 mt-3 font-medium truncate px-2">
            {selectedFile ? selectedFile.name : 'No file selected'}
          </p>
          <p className="text-xs text-slate-500 mt-1">JPG, PNG, or MP4 · videos up to 2 min / 150 MB</p>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <label className="text-sm space-y-1.5">
            <span className="text-slate-400 text-xs">Latitude</span>
            <input className="input" value={form.latitude} onChange={(e) => setForm({ ...form, latitude: e.target.value })} />
          </label>
          <label className="text-sm space-y-1.5">
            <span className="text-slate-400 text-xs">Longitude</span>
            <input className="input" value={form.longitude} onChange={(e) => setForm({ ...form, longitude: e.target.value })} />
          </label>
        </div>

        <label className="text-sm space-y-1.5 block">
          <span className="text-slate-400 text-xs">Camera ID</span>
          <input className="input" value={form.camera_id} onChange={(e) => setForm({ ...form, camera_id: e.target.value })} />
        </label>

        <button
          type="button"
          onClick={() => setAdvancedOpen(!advancedOpen)}
          className="flex items-center gap-2 text-sm text-slate-400 hover:text-slate-200 w-full"
        >
          <ChevronDown className={`w-4 h-4 transition-transform ${advancedOpen ? 'rotate-180' : ''}`} />
          Advanced scene rules
        </button>

        <AnimatePresence>
          {advancedOpen && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="space-y-3 overflow-hidden"
            >
              <label className="text-sm space-y-1.5 block">
                <span className="text-slate-400 text-xs">Legal Direction Angle (°)</span>
                <input className="input" value={form.legal_direction_angle} onChange={(e) => setForm({ ...form, legal_direction_angle: e.target.value })} />
              </label>
              <label className="text-sm space-y-1.5 block">
                <span className="text-slate-400 text-xs">No-Parking Zones JSON</span>
                <input className="input font-mono text-xs" value={form.no_parking_zones} onChange={(e) => setForm({ ...form, no_parking_zones: e.target.value })} />
              </label>
              <label className="text-sm space-y-1.5 block">
                <span className="text-slate-400 text-xs">Stop Line Y (optional)</span>
                <input className="input" value={form.stop_line_y} onChange={(e) => setForm({ ...form, stop_line_y: e.target.value })} placeholder="e.g. 450" />
              </label>
              <div className="grid grid-cols-2 gap-3">
                <label className="text-sm space-y-1.5">
                  <span className="text-slate-400 text-xs">Traffic Light</span>
                  <select className="input" value={form.traffic_light_state} onChange={(e) => setForm({ ...form, traffic_light_state: e.target.value })}>
                    <option value="unknown">Unknown</option>
                    <option value="red">Red</option>
                    <option value="green">Green</option>
                    <option value="yellow">Yellow</option>
                  </select>
                </label>
                <label className="text-sm space-y-1.5">
                  <span className="text-slate-400 text-xs">Signal State</span>
                  <select className="input" value={form.signal_state} onChange={(e) => setForm({ ...form, signal_state: e.target.value })}>
                    <option value="unknown">Unknown</option>
                    <option value="red">Red</option>
                    <option value="green">Green</option>
                  </select>
                </label>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <button type="submit" className="btn-primary w-full flex items-center justify-center gap-2" disabled={uploading}>
          {uploading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Processing…
            </>
          ) : (
            'Upload & Analyze'
          )}
        </button>
      </form>

      <div className="card space-y-4">
        <h2 className="font-semibold text-lg text-brand-900">Processing Result</h2>

        {!job && (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <div className="w-16 h-16 rounded-2xl bg-green-50 border border-surface-border flex items-center justify-center mb-4">
              <UploadIcon className="w-8 h-8 text-brand-600" />
            </div>
            <p className="text-slate-400 text-sm">Upload an image or video clip to start per-vehicle analysis</p>
            <p className="text-xs text-slate-600 mt-1">First run may take 1–2 min while models load</p>
          </div>
        )}

        {job && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-4">
            <div className="flex items-center gap-3">
              {(job.status === 'queued' || job.status === 'processing') && (
                <Loader2 className="w-5 h-5 text-brand-400 animate-spin" />
              )}
              {job.status === 'completed' && <CheckCircle2 className="w-5 h-5 text-emerald-400" />}
              <div>
                <p className="text-sm font-medium capitalize">{job.status}</p>
                {job.latency_ms && <p className="text-xs text-slate-500">Latency: {job.latency_ms} ms</p>}
              </div>
            </div>

            {(job.status === 'queued' || job.status === 'processing') && uploading && (
              <div className="space-y-2">
                <div className="h-1.5 bg-green-100 rounded-full overflow-hidden">
                  <motion.div
                    className="h-full bg-brand-600 rounded-full"
                    initial={{ width: '10%' }}
                    animate={{ width: '85%' }}
                    transition={{ duration: 30, ease: 'linear' }}
                  />
                </div>
                <p className="text-xs text-amber-300">Analyzing vehicles… models loading on first run.</p>
              </div>
            )}

            {(job.annotated_video_path || job.enforcement?.annotated_video_path) && (
              <div className="space-y-2">
                <h3 className="font-medium text-sm text-slate-300">Annotated Video (demo)</h3>
                <video
                  controls
                  className="rounded-xl border border-surface-border w-full bg-black"
                  src={annotatedVideoUrl(job.annotated_video_path || job.enforcement?.annotated_video_path)}
                />
                <p className="text-xs text-slate-500">
                  Per-frame tracking with green = compliant, red = violation (like CCTV review)
                </p>
              </div>
            )}

            {job.annotated_path && (
              <img src={annotatedUrl(job.annotated_path)} alt="Annotated" className="rounded-xl border border-surface-border w-full" />
            )}

            {job.enforcement?.vehicles?.length > 0 && (
              <div className="space-y-2">
                <h3 className="font-medium text-sm text-slate-300">Per-Vehicle Enforcement</h3>
                {job.enforcement.vehicles.map((v) => (
                  <div
                    key={v.vehicle_id}
                    className={`border rounded-xl p-3 text-sm ${
                      v.compliance_status === 'violation' ? 'border-red-200 bg-red-50' : 'border-green-200 bg-green-50'
                    }`}
                  >
                    <p className="font-mono font-semibold">
                      {v.vehicle_id} · {v.vehicle_type}
                      <span className={`ml-2 ${v.compliance_status === 'violation' ? 'text-red-600' : 'text-green-700'}`}>
                        {v.compliance_status}
                      </span>
                    </p>
                    <p className="text-slate-400 mt-1">Plate: {v.license_plate?.plate_normalized || 'N/A'}</p>
                    {v.violations?.length > 0 ? (
                      <ul className="text-slate-400 mt-1 space-y-0.5">
                        {v.violations.map((vi, i) => (
                          <li key={i}>{VIOLATION_LABELS[vi.type] || vi.type} ({(vi.confidence * 100).toFixed(0)}%)</li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-emerald-400/80 mt-1">No violations</p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </motion.div>
        )}

        {error && <p className="text-sm text-rose-300">{error}</p>}
      </div>
    </motion.div>
  )
}
