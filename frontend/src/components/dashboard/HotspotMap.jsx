import { useEffect } from 'react'
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from 'react-leaflet'
import { CITY, isLegacyHyderabad, remapToBangalore } from '../../config/city'
import { THEME } from '../../config/theme'

function MapViewController({ center, zoom }) {
  const map = useMap()
  useEffect(() => {
    map.setView(center, zoom, { animate: false })
  }, [center, zoom, map])
  return null
}

function normalizeHotspots(hotspots) {
  return (hotspots || []).map((h, i) => {
    if (isLegacyHyderabad(h.lat, h.lng)) {
      const remapped = remapToBangalore(h.lat, h.lng, i)
      return {
        ...h,
        lat: remapped.lat,
        lng: remapped.lng,
        camera_id: h.camera_id?.includes('HYD') ? remapped.cameraId : h.camera_id,
        zone: remapped.zoneName,
      }
    }
    return h
  })
}

export function HotspotMap({ hotspots }) {
  const normalized = normalizeHotspots(hotspots)
  const center = CITY.mapCenter

  return (
    <div className="relative h-full min-h-[280px]">
      <div className="absolute top-3 left-3 z-[1000] bg-white/95 backdrop-blur border border-surface-border rounded-lg px-3 py-1.5 text-xs font-semibold text-brand-900 shadow-sm">
        {CITY.displayName} · Violation Map
      </div>
      <MapContainer
        center={center}
        zoom={CITY.mapZoom}
        minZoom={11}
        maxBounds={CITY.mapBounds}
        maxBoundsViscosity={0.8}
        className="h-full w-full rounded-xl"
        style={{ minHeight: 280 }}
        scrollWheelZoom
      >
        <MapViewController center={center} zoom={CITY.mapZoom} />
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {normalized.map((h, i) => (
          <CircleMarker
            key={`${h.lat}-${h.lng}-${i}`}
            center={[h.lat, h.lng]}
            radius={8 + Math.min(h.count * 2, 18)}
            pathOptions={{
              color: h.count > 5 ? THEME.danger : h.count > 2 ? THEME.warning : THEME.chartPrimary,
              fillColor: h.count > 5 ? THEME.danger : h.count > 2 ? THEME.warning : THEME.chartPrimary,
              fillOpacity: 0.6,
              weight: 2,
            }}
          >
            <Popup>
              <div className="text-sm min-w-[140px]">
                <strong className="text-brand-900">{h.camera_id}</strong>
                {h.zone && <p className="text-gray-600 text-xs mt-0.5">{h.zone}</p>}
                <p className="text-gray-700 mt-1">
                  {h.count} violation{h.count !== 1 ? 's' : ''}
                </p>
                <p className="text-[10px] text-gray-400 mt-1">{CITY.name}</p>
              </div>
            </Popup>
          </CircleMarker>
        ))}
        {/* Default zone markers when no hotspot data */}
        {!normalized.length &&
          CITY.zones.slice(0, 3).map((z) => (
            <CircleMarker
              key={z.id}
              center={[z.lat, z.lng]}
              radius={6}
              pathOptions={{
                color: THEME.chartPrimary,
                fillColor: THEME.chartPrimary,
                fillOpacity: 0.3,
                weight: 1,
                dashArray: '4 4',
              }}
            >
              <Popup>
                <span className="text-sm">
                  <strong>{z.name}</strong>
                  <br />
                  <span className="text-gray-500 text-xs">{z.id} · No violations yet</span>
                </span>
              </Popup>
            </CircleMarker>
          ))}
      </MapContainer>
      <div className="absolute bottom-3 left-3 bg-white/95 backdrop-blur border border-surface-border rounded-lg px-3 py-2 text-[10px] z-[1000] shadow-sm">
        <p className="text-gray-600 mb-1 font-medium">Intensity</p>
        <div className="flex items-center gap-1">
          <span className="w-3 h-3 rounded-full" style={{ background: THEME.chartPrimary }} />
          <span className="text-gray-500">Low</span>
          <span className="w-3 h-3 rounded-full ml-1" style={{ background: THEME.warning }} />
          <span className="text-gray-500">Med</span>
          <span className="w-3 h-3 rounded-full ml-1" style={{ background: THEME.danger }} />
          <span className="text-gray-500">High</span>
        </div>
      </div>
    </div>
  )
}
