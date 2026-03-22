import { useEffect, useState } from 'react'
import { motion } from 'motion/react'
import type {
  SolveResponse,
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
import { buildLabels, formatTime, formatAttributeValue } from '../utils/build-labels'
import { getRouteColor } from '../utils/route-colors'
import { Heading } from '../components/heading'
import { Badge } from '../components/badge'

function getTodayDate(): string {
  const d = new Date()
  return d.toISOString().split('T')[0]
}

function formatDisplayDate(isoDate: string): string {
  const [year, month, day] = isoDate.split('-').map(Number)
  const d = new Date(year, month - 1, day)
  return d.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })
}

interface WorkerStop {
  stopNumber: number
  locationId: string
  locationName: string
  arrivalTime: number | null
  departureTime: number | null
  jobName: string | null
  consumedResourcesDropped: string[]
}

interface WorkerSchedule {
  workerId: string
  workerName: string
  vehicleId: string
  vehicleName: string
  routeIndex: number
  attributes: Record<string, string | string[] | boolean | number>
  stops: WorkerStop[]
}

function buildCrewData(
  solveResult: SolveResponse,
  resources: ResourceResponse[],
  labels: DisplayLabels,
  jobs: JobResponse[],
): { assigned: WorkerSchedule[]; unassigned: ResourceResponse[] } {
  const workers = resources.filter((r) => r.stays_with_vehicle === true)
  const workerIdSet = new Set(workers.map((w) => w.id))

  const jobByLocation = new Map(jobs.map((j) => [j.location_id, j]))

  // Workers not consumed — they don't have dropoff_location_ids in the route stops
  // They appear in resources_picked_up at their pickup stop
  const assignedWorkerIds = new Set<string>()
  const schedules: WorkerSchedule[] = []

  solveResult.routes.forEach((route, routeIndex) => {
    // Find all worker IDs that appear in this route's resources_picked_up
    const routeWorkerIds = new Set<string>()
    route.stops.forEach((stop) => {
      stop.resources_picked_up.forEach((rid) => {
        if (workerIdSet.has(rid)) routeWorkerIds.add(rid)
      })
    })

    if (routeWorkerIds.size === 0) return

    // Build job stop itinerary (exclude first and last stops — depot start/return)
    const jobStops = route.stops.slice(1, route.stops.length - 1)

    const stops: WorkerStop[] = jobStops.map((stop, idx) => {
      const job = jobByLocation.get(stop.location_id) ?? null

      // Find consumed resources (not workers) dropped off at this stop
      const consumedDropped = stop.resources_dropped_off
        .filter((rid) => !workerIdSet.has(rid))
        .map((rid) => labels.resources[rid] ?? rid)

      return {
        stopNumber: idx + 1,
        locationId: stop.location_id,
        locationName: labels.locations[stop.location_id] ?? stop.location_id,
        arrivalTime: stop.arrival_time ?? null,
        departureTime: stop.departure_time ?? null,
        jobName: job?.name ?? null,
        consumedResourcesDropped: consumedDropped,
      }
    })

    routeWorkerIds.forEach((workerId) => {
      assignedWorkerIds.add(workerId)
      const workerResource = workers.find((w) => w.id === workerId)
      if (!workerResource) return

      schedules.push({
        workerId,
        workerName: labels.resources[workerId] ?? workerId,
        vehicleId: route.vehicle_id,
        vehicleName: labels.vehicles[route.vehicle_id] ?? route.vehicle_id,
        routeIndex,
        attributes: workerResource.attributes ?? {},
        stops,
      })
    })
  })

  const unassigned = workers.filter((w) => !assignedWorkerIds.has(w.id))

  return { assigned: schedules, unassigned }
}

export function CrewSchedulePage() {
  const { activeTenant, loading: tenantLoading } = useTenant()
  const [dataLoading, setDataLoading] = useState(true)
  const [solveLoading, setSolveLoading] = useState(false)
  const [solveResult, setSolveResult] = useState<SolveResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const [resources, setResources] = useState<ResourceResponse[]>([])
  const [jobs, setJobs] = useState<JobResponse[]>([])
  const [labels, setLabels] = useState<DisplayLabels | null>(null)

  const todayDate = getTodayDate()

  useEffect(() => {
    if (!activeTenant) return

    setSolveResult(null)
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

        if (cancelled) return

        setResources(ress)
        setJobs(jbs)
        setLabels(buildLabels(locs, vehs, ress, jbs))
        setDataLoading(false)

        if (jbs.length === 0) return

        setSolveLoading(true)
        try {
          const result = await solveFromDb(activeTenant.id, todayDate)
          if (!cancelled) setSolveResult(result)
        } catch (solveErr) {
          if (!cancelled) setError(solveErr instanceof Error ? solveErr.message : 'Optimization failed')
        } finally {
          if (!cancelled) setSolveLoading(false)
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

  const isLoading = tenantLoading || dataLoading || solveLoading

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="flex items-center gap-3 text-gray-500">
          <svg className="animate-spin h-5 w-5 text-brand-secondary" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          {dataLoading ? 'Loading data…' : 'Optimizing routes…'}
        </div>
      </div>
    )
  }

  const crewData =
    solveResult && labels
      ? buildCrewData(solveResult, resources, labels, jobs)
      : null

  const assignedCount = crewData?.assigned.length ?? 0
  const unassignedCount = crewData?.unassigned.length ?? 0

  return (
    <div className="px-1">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25 }}
        className="flex flex-col gap-1 mb-6"
      >
        <Heading className="font-heading">Crew Schedule</Heading>
        <p className="text-sm text-zinc-500">{formatDisplayDate(todayDate)}</p>

        {crewData && (
          <div className="flex items-center gap-3 mt-2">
            <Badge color="green">{assignedCount} assigned</Badge>
            {unassignedCount > 0 && (
              <Badge color="zinc">{unassignedCount} unassigned</Badge>
            )}
          </div>
        )}
      </motion.div>

      {/* Error banner */}
      {error && (
        <motion.div
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-6 rounded-lg bg-red-50 border border-red-200 px-4 py-3 flex items-start gap-3"
        >
          <svg className="w-5 h-5 text-red-500 shrink-0 mt-0.5" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z" clipRule="evenodd" />
          </svg>
          <div>
            <p className="text-sm font-medium text-red-800">Error</p>
            <p className="text-xs text-red-600 mt-0.5">{error}</p>
          </div>
        </motion.div>
      )}

      {/* No jobs state */}
      {!error && jobs.length === 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="py-16 text-center text-zinc-400 text-sm"
        >
          No jobs scheduled for today
        </motion.div>
      )}

      {/* Crew grid */}
      {crewData && (
        <div className="space-y-8">
          {/* Assigned workers */}
          {crewData.assigned.length > 0 && (
            <section>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {crewData.assigned.map((worker, i) => (
                  <WorkerCard key={worker.workerId} worker={worker} index={i} />
                ))}
              </div>
            </section>
          )}

          {/* Unassigned workers */}
          {crewData.unassigned.length > 0 && (
            <section>
              <h2 className="text-sm font-semibold text-zinc-500 uppercase tracking-wide mb-3">
                Unassigned
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {crewData.unassigned.map((worker, i) => (
                  <UnassignedCard key={worker.id} worker={worker} index={i} />
                ))}
              </div>
            </section>
          )}
        </div>
      )}
    </div>
  )
}

function WorkerCard({ worker, index }: { worker: WorkerSchedule; index: number }) {
  const accentColor = getRouteColor(worker.routeIndex)
  const attrEntries = Object.entries(worker.attributes)

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2, delay: index * 0.04 }}
      className="rounded-xl border border-zinc-200 bg-white shadow-sm overflow-hidden"
      style={{ borderLeftWidth: 4, borderLeftColor: accentColor }}
    >
      {/* Card header */}
      <div className="px-4 pt-4 pb-3">
        <div className="flex items-start justify-between gap-2">
          <h3 className="font-heading text-base font-semibold text-zinc-900 leading-tight">
            {worker.workerName}
          </h3>
          <Badge color="blue">{worker.vehicleName}</Badge>
        </div>

        {attrEntries.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-2">
            {attrEntries.map(([key, value]) => (
              <Badge key={key} color="zinc">
                {formatAttributeValue(value)}
              </Badge>
            ))}
          </div>
        )}
      </div>

      {/* Stop itinerary */}
      {worker.stops.length > 0 ? (
        <ol className="border-t border-zinc-100 divide-y divide-zinc-100">
          {worker.stops.map((stop) => (
            <li key={stop.locationId + stop.stopNumber} className="px-4 py-3">
              <div className="flex items-start gap-3">
                <span
                  className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[10px] font-bold text-white"
                  style={{ backgroundColor: accentColor }}
                >
                  {stop.stopNumber}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-zinc-800 leading-tight truncate">
                    {stop.locationName}
                  </p>
                  {stop.jobName && (
                    <p className="text-xs text-zinc-500 mt-0.5 truncate">{stop.jobName}</p>
                  )}
                  <div className="flex items-center gap-2 mt-1">
                    {stop.arrivalTime != null && (
                      <span className="text-xs text-zinc-400">
                        Arrive {formatTime(stop.arrivalTime)}
                      </span>
                    )}
                    {stop.arrivalTime != null && stop.departureTime != null && (
                      <span className="text-xs text-zinc-300">·</span>
                    )}
                    {stop.departureTime != null && (
                      <span className="text-xs text-zinc-400">
                        Depart {formatTime(stop.departureTime)}
                      </span>
                    )}
                  </div>
                  {stop.consumedResourcesDropped.length > 0 && (
                    <p className="text-xs text-zinc-400 mt-1">
                      Drops: {stop.consumedResourcesDropped.join(', ')}
                    </p>
                  )}
                </div>
              </div>
            </li>
          ))}
        </ol>
      ) : (
        <p className="px-4 pb-4 text-xs text-zinc-400 border-t border-zinc-100 pt-3">
          No job stops on this route
        </p>
      )}
    </motion.div>
  )
}

function UnassignedCard({ worker, index }: { worker: ResourceResponse; index: number }) {
  const attrEntries = Object.entries(worker.attributes ?? {})

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2, delay: index * 0.04 }}
      className="rounded-xl border border-zinc-200 bg-zinc-50 shadow-sm overflow-hidden"
      style={{ borderLeftWidth: 4, borderLeftColor: '#d4d4d8' }}
    >
      <div className="px-4 py-4">
        <div className="flex items-start justify-between gap-2">
          <h3 className="font-heading text-base font-semibold text-zinc-500 leading-tight">
            {worker.name}
          </h3>
          <Badge color="zinc">Unassigned</Badge>
        </div>
        {attrEntries.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-2">
            {attrEntries.map(([key, value]) => (
              <Badge key={key} color="zinc">
                {formatAttributeValue(value)}
              </Badge>
            ))}
          </div>
        )}
      </div>
    </motion.div>
  )
}
