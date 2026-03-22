import type {
  SolveRequestBody,
  SolveResponse,
  TenantResponse,
  LocationResponse,
  VehicleResponse,
  ResourceResponse,
  JobResponse,
} from '../types/api'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export async function solveRoutes(body: SolveRequestBody): Promise<SolveResponse> {
  const response = await fetch(`${API_BASE}/api/v1/solve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    const detail = errorData?.detail
    const message =
      typeof detail === 'string'
        ? detail
        : detail?.message || `Solver returned ${response.status}`
    throw new Error(message)
  }

  return response.json()
}

export async function fetchTenants(): Promise<TenantResponse[]> {
  const response = await fetch(`${API_BASE}/api/v1/tenants`)
  if (!response.ok) throw new Error(`Failed to fetch tenants: ${response.status}`)
  return response.json()
}

export async function fetchLocations(tenantId: string): Promise<LocationResponse[]> {
  const response = await fetch(`${API_BASE}/api/v1/tenants/${tenantId}/locations`)
  if (!response.ok) throw new Error(`Failed to fetch locations: ${response.status}`)
  return response.json()
}

export async function fetchVehicles(tenantId: string): Promise<VehicleResponse[]> {
  const response = await fetch(`${API_BASE}/api/v1/tenants/${tenantId}/vehicles`)
  if (!response.ok) throw new Error(`Failed to fetch vehicles: ${response.status}`)
  return response.json()
}

export async function fetchResources(tenantId: string): Promise<ResourceResponse[]> {
  const response = await fetch(`${API_BASE}/api/v1/tenants/${tenantId}/resources`)
  if (!response.ok) throw new Error(`Failed to fetch resources: ${response.status}`)
  return response.json()
}

export async function fetchJobs(tenantId: string, date: string): Promise<JobResponse[]> {
  const response = await fetch(`${API_BASE}/api/v1/tenants/${tenantId}/jobs?date=${date}`)
  if (!response.ok) throw new Error(`Failed to fetch jobs: ${response.status}`)
  return response.json()
}

export async function solveFromDb(tenantId: string, date: string): Promise<SolveResponse> {
  const response = await fetch(`${API_BASE}/api/v1/tenants/${tenantId}/solve?date=${date}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  })
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    const detail = errorData?.detail
    const message = typeof detail === 'string' ? detail : detail?.message || `Solver returned ${response.status}`
    throw new Error(message)
  }
  return response.json()
}
