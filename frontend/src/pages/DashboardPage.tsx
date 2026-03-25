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
import { useTour } from '../contexts/TourContext'
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
  const { registerPrepareHandler } = useTour()
  const [dataLoading, setDataLoading] = useState(true)
  const [solveResult, setSolveResult] = useState<SolveResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedRoute, setSelectedRoute] = useState<string | null>(null)
  const [focusLocation, setFocusLocation] = useState<string | null>(null)
  const [sheetOpen, setSheetOpen] = useState(false)

  // API data
  const [locations, setLocations] = useState<LocationResponse[]>([])
  const [vehicles, setVehicles] = useState<VehicleResponse[]>([])
  const [resources, setResources] = useState<ResourceResponse[]>([])
  const [jobs, setJobs] = useState<JobResponse[]>([])
  const [labels, setLabels] = useState<DisplayLabels | null>(null)

  const todayDate = getTodayDate()

  // Register tour handler: open the bottom sheet when the tour needs to show the detail panel
  useEffect(() => {
    return registerPrepareHandler('sheet', () => setSheetOpen(true))
  }, [registerPrepareHandler])

  useEffect(() => {
    if (!activeTenant) return

    // Reset state on tenant change
    setSolveResult(null)
    setSelectedRoute(null)
    setFocusLocation(null)
    setError(null)
    setDataLoading(true)
    setSheetOpen(false)

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
      // Auto-open sheet on mobile after solve completes
      setSheetOpen(true)
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

  const panelLabel = solveResult ? 'Route Plan' : 'Dispatch'

  return (
    <div className="absolute inset-0 flex flex-col lg:flex-row">
      {/* Map area */}
      <div className="flex-1 relative min-h-0" data-tour="dashboard-map">
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

        {/* Floating optimize button */}
        {!solveResult && !dataLoading && jobs.length > 0 && (
          <div
            className="absolute z-[450] left-1/2 -translate-x-1/2 bottom-24 lg:bottom-6"
            data-tour="optimize-button"
          >
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
          <div className="absolute top-4 left-1/2 -translate-x-1/2 z-[450] max-w-md w-full px-4">
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

        {/* Mobile sheet toggle tab — visible when sheet is closed */}
        <button
          onClick={() => setSheetOpen(true)}
          className={`
            lg:hidden absolute bottom-0 left-1/2 -translate-x-1/2 z-[490]
            flex items-center gap-2 bg-white rounded-t-2xl shadow-lg
            px-6 py-2 border border-b-0 border-gray-200
            text-sm font-semibold text-brand-primary
            transition-opacity duration-200
            ${sheetOpen ? 'opacity-0 pointer-events-none' : 'opacity-100'}
          `}
          aria-label="Open dispatch panel"
        >
          <svg className="w-4 h-4" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M10 15a.75.75 0 01-.53-.22l-4.25-4.25a.75.75 0 111.06-1.06L10 13.19l3.72-3.72a.75.75 0 111.06 1.06l-4.25 4.25A.75.75 0 0110 15z" clipRule="evenodd" />
          </svg>
          {panelLabel}
        </button>
      </div>

      {/* Detail Panel — side panel on desktop, bottom sheet on mobile */}
      <div
        data-tour="detail-panel"
        className={`
          lg:w-[360px] lg:shrink-0 lg:relative lg:translate-y-0 lg:h-auto lg:opacity-100
          fixed bottom-0 left-0 right-0 z-[500]
          h-[72vh]
          transition-transform duration-300 ease-in-out
          ${sheetOpen ? 'translate-y-0' : 'translate-y-full'}
          lg:transition-none lg:translate-y-0
        `}
      >
        {/* Sheet drag handle — mobile only */}
        <button
          onClick={() => setSheetOpen(false)}
          className="lg:hidden w-full flex flex-col items-center pt-2 pb-1 bg-white rounded-t-2xl border-t border-x border-gray-200 cursor-pointer"
          aria-label="Close panel"
        >
          <div className="w-10 h-1 rounded-full bg-gray-300 mb-1" />
          <span className="text-xs text-gray-400">{panelLabel} — tap to close</span>
        </button>

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

      {/* Mobile backdrop — tap outside sheet to close */}
      {sheetOpen && (
        <div
          className="lg:hidden fixed inset-0 z-[495] bg-black/20"
          onClick={() => setSheetOpen(false)}
          aria-hidden="true"
        />
      )}
    </div>
  )
}
