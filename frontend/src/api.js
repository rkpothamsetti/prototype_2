/** Empty in local dev (Vite proxies /api and /health). Set VITE_API_URL on Vercel to your hosted API origin. */
const API_ORIGIN = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')
const API_BASE = API_ORIGIN ? `${API_ORIGIN}/api/v1` : '/api/v1'
const HEALTH_URL = API_ORIGIN ? `${API_ORIGIN}/health` : '/health'

async function request(path, options = {}, timeoutMs = 60000) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  try {
    const res = await fetch(`${API_BASE}${path}`, { ...options, signal: controller.signal })
    if (!res.ok) {
      let detail = await res.text()
      try {
        detail = JSON.parse(detail).detail || detail
      } catch {
        /* keep text */
      }
      throw new Error(detail || `Request failed: ${res.status}`)
    }
    return res.json()
  } catch (err) {
    if (err.name === 'AbortError') {
      throw new Error('Request timed out — is the backend running on port 8001?')
    }
    if (err.message?.includes('Failed to fetch') || err.message?.includes('NetworkError')) {
      throw new Error('Cannot reach backend. Start API: python run_server.py (port 8001)')
    }
    throw err
  } finally {
    clearTimeout(timer)
  }
}

export async function checkHealth() {
  const res = await fetch(HEALTH_URL, { signal: AbortSignal.timeout(5000) })
  if (!res.ok) throw new Error('Backend health check failed')
  return res.json()
}

export async function uploadMedia(formData) {
  return request('/media/upload', { method: 'POST', body: formData }, 120000)
}

export async function getJob(jobId) {
  return request(`/jobs/${jobId}`, {}, 120000)
}

export async function getEvidence(params = {}) {
  const clean = Object.fromEntries(
    Object.entries(params).filter(([, v]) => v != null && v !== '' && v !== 'undefined')
  )
  const query = new URLSearchParams(clean)
  const qs = query.toString()
  return request(qs ? `/evidence?${qs}` : '/evidence')
}

export async function updateReview(evidenceId, reviewStatus) {
  return request(`/evidence/${evidenceId}/review?review_status=${reviewStatus}`, { method: 'PATCH' })
}

export async function exportChallan(evidenceId) {
  return request(`/evidence/${evidenceId}/export-challan`, { method: 'POST' })
}

export async function getAnalytics() {
  return request('/analytics/summary')
}

export async function getMobilityAnalytics() {
  return request('/analytics/mobility')
}

export async function getFeedbackStats() {
  return request('/feedback/stats')
}

export async function getMetrics() {
  return request('/metrics')
}

export function annotatedUrl(path) {
  if (!path) return ''
  const filename = path.split(/[\\/]/).pop()
  return `${API_BASE}/files/annotated/${filename}`
}

export function annotatedVideoUrl(path) {
  return annotatedUrl(path)
}

export function challanReceiptUrl(path) {
  if (!path) return ''
  const filename = path.split(/[\\/]/).pop()
  return `${API_BASE}/files/challan/${filename}`
}
