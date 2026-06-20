export function formatLatency(ms) {
  if (!ms || ms < 1000) return `${Math.round(ms || 0)} ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
  const mins = Math.floor(ms / 60000)
  const secs = Math.round((ms % 60000) / 1000)
  return `${mins}m ${secs}s`
}

export function isLatencyDegraded(ms) {
  return ms > 5000
}

export function formatThroughput(ips) {
  if (!ips) return '0 img/s'
  if (ips < 0.1) return `${ips.toFixed(3)} img/s`
  return `${ips.toFixed(2)} img/s`
}

export function formatDate(iso) {
  if (!iso) return '—'
  try {
    const d = new Date(iso)
    return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
  } catch {
    return iso.slice(0, 10)
  }
}

export function formatDateTime(iso) {
  if (!iso) return '—'
  try {
    const d = new Date(iso)
    return d.toLocaleString('en-IN', {
      day: 'numeric',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return iso
  }
}

export function timeAgo(iso) {
  if (!iso) return ''
  try {
    const diff = Date.now() - new Date(iso).getTime()
    const mins = Math.floor(diff / 60000)
    if (mins < 1) return 'just now'
    if (mins < 60) return `${mins}m ago`
    const hrs = Math.floor(mins / 60)
    if (hrs < 24) return `${hrs}h ago`
    return `${Math.floor(hrs / 24)}d ago`
  } catch {
    return ''
  }
}

export function confidencePercent(c) {
  return `${((c || 0) * 100).toFixed(1)}%`
}
