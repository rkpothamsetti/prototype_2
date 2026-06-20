/** Bangalore deployment — map & location defaults */
export const CITY = {
  name: 'Bangalore',
  displayName: 'Bengaluru',
  cameraId: 'CAM_BLR_MG_01',
  latitude: '12.9750',
  longitude: '77.6063',
  mapCenter: [12.9716, 77.5946],
  mapZoom: 12,
  mapBounds: [
    [12.75, 77.45], // SW
    [13.15, 77.85], // NE
  ],
  zone: 'MG Road Junction',
  /** Known Bangalore CCTV zones for map labels */
  zones: [
    { id: 'CAM_BLR_MG_01', name: 'MG Road', lat: 12.975, lng: 77.6063 },
    { id: 'CAM_BLR_SILK_01', name: 'Silk Board', lat: 12.9176, lng: 77.6234 },
    { id: 'CAM_BLR_HEBBAL_01', name: 'Hebbal Flyover', lat: 13.0358, lng: 77.597 },
    { id: 'CAM_BLR_ECITY_01', name: 'Electronic City', lat: 12.8399, lng: 77.677 },
    { id: 'CAM_BLR_INDIRA_01', name: 'Indiranagar', lat: 12.9784, lng: 77.6408 },
  ],
}

/** Hyderabad coords (legacy) — used to detect & remap hotspots */
export const LEGACY_HYDERABAD = {
  lat: 17.385,
  lng: 78.4867,
  tolerance: 0.5,
}

/** Remap legacy Hyderabad coordinates to Bangalore zone grid */
export function remapToBangalore(lat, lng, index = 0) {
  const zones = CITY.zones
  const z = zones[index % zones.length]
  const jitter = (index % 3) * 0.002
  return {
    lat: z.lat + jitter,
    lng: z.lng + jitter,
    cameraId: z.id,
    zoneName: z.name,
  }
}

export function isLegacyHyderabad(lat, lng) {
  if (lat == null || lng == null) return false
  return (
    Math.abs(lat - LEGACY_HYDERABAD.lat) < LEGACY_HYDERABAD.tolerance &&
    Math.abs(lng - LEGACY_HYDERABAD.lng) < LEGACY_HYDERABAD.tolerance
  )
}
