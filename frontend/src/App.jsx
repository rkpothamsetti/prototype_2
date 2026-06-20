import {
  checkHealth,
  getAnalytics,
  getEvidence,
  getFeedbackStats,
  getJob,
  getMetrics,
  getMobilityAnalytics,
  updateReview,
  uploadMedia,
  exportChallan,
} from './api'
import { useCallback, useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { Sidebar } from './components/layout/Sidebar'
import { MobileNav } from './components/layout/MobileNav'
import { TopBar } from './components/layout/TopBar'
import { DashboardView } from './components/dashboard/DashboardView'
import { MobilityView } from './components/dashboard/MobilityView'
import { UploadView } from './components/upload/UploadView'
import { EvidenceView } from './components/evidence/EvidenceView'
import { CITY } from './config/city'
import { APP_NAME } from './constants'
import { timeAgo } from './utils/format'

export default function App() {
  const [tab, setTab] = useState('dashboard')
  const [analytics, setAnalytics] = useState(null)
  const [mobility, setMobility] = useState(null)
  const [feedback, setFeedback] = useState(null)
  const [metrics, setMetrics] = useState(null)
  const [evidence, setEvidence] = useState([])
  const [filters, setFilters] = useState({ plate: '', violation_type: '', review_status: '' })
  const [uploading, setUploading] = useState(false)
  const [job, setJob] = useState(null)
  const [backendOk, setBackendOk] = useState(null)
  const [modelsReady, setModelsReady] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [lastUpdated, setLastUpdated] = useState('')
  const [preselectedEvidence, setPreselectedEvidence] = useState(null)
  const [form, setForm] = useState({
    latitude: CITY.latitude,
    longitude: CITY.longitude,
    camera_id: CITY.cameraId,
    legal_direction_angle: '0',
    no_parking_zones: '[[100,300,500,600]]',
    stop_line_y: '',
    traffic_light_state: 'unknown',
    signal_state: 'unknown',
  })

  useEffect(() => {
    let cancelled = false
    let timer

    function poll() {
      checkHealth()
        .then((h) => {
          if (cancelled) return
          const ok = h.app === APP_NAME && Array.isArray(h.features)
          setBackendOk(ok)
          setModelsReady(h.models_ready !== false)
          if (ok && h.models_ready === false) {
            timer = setTimeout(poll, 2000)
          }
        })
        .catch(() => {
          if (!cancelled) setBackendOk(false)
        })
    }

    poll()
    return () => {
      cancelled = true
      if (timer) clearTimeout(timer)
    }
  }, [])

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      const [a, m, mob, fb, e] = await Promise.all([
        getAnalytics(),
        getMetrics(),
        getMobilityAnalytics().catch(() => null),
        getFeedbackStats().catch(() => null),
        getEvidence({ limit: 100 }),
      ])
      setAnalytics(a)
      setMetrics(m)
      setMobility(mob)
      setFeedback(fb)
      setEvidence(e)
      setLastUpdated(timeAgo(new Date().toISOString()) || 'just now')
      setError('')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  const pendingCount = (evidence || []).filter(
    (e) => e.review_status === 'pending_review' && e.violation_type !== 'none',
  ).length

  async function handleUpload(e) {
    e.preventDefault()
    setError('')
    setUploading(true)
    setJob(null)
    try {
      const fd = new FormData(e.target)
      fd.set('latitude', form.latitude)
      fd.set('longitude', form.longitude)
      fd.set('camera_id', form.camera_id)
      fd.set('legal_direction_angle', form.legal_direction_angle)
      fd.set('no_parking_zones', form.no_parking_zones)
      if (form.stop_line_y) fd.set('stop_line_y', form.stop_line_y)
      fd.set('traffic_light_state', form.traffic_light_state)
      fd.set('signal_state', form.signal_state)

      const res = await uploadMedia(fd)
      let attempts = 0
      const poll = async () => {
        const status = await getJob(res.job_id)
        setJob(status)
        if (status.status === 'completed') {
          await refresh()
          setUploading(false)
          setTab('evidence')
          return
        }
        if (status.status === 'failed') {
          setError(status.error_message || 'Processing failed')
          setUploading(false)
          return
        }
        if (attempts > 90) {
          setError('Processing is taking longer than expected. Check Evidence tab shortly.')
          setUploading(false)
          return
        }
        attempts += 1
        setTimeout(poll, 2000)
      }
      poll()
    } catch (err) {
      setError(err.message)
      setUploading(false)
    }
  }

  async function handleReview(evidenceId, status) {
    await updateReview(evidenceId, status)
    await refresh()
  }

  async function handleExportChallan(evidenceId) {
    return exportChallan(evidenceId)
  }

  function goToEvidence(item) {
    setPreselectedEvidence(item?.evidence_id || null)
    setTab('evidence')
  }

  return (
    <div className="flex min-h-screen">
      <Sidebar tab={tab} setTab={setTab} pendingCount={pendingCount} backendOk={backendOk} modelsReady={modelsReady} />

      <div className="flex-1 flex flex-col min-w-0 pb-20 lg:pb-0">
        <TopBar tab={tab} onRefresh={refresh} lastUpdated={lastUpdated} loading={loading} />

        <main className="flex-1 px-4 lg:px-8 py-6">
          {backendOk === false && (
            <motion.div
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              className="card-sm border-red-200 bg-red-50 text-red-800 text-sm mb-6"
            >
              Cannot reach the API. Keep{' '}
              <code className="text-red-700 font-mono bg-red-100 px-1 rounded">python run_server.py</code>{' '}
              and <code className="text-red-700 font-mono bg-red-100 px-1 rounded">ngrok http 8001</code>{' '}
              running on your PC, then refresh.
            </motion.div>
          )}

          {error && tab !== 'upload' && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="card-sm border-red-200 bg-red-50 text-red-800 text-sm mb-6"
            >
              {error}
            </motion.div>
          )}

          <AnimatePresence mode="wait">
            <motion.div
              key={tab}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
            >
              {tab === 'dashboard' && (
                <DashboardView
                  analytics={analytics}
                  metrics={metrics}
                  mobility={mobility}
                  feedback={feedback}
                  evidence={evidence}
                  loading={loading}
                  onReviewSelect={goToEvidence}
                  onGoEvidence={() => goToEvidence(null)}
                />
              )}

              {tab === 'mobility' && (
                <MobilityView mobility={mobility} analytics={analytics} loading={loading} />
              )}

              {tab === 'upload' && (
                <UploadView
                  form={form}
                  setForm={setForm}
                  onSubmit={handleUpload}
                  uploading={uploading}
                  job={job}
                  error={error}
                />
              )}

              {tab === 'evidence' && (
                <EvidenceView
                  evidence={evidence}
                  loading={loading}
                  filters={filters}
                  setFilters={setFilters}
                  onRefresh={refresh}
                  onReview={handleReview}
                  onExportChallan={handleExportChallan}
                  preselectedId={preselectedEvidence}
                />
              )}
            </motion.div>
          </AnimatePresence>
        </main>
      </div>

      <MobileNav tab={tab} setTab={setTab} pendingCount={pendingCount} />
    </div>
  )
}
