import { useEffect, useState } from 'react'
import type {
  SolveResponse,
  Location,
  Vehicle,
  Resource,
  LocationResponse,
  VehicleResponse,
  ResourceResponse,
  JobResponse,
  DisplayLabels,
} from '../types/api'
import {
  fetchLocations,
  fetchVehicles,
  fetchResources,
  fetchJobs,
  solveFromDb,
} from '../api/client'
import { useTenant } from '../contexts/TenantContext'
import { buildLabels } from '../utils/build-labels'
import { RouteMap } from '../components/RouteMap'
import { DetailPanel } from '../components/DetailPanel'

function getTodayDate(): string {
  const d = new Date()
  return d.toISOString().split('T')[0]
}

// Convert API LocationResponse to solver Location type for the map
// Merges job data (requirements, service_time) onto locations for today's view
function toMapLocations(locs: LocationResponse[], jobs: JobResponse[]): Location[] {
  const jobByLocation = new Map(jobs.map((j) => [j.location_id, j]))
  return locs.map((l) => {
    const job = jobByLocation.get(l.id)
    return {
      id: l.id,
      latitude: l.latitude,
      longitude: l.longitude,
      service_time: job?.service_time ?? l.service_time,
      required_resources: job?.required_resources ?? l.required_resources,
    }
  })
}

// Convert API VehicleResponse to solver Vehicle type
function toMapVehicles(vehicles: VehicleResponse[]): Vehicle[] {
  return vehicles.map((v) => ({
    id: v.id,
    start_location_id: v.start_location_id,
    end_location_id: v.end_location_id,
    compartments: v.compartments,
  }))
}

// Convert API ResourceResponse to solver Resource type
function toMapResources(resources: ResourceResponse[]): Resource[] {
  return resources.map((r) => ({
    id: r.id,
    pickup_location_id: r.pickup_location_id,
    dropoff_location_id: r.dropoff_location_id,
    compartment_types: r.compartment_types,
    capacity_consumption: r.capacity_consumption,
    quantity: r.quantity,
    stays_with_vehicle: r.stays_with_vehicle,
    attributes: r.attributes,
  }))
}

// Build module_data for pre-solve display from jobs
function buildModuleData(jobs: JobResponse[]): Record<string, unknown> {
  const windows = jobs
    .filter((j) => j.time_window_earliest != null && j.time_window_latest != null)
    .map((j) => ({
      location_id: j.location_id,
      earliest: j.time_window_earliest!,
      latest: j.time_window_latest!,
    }))
  return {
    time_windows: { windows },
  }
}

export function DashboardPage() {
  const { activeTenant, loading: tenantLoading } = useTenant()
  const [dataLoading, setDataLoading] = useState(true)
  const [solveResult, setSolveResult] = useState<SolveResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedRoute, setSelectedRoute] = useState<string | null>(null)
  const [focusLocation, setFocusLocation] = useState<string | null>(null)

  // API data
  const [locations, setLocations] = useState<LocationResponse[]>([])
  const [vehicles, setVehicles] = useState<VehicleResponse[]>([])
  const [resources, setResources] = useState<ResourceResponse[]>([])
  const [jobs, setJobs] = useState<JobResponse[]>([])
  const [labels, setLabels] = useState<DisplayLabels | null>(null)

  const todayDate = getTodayDate()

  useEffect(() => {
    if (!activeTenant) return

    // Reset state on tenant change
    setSolveResult(null)
    setSelectedRoute(null)
    setFocusLocation(null)
    setError(null)
    setDataLoading(true)

    let cancelled = false
    const load = async () => {
      try {
        const [locs, vehs, ress, jbs] = await Promise.all([
          fetchLocations(activeTenant.id),
          fetchVehicles(activeTenant.id),
          fetchResources(activeTenant.id),
          fetchJobs(activeTenant.id, todayDate),
        ])
        if (!cancelled) {
          setLocations(locs)
          setVehicles(vehs)
          setResources(ress)
          setJobs(jbs)
          setLabels(buildLabels(locs, vehs, ress, jbs))
          setDataLoading(false)
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load data')
          setDataLoading(false)
        }
      }
    }
    load()
    return () => { cancelled = true }
  }, [activeTenant?.id, todayDate])

  const depotIds = new Set(
    vehicles.flatMap((v) =>
      [v.start_location_id, v.end_location_id].filter((id): id is string => id != null)
    )
  )

  const handleReset = () => {
    setSolveResult(null)
    setSelectedRoute(null)
    setFocusLocation(null)
    setError(null)
  }

  const handleOptimize = async () => {
    if (!activeTenant) return
    setLoading(true)
    setError(null)
    setSolveResult(null)
    setSelectedRoute(null)
    setFocusLocation(null)

    try {
      const result = await solveFromDb(activeTenant.id, todayDate)
      setSolveResult(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Optimization failed')
    } finally {
      setLoading(false)
    }
  }

  // Convert to map-compatible types
  const mapLocations = toMapLocations(locations, jobs)
  const mapVehicles = toMapVehicles(vehicles)
  const mapResources = toMapResources(resources)
  const moduleData = buildModuleData(jobs)

  if (tenantLoading || dataLoading) {
    return (
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="flex items-center gap-3 text-gray-500">
          <svg className="animate-spin h-5 w-5 text-brand-secondary" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          Loading...
        </div>
      </div>
    )
  }

  return (
    <div className="absolute inset-0 flex">
      {/* Map */}
      <div className="flex-1 relative">
        <RouteMap
          locations={mapLocations}
          depotIds={depotIds}
          routes={solveResult?.routes}
          selectedRoute={selectedRoute}
          onSelectRoute={setSelectedRoute}
          focusLocationId={focusLocation}
          labels={labels || { locations: {}, locationDescriptions: {}, vehicles: {}, resources: {} }}
        />

        {/* No jobs message */}
        {!dataLoading && jobs.length === 0 && !solveResult && (
          <div className="absolute top-4 left-1/2 -translate-x-1/2 z-[450]">
            <div className="rounded-lg bg-white/90 backdrop-blur-sm shadow-lg px-4 py-3 text-sm text-gray-600">
              No jobs scheduled for today
            </div>
          </div>
        )}

        {/* Floating optimize bar */}
        {!solveResult && !dataLoading && jobs.length > 0 && (
          <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-[450]">
            <button
              onClick={handleOptimize}
              disabled={loading}
              className={`
                inline-flex items-center gap-3 rounded-full px-8 py-4
                text-base font-bold text-white
                shadow-xl shadow-brand-accent/25
                transition-all duration-200
                ${loading
                  ? 'bg-brand-accent/70 cursor-wait scale-95'
                  : 'bg-brand-accent hover:bg-brand-accent/90 hover:shadow-2xl hover:shadow-brand-accent/30 hover:scale-[1.02] active:scale-[0.97]'
                }
              `}
            >
              {loading ? (
                <>
                  <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Optimizing…
                </>
              ) : (
                <>
                  <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z" clipRule="evenodd" />
                  </svg>
                  Optimize Routes
                </>
              )}
            </button>
          </div>
        )}

        {/* Error banner */}
        {error && (
          <div className="absolute top-4 left-1/2 -translate-x-1/2 z-[450] max-w-md w-full">
            <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 shadow-lg flex items-start gap-3">
              <svg className="w-5 h-5 text-red-500 shrink-0 mt-0.5" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z" clipRule="evenodd" />
              </svg>
              <div className="flex-1">
                <p className="text-sm font-medium text-red-800">Error</p>
                <p className="text-xs text-red-600 mt-0.5">{error}</p>
              </div>
              <button
                onClick={() => setError(null)}
                className="text-red-400 hover:text-red-600 transition-colors"
              >
                <svg className="w-4 h-4" viewBox="0 0 20 20" fill="currentColor">
                  <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
                </svg>
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Detail Panel */}
      <div className="w-[360px] shrink-0">
        <DetailPanel
          locations={mapLocations}
          vehicles={mapVehicles}
          resources={mapResources}
          solveResult={solveResult}
          selectedRoute={selectedRoute}
          onSelectRoute={setSelectedRoute}
          onFocusLocation={setFocusLocation}
          onReset={handleReset}
          labels={labels || { locations: {}, locationDescriptions: {}, vehicles: {}, resources: {} }}
          depotIds={depotIds}
          moduleData={moduleData}
        />
      </div>
    </div>
  )
}
