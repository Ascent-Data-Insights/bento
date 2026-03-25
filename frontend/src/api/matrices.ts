import type { Location, Route } from '../types/api'

const API_BASE = import.meta.env.VITE_API_URL || ''
const OSRM_BASE = import.meta.env.VITE_OSRM_URL || 'https://router.project-osrm.org'

export async function computeMatrices(
  locations: Location[]
): Promise<{ distance: Record<string, Record<string, number>>; time: Record<string, Record<string, number>> }> {
  const response = await fetch(`${API_BASE}/api/v1/matrices`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      locations: locations.map((l) => ({
        id: l.id,
        latitude: l.latitude,
        longitude: l.longitude,
      })),
    }),
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw new Error(errorData?.detail || `Matrix computation failed: ${response.status}`)
  }

  const data = await response.json()
  return data.matrices
}

/**
 * Decode an OSRM encoded polyline string into [lat, lng] pairs.
 * Uses the standard polyline encoding algorithm (precision 5).
 */
function decodePolyline(encoded: string): [number, number][] {
  const points: [number, number][] = []
  let index = 0
  let lat = 0
  let lng = 0

  while (index < encoded.length) {
    let shift = 0
    let result = 0
    let byte: number

    do {
      byte = encoded.charCodeAt(index++) - 63
      result |= (byte & 0x1f) << shift
      shift += 5
    } while (byte >= 0x20)
    lat += result & 1 ? ~(result >> 1) : result >> 1

    shift = 0
    result = 0
    do {
      byte = encoded.charCodeAt(index++) - 63
      result |= (byte & 0x1f) << shift
      shift += 5
    } while (byte >= 0x20)
    lng += result & 1 ? ~(result >> 1) : result >> 1

    points.push([lat / 1e5, lng / 1e5])
  }

  return points
}

/**
 * Fetch the actual road geometry for a route's stops from OSRM.
 * Returns an array of [lat, lng] points following the roads.
 */
export async function fetchRouteGeometry(
  route: Route,
  locationMap: Map<string, Location>
): Promise<[number, number][]> {
  const coords = route.stops
    .map((stop) => {
      const loc = locationMap.get(stop.location_id)
      return loc ? `${loc.longitude},${loc.latitude}` : null
    })
    .filter((c): c is string => c !== null)

  if (coords.length < 2) return []

  const url = `${OSRM_BASE}/route/v1/driving/${coords.join(';')}?overview=full&geometries=polyline`

  try {
    const response = await fetch(url)
    if (!response.ok) return fallbackStraightLine(route, locationMap)

    const data = await response.json()
    if (data.code !== 'Ok' || !data.routes?.[0]?.geometry) {
      return fallbackStraightLine(route, locationMap)
    }

    return decodePolyline(data.routes[0].geometry)
  } catch {
    return fallbackStraightLine(route, locationMap)
  }
}

function fallbackStraightLine(
  route: Route,
  locationMap: Map<string, Location>
): [number, number][] {
  return route.stops
    .map((stop) => {
      const loc = locationMap.get(stop.location_id)
      return loc ? [loc.latitude, loc.longitude] as [number, number] : null
    })
    .filter((c): c is [number, number] => c !== null)
}
