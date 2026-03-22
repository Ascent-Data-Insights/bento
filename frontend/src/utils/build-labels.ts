import type { LocationResponse, VehicleResponse, ResourceResponse, JobResponse, DisplayLabels } from '../types/api'

export const attributeLabels: Record<string, string> = {
  mower_operator: 'Mower Operator',
  mower: 'Mower',
  hedger: 'Hedger',
  mulch: 'Mulch',
}

export const compartmentLabels: Record<string, string> = {
  cab: 'Cab',
  bed: 'Truck Bed',
  trailer: 'Trailer',
}

export function formatAttributeValue(value: string | string[] | boolean | number): string {
  if (typeof value === 'string') return attributeLabels[value] || value
  if (Array.isArray(value)) return value.map((v) => attributeLabels[v] || v).join(', ')
  return String(value)
}

export function formatTime(minutes: number): string {
  const h = Math.floor(minutes / 60)
  const m = Math.round(minutes % 60)
  const period = h >= 12 ? 'PM' : 'AM'
  const hour = h > 12 ? h - 12 : h === 0 ? 12 : h
  return `${hour}:${m.toString().padStart(2, '0')} ${period}`
}

export function buildLabels(
  locations: LocationResponse[],
  vehicles: VehicleResponse[],
  resources: ResourceResponse[],
  jobs: JobResponse[],
): DisplayLabels {
  const jobDescriptions = new Map(
    jobs.filter((j) => j.description).map((j) => [j.location_id, j.description!])
  )

  return {
    locations: Object.fromEntries(locations.map((l) => [l.id, l.name])),
    locationDescriptions: Object.fromEntries(
      locations.map((l) => [l.id, jobDescriptions.get(l.id) || ''])
    ),
    vehicles: Object.fromEntries(vehicles.map((v) => [v.id, v.name])),
    resources: Object.fromEntries(resources.map((r) => [r.id, r.name])),
  }
}
