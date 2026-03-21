import type { SolveRequestBody, SolveResponse } from '../types/api'

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
