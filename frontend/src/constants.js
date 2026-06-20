export const APP_NAME = 'Nigha AI'
export const LOGO_SRC = '/nigha-logo.png'

/** Indicative MV Act penalty amounts (INR) — mirrored from backend */
export const VIOLATION_PENALTIES_INR = {
  helmet_non_compliance: 1000,
  triple_riding: 2000,
  wrong_side_driving: 3000,
  illegal_parking: 500,
  seatbelt_non_compliance: 1500,
  stop_line_violation: 1000,
  red_light_violation: 5000,
}

export const VIOLATION_LABELS = {
  helmet_non_compliance: 'No Helmet',
  triple_riding: 'Triple Riding',
  wrong_side_driving: 'Wrong Side',
  illegal_parking: 'Illegal Parking',
  seatbelt_non_compliance: 'No Seatbelt',
  stop_line_violation: 'Stop Line',
  red_light_violation: 'Red Light',
  none: 'No Violation',
}

export const VIOLATION_COLORS = {
  helmet_non_compliance: '#d97706',
  triple_riding: '#d97706',
  wrong_side_driving: '#dc2626',
  illegal_parking: '#16a34a',
  seatbelt_non_compliance: '#d97706',
  stop_line_violation: '#059669',
  red_light_violation: '#dc2626',
  none: '#9ca3af',
}

export const VIOLATION_SEVERITY = {
  helmet_non_compliance: 'high',
  triple_riding: 'high',
  wrong_side_driving: 'critical',
  illegal_parking: 'low',
  seatbelt_non_compliance: 'high',
  stop_line_violation: 'medium',
  red_light_violation: 'critical',
  none: 'low',
}

const SEVERITY_RANK = { critical: 4, high: 3, medium: 2, low: 1 }

/** Human-readable label for one or comma-merged violation types. */
export function formatViolationTypes(typeStr) {
  if (!typeStr || typeStr === 'none') return VIOLATION_LABELS.none
  return typeStr
    .split(',')
    .map((t) => VIOLATION_LABELS[t.trim()] || t.trim())
    .join(' + ')
}

/** Highest-severity type when multiple violations are merged on one evidence row. */
export function primaryViolationType(typeStr) {
  if (!typeStr) return ''
  const types = typeStr.split(',').map((t) => t.trim()).filter(Boolean)
  if (types.length <= 1) return types[0] || typeStr
  return types.sort(
    (a, b) => (SEVERITY_RANK[VIOLATION_SEVERITY[b]] || 0) - (SEVERITY_RANK[VIOLATION_SEVERITY[a]] || 0),
  )[0]
}

export const REVIEW_STATUS = {
  pending_review: { label: 'Pending', color: 'bg-amber-100 text-amber-800 border-amber-300' },
  confirmed: { label: 'Confirmed', color: 'bg-green-100 text-green-800 border-green-300' },
  rejected: { label: 'Rejected', color: 'bg-red-100 text-red-800 border-red-300' },
  auto_cleared: { label: 'Cleared', color: 'bg-gray-100 text-gray-600 border-gray-300' },
}

export const NAV_ITEMS = [
  { id: 'dashboard', label: 'Dashboard', icon: 'LayoutDashboard' },
  { id: 'mobility', label: 'Mobility', icon: 'Map' },
  { id: 'upload', label: 'Upload', icon: 'Upload' },
  { id: 'evidence', label: 'Evidence', icon: 'FileSearch' },
]

export const CONGESTION_LABELS = {
  free_flow: 'Free Flow',
  moderate: 'Moderate',
  heavy: 'Heavy',
  gridlock: 'Gridlock',
}

export const CONGESTION_COLORS = {
  free_flow: '#16a34a',
  moderate: '#d97706',
  heavy: '#ea580c',
  gridlock: '#dc2626',
}

export const PRIORITY_COLORS = {
  critical: 'bg-red-100 text-red-700 border-red-300',
  high: 'bg-amber-100 text-amber-800 border-amber-300',
  medium: 'bg-green-100 text-green-800 border-green-300',
  low: 'bg-gray-100 text-gray-600 border-gray-300',
}
