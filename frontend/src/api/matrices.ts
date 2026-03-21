import type { Location } from '../types/api'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

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
