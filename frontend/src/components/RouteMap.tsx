import { useEffect, useRef, useState } from 'react'
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from 'react-leaflet'
import L from 'leaflet'
import type { Location, Route, DisplayLabels } from '../types/api'
import { getRouteColor } from '../utils/route-colors'
import { formatAttributeValue } from '../utils/build-labels'
import { fetchRouteGeometry } from '../api/matrices'

// Circle marker with a Lucide icon inside
function createPinIcon(color: string, iconPath: string, size: number = 32) {
  const half = size / 2
  const iconSize = size * 0.55
  const iconOffset = (size - iconSize) / 2
  return L.divIcon({
    className: '',
    iconSize: [size, size],
    iconAnchor: [half, half],
    popupAnchor: [0, -half],
    html: `
      <svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" xmlns="http://www.w3.org/2000/svg">
        <circle cx="${half}" cy="${half}" r="${half}" fill="${color}" stroke="white" stroke-width="2.5"/>
        <svg x="${iconOffset}" y="${iconOffset}" width="${iconSize}" height="${iconSize}" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          ${iconPath}
        </svg>
      </svg>
    `,
  })
}

// Lucide icon paths
const WAREHOUSE_PATH = '<path d="M22 8.35V20a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V8.35A2 2 0 0 1 3.26 6.5l8-3.2a2 2 0 0 1 1.48 0l8 3.2A2 2 0 0 1 22 8.35Z"/><path d="M6 18h12"/><path d="M6 14h12"/><rect x="9" y="18" width="6" height="4"/>'
const HOUSE_PATH = '<path d="M15 21v-8a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v8"/><path d="M3 10a2 2 0 0 1 .709-1.528l7-5.999a2 2 0 0 1 2.582 0l7 5.999A2 2 0 0 1 21 10v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>'

const depotIcon = createPinIcon('#03344E', WAREHOUSE_PATH, 40)
const jobIcon = createPinIcon('#4785BF', HOUSE_PATH, 34)

// Component to fit bounds on mount / location changes
function FitBounds({ locations }: { locations: Location[] }) {
  const map = useMap()
  const fitted = useRef(false)

  useEffect(() => {
    if (locations.length === 0 || fitted.current) return
    const bounds = L.latLngBounds(
      locations.map((l) => [l.latitude, l.longitude] as [number, number])
    )
    map.fitBounds(bounds, { padding: [50, 50] })
    fitted.current = true
  }, [locations, map])

  return null
}

// Component to fit bounds to a selected route
function FitToRoute({
  selectedRoute,
  routeLines,
  roadGeometries,
}: {
  selectedRoute: string | null
  routeLines: { vehicleId: string; coords: [number, number][] }[]
  roadGeometries: Record<string, [number, number][]>
}) {
  const map = useMap()
  const prevSelected = useRef<string | null>(null)
  const prevRouteCount = useRef(0)

  useEffect(() => {
    const routeCount = routeLines.length

    // Routes just appeared (optimize was clicked) — zoom to fit all
    if (routeCount > 0 && prevRouteCount.current === 0) {
      prevRouteCount.current = routeCount
      prevSelected.current = null
      const allCoords = routeLines.flatMap((r) => r.coords)
      if (allCoords.length > 0) {
        map.flyToBounds(L.latLngBounds(allCoords), { padding: [50, 50], duration: 0.6 })
      }
      return
    }
    prevRouteCount.current = routeCount

    // Selection changed
    if (selectedRoute === prevSelected.current) return
    prevSelected.current = selectedRoute

    if (!selectedRoute) {
      // Deselected — zoom back out to fit all routes
      const allCoords = routeLines.flatMap((r) => r.coords)
      if (allCoords.length > 0) {
        map.flyToBounds(L.latLngBounds(allCoords), { padding: [50, 50], duration: 0.6 })
      }
      return
    }

    // Use road geometry if available, otherwise the stop coords
    const coords = roadGeometries[selectedRoute]
      || routeLines.find((r) => r.vehicleId === selectedRoute)?.coords
      || []

    if (coords.length > 0) {
      map.flyToBounds(L.latLngBounds(coords), { padding: [60, 60], duration: 0.6 })
    }
  }, [selectedRoute, routeLines, roadGeometries, map])

  return null
}

// Component to fly to a location
function FlyToLocation({ locationId, locations }: { locationId: string | null; locations: Location[] }) {
  const map = useMap()

  useEffect(() => {
    if (!locationId) return
    const loc = locations.find((l) => l.id === locationId)
    if (loc) {
      map.flyTo([loc.latitude, loc.longitude], 15, { duration: 0.8 })
    }
  }, [locationId, locations, map])

  return null
}

interface RouteMapProps {
  locations: Location[]
  depotIds: Set<string>
  routes?: Route[]
  selectedRoute?: string | null
  onSelectRoute?: (vehicleId: string | null) => void
  focusLocationId?: string | null
  labels: DisplayLabels
}

export function RouteMap({
  locations,
  depotIds,
  routes,
  selectedRoute,
  onSelectRoute,
  focusLocationId,
  labels,
}: RouteMapProps) {
  const locationMap = new Map(locations.map((l) => [l.id, l]))
  const [roadGeometries, setRoadGeometries] = useState<Record<string, [number, number][]>>({})

  // Fetch road geometries when routes change
  useEffect(() => {
    if (!routes || routes.length === 0) {
      setRoadGeometries({})
      return
    }

    let cancelled = false
    const fetchAll = async () => {
      const geometries: Record<string, [number, number][]> = {}
      await Promise.all(
        routes.map(async (route) => {
          const coords = await fetchRouteGeometry(route, locationMap)
          if (!cancelled) {
            geometries[route.vehicle_id] = coords
          }
        })
      )
      if (!cancelled) {
        setRoadGeometries(geometries)
      }
    }
    fetchAll()
    return () => { cancelled = true }
  }, [routes, locations])

  // Build route polyline data
  const routeLines = (routes || []).map((route, idx) => {
    // Use road geometry if available, fall back to straight lines
    const coords = roadGeometries[route.vehicle_id] || route.stops
      .map((stop) => {
        const loc = locationMap.get(stop.location_id)
        return loc ? [loc.latitude, loc.longitude] as [number, number] : null
      })
      .filter((c): c is [number, number] => c !== null)

    return {
      vehicleId: route.vehicle_id,
      coords,
      color: getRouteColor(idx),
      isSelected: selectedRoute === route.vehicle_id,
    }
  })


  return (
    <MapContainer
      center={[39.14, -84.50]}
      zoom={11}
      className="h-full w-full"
      zoomControl={true}
    >
      <TileLayer
        attribution='&copy; <a href="https://carto.com/">CARTO</a>'
        url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
      />
      <FitBounds locations={locations} />
      <FlyToLocation locationId={focusLocationId ?? null} locations={locations} />
      <FitToRoute selectedRoute={selectedRoute ?? null} routeLines={routeLines} roadGeometries={roadGeometries} />

      {/* Route polylines (unselected first, selected on top) */}
      {routeLines
        .filter((r) => !r.isSelected)
        .map((r) => (
          <Polyline
            key={r.vehicleId}
            positions={r.coords}
            pathOptions={{
              color: r.color,
              weight: 3,
              opacity: selectedRoute ? 0.25 : 0.7,
              dashArray: selectedRoute ? '8 4' : undefined,
            }}
            eventHandlers={{
              click: () => onSelectRoute?.(r.vehicleId),
            }}
          />
        ))}
      {routeLines
        .filter((r) => r.isSelected)
        .map((r) => (
          <Polyline
            key={r.vehicleId}
            positions={r.coords}
            pathOptions={{
              color: r.color,
              weight: 5,
              opacity: 1,
            }}
          />
        ))}

      {/* Location markers */}
      {locations.map((loc) => {
        const isDepot = depotIds.has(loc.id)
        const icon = isDepot ? depotIcon : jobIcon

        return (
          <Marker
            key={loc.id}
            position={[loc.latitude, loc.longitude]}
            icon={icon}
          >
            <Popup>
              <div className="font-body text-sm min-w-[160px]">
                <div className="font-semibold text-brand-primary">
                  {labels.locations[loc.id] || loc.id}
                </div>
                {isDepot && (
                  <div className="text-xs text-gray-500 mt-0.5">Depot</div>
                )}
                {labels.locationDescriptions[loc.id] && (
                  <div className="text-xs text-gray-500 mt-0.5">{labels.locationDescriptions[loc.id]}</div>
                )}
                {loc.service_time ? (
                  <div className="text-xs text-gray-600 mt-1">
                    Service: {loc.service_time} min
                  </div>
                ) : null}
                {loc.required_resources && loc.required_resources.length > 0 && (
                  <div className="mt-1.5 flex flex-wrap gap-1">
                    {loc.required_resources.map((req, i) => {
                      const label = Object.values(req.attributes)
                        .map((v) => formatAttributeValue(v))
                        .join(', ')
                      return (
                        <span
                          key={i}
                          className="inline-block rounded bg-brand-secondary/10 px-1.5 py-0.5 text-[10px] font-medium text-brand-secondary"
                        >
                          {req.quantity}x {label || 'any'}
                        </span>
                      )
                    })}
                  </div>
                )}
              </div>
            </Popup>
          </Marker>
        )
      })}
    </MapContainer>
  )
}
