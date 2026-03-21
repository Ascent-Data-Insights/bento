import { useEffect, useRef } from 'react'
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from 'react-leaflet'
import L from 'leaflet'
import type { Location, Route } from '../types/api'
import { getRouteColor } from '../utils/route-colors'
import { locationLabels } from '../data/grasscutting-demo'

// Custom marker icons using divIcon (no image asset issues)
function createMarkerIcon(color: string, size: number = 12, pulse: boolean = false) {
  return L.divIcon({
    className: '',
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    html: `
      <div style="
        width: ${size}px;
        height: ${size}px;
        background: ${color};
        border: 2.5px solid white;
        border-radius: 50%;
        box-shadow: 0 1px 4px rgba(0,0,0,0.3);
        ${pulse ? 'animation: pulse 2s infinite;' : ''}
      "></div>
    `,
  })
}

const depotIcon = createMarkerIcon('#03344E', 16)
const jobIcon = createMarkerIcon('#4785BF', 12)
const jobActiveIcon = createMarkerIcon('#FB8500', 14)

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
}

export function RouteMap({
  locations,
  depotIds,
  routes,
  selectedRoute,
  onSelectRoute,
  focusLocationId,
}: RouteMapProps) {
  const locationMap = new Map(locations.map((l) => [l.id, l]))

  // Build route polyline data
  const routeLines = (routes || []).map((route, idx) => {
    const coords: [number, number][] = route.stops
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

  // Locations that are on the selected route
  const selectedStops = new Set<string>()
  if (selectedRoute && routes) {
    const route = routes.find((r) => r.vehicle_id === selectedRoute)
    if (route) {
      route.stops.forEach((s) => selectedStops.add(s.location_id))
    }
  }

  return (
    <MapContainer
      center={[39.14, -84.50]}
      zoom={11}
      className="h-full w-full"
      zoomControl={false}
    >
      <TileLayer
        attribution='&copy; <a href="https://carto.com/">CARTO</a>'
        url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
      />
      <FitBounds locations={locations} />
      <FlyToLocation locationId={focusLocationId ?? null} locations={locations} />

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
        const isOnSelectedRoute = selectedStops.has(loc.id)
        const icon = isDepot
          ? depotIcon
          : isOnSelectedRoute
            ? jobActiveIcon
            : jobIcon

        return (
          <Marker
            key={loc.id}
            position={[loc.latitude, loc.longitude]}
            icon={icon}
          >
            <Popup>
              <div className="font-body text-sm min-w-[160px]">
                <div className="font-semibold text-brand-primary">
                  {locationLabels[loc.id] || loc.id}
                </div>
                {isDepot && (
                  <div className="text-xs text-gray-500 mt-0.5">Depot</div>
                )}
                {loc.service_time ? (
                  <div className="text-xs text-gray-600 mt-1">
                    Service: {loc.service_time} min
                  </div>
                ) : null}
                {loc.required_resources && loc.required_resources.length > 0 && (
                  <div className="mt-1.5 flex flex-wrap gap-1">
                    {loc.required_resources.map((req, i) => {
                      const label = Object.entries(req.attributes)
                        .map(([, v]) => v)
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
