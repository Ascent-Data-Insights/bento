import { Badge } from './badge'
import type { Location, Vehicle, Resource, SolveResponse, Route } from '../types/api'
import { SolveStatus } from '../types/api'
import { getRouteColor } from '../utils/route-colors'
import {
  locationLabels,
  locationDescriptions,
  resourceLabels,
  vehicleLabels,
  compartmentLabels,
  formatTime,
  formatAttributeValue,
} from '../data/grasscutting-demo'

interface DetailPanelProps {
  locations: Location[]
  vehicles: Vehicle[]
  resources: Resource[]
  solveResult: SolveResponse | null
  selectedRoute: string | null
  onSelectRoute: (vehicleId: string | null) => void
  onFocusLocation?: (locationId: string) => void
  onReset?: () => void
  moduleData?: Record<string, unknown>
}

function StatusBadge({ status }: { status: SolveStatus }) {
  const styles: Record<string, string> = {
    [SolveStatus.OPTIMAL]: 'bg-green-500 text-white',
    [SolveStatus.FEASIBLE]: 'bg-amber-500 text-white',
    [SolveStatus.INFEASIBLE]: 'bg-red-500 text-white',
    [SolveStatus.TIMEOUT]: 'bg-red-500 text-white',
    [SolveStatus.ERROR]: 'bg-red-500 text-white',
  }
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-bold tracking-wide ${styles[status] || 'bg-zinc-500 text-white'}`}>
      {status.toUpperCase()}
    </span>
  )
}

function PreSolveView({
  locations,
  vehicles,
  resources,
  moduleData,
  onFocusLocation,
}: {
  locations: Location[]
  vehicles: Vehicle[]
  resources: Resource[]
  moduleData?: Record<string, unknown>
  onFocusLocation?: (locationId: string) => void
}) {
  const jobSites = locations.filter(
    (l) => l.required_resources && l.required_resources.length > 0
  )
  const workers = resources.filter((r) => r.stays_with_vehicle && r.attributes?.skill)
  const mowers = resources.filter((r) => r.stays_with_vehicle && r.attributes?.type === 'mower')
  const consumed = resources.filter((r) => !r.stays_with_vehicle)

  // Get time windows from module data
  const twData = moduleData?.time_windows as { windows?: { location_id: string; earliest: number; latest: number }[] } | undefined
  const windowMap = new Map(
    (twData?.windows || []).map((w) => [w.location_id, w])
  )

  return (
    <div className="space-y-5">
      {/* Summary counts */}
      <div className="grid grid-cols-3 gap-2">
        <div className="rounded-lg bg-brand-primary/5 p-3 text-center">
          <div className="text-2xl font-bold text-brand-primary">{jobSites.length}</div>
          <div className="text-[11px] font-medium text-gray-500 uppercase tracking-wider">Jobs</div>
        </div>
        <div className="rounded-lg bg-brand-secondary/5 p-3 text-center">
          <div className="text-2xl font-bold text-brand-secondary">{vehicles.length}</div>
          <div className="text-[11px] font-medium text-gray-500 uppercase tracking-wider">Trucks</div>
        </div>
        <div className="rounded-lg bg-brand-accent/5 p-3 text-center">
          <div className="text-2xl font-bold text-brand-accent">{workers.length}</div>
          <div className="text-[11px] font-medium text-gray-500 uppercase tracking-wider">Crew</div>
        </div>
      </div>

      {/* Job list */}
      <div>
        <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">Today's Jobs</h4>
        <div className="space-y-2">
          {jobSites.map((loc) => {
            const tw = windowMap.get(loc.id)
            return (
              <button
                key={loc.id}
                onClick={() => onFocusLocation?.(loc.id)}
                className="w-full text-left rounded-lg border border-gray-200 p-3 hover:border-brand-secondary/40 hover:bg-brand-secondary/5 transition-colors cursor-pointer"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="font-medium text-sm text-gray-900 leading-tight">
                    {locationLabels[loc.id] || loc.id}
                  </div>
                  <span className="shrink-0 text-[11px] text-gray-400">
                    {loc.service_time} min
                  </span>
                </div>
                {locationDescriptions[loc.id] && (
                  <p className="text-xs text-gray-500 mt-0.5">{locationDescriptions[loc.id]}</p>
                )}
                {tw && (
                  <div className="mt-1 text-[11px] text-gray-500">
                    {formatTime(tw.earliest)} – {formatTime(tw.latest)}
                  </div>
                )}
                <div className="mt-1.5 flex flex-wrap gap-1">
                  {(loc.required_resources || []).map((req, i) => {
                    const label = Object.values(req.attributes).map((v) => formatAttributeValue(v)).join(', ')
                    const isSkill = 'skill' in req.attributes
                    return (
                      <Badge key={i} color={isSkill ? 'sky' : 'emerald'}>
                        {req.quantity}× {label}
                      </Badge>
                    )
                  })}
                </div>
              </button>
            )
          })}
        </div>
      </div>

      {/* Fleet summary */}
      <div>
        <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">Fleet</h4>
        <div className="space-y-1.5">
          {vehicles.map((v) => (
            <div key={v.id} className="flex items-center justify-between rounded-lg bg-gray-50 px-3 py-2">
              <span className="text-sm font-medium text-gray-700">
                {vehicleLabels[v.id] || v.id}
              </span>
              <div className="flex gap-1">
                {v.compartments.map((c, i) => (
                  <Badge key={i} color="zinc">{compartmentLabels[c.type] || c.type}</Badge>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Resources summary */}
      <div>
        <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">Resources</h4>
        <div className="flex flex-wrap gap-1.5">
          {workers.map((r) => (
            <Badge key={r.id} color="sky">{resourceLabels[r.id] || r.id}</Badge>
          ))}
          {mowers.map((r) => (
            <Badge key={r.id} color="emerald">{resourceLabels[r.id] || r.id}</Badge>
          ))}
          {consumed.map((r) => (
            <Badge key={r.id} color="amber">
              {resourceLabels[r.id] || r.id}{r.quantity && r.quantity > 1 ? ` ×${r.quantity}` : ''}
            </Badge>
          ))}
        </div>
      </div>
    </div>
  )
}

function PostSolveView({
  solveResult,
  routes,
  selectedRoute,
  onSelectRoute,
  onReset,
}: {
  solveResult: SolveResponse
  routes: Route[]
  selectedRoute: string | null
  onSelectRoute: (vehicleId: string | null) => void
  onReset?: () => void
}) {
  const arrivalTimes = (solveResult.module_results?.time_windows as { arrival_times?: Record<string, Record<string, number>> })?.arrival_times

  return (
    <div className="space-y-4">
      {/* Results summary */}
      <div className="rounded-lg bg-gradient-to-br from-brand-primary to-brand-primary/80 p-4 text-white">
        <div className="flex items-center justify-between mb-3">
          <StatusBadge status={solveResult.status} />
          <span className="text-xs opacity-70">{routes.length} routes</span>
        </div>
        <div className="text-3xl font-bold font-heading">
          {solveResult.objective_value?.toFixed(1)} <span className="text-base font-normal opacity-70">mi</span>
        </div>
        <div className="text-xs opacity-60 mt-0.5">Total distance</div>
      </div>

      {/* Re-plan button */}
      {onReset && (
        <button
          onClick={onReset}
          className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm font-medium text-gray-600 hover:bg-gray-50 hover:text-gray-900 transition-colors"
        >
          ← Back to planning
        </button>
      )}

      {/* Warnings */}
      {solveResult.unserved_locations.length > 0 && (
        <div className="rounded-lg bg-red-50 border border-red-200 p-3 text-sm text-red-700">
          {solveResult.unserved_locations.length} location(s) could not be served
        </div>
      )}

      {/* Route cards */}
      <div>
        <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">Routes</h4>
        <div className="space-y-2">
          {routes.map((route, idx) => {
            const color = getRouteColor(idx)
            const isSelected = selectedRoute === route.vehicle_id
            const vehicleArrivals = arrivalTimes?.[route.vehicle_id]

            return (
              <button
                key={route.vehicle_id}
                onClick={() => onSelectRoute(isSelected ? null : route.vehicle_id)}
                className={`w-full text-left rounded-lg border-2 p-3 transition-all ${
                  isSelected
                    ? 'border-current shadow-md'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
                style={isSelected ? { borderColor: color } : undefined}
              >
                <div className="flex items-center gap-2 mb-2">
                  <div
                    className="w-3 h-3 rounded-full shrink-0"
                    style={{ backgroundColor: color }}
                  />
                  <span className="font-semibold text-sm text-gray-900">
                    {vehicleLabels[route.vehicle_id] || route.vehicle_id}
                  </span>
                  <span className="ml-auto text-xs text-gray-400">
                    {route.total_distance.toFixed(1)} mi
                  </span>
                </div>

                {/* Stop sequence */}
                <div className="flex items-center gap-1 flex-wrap">
                  {route.stops.map((stop, si) => (
                    <span key={si} className="flex items-center gap-1">
                      {si > 0 && (
                        <svg className="w-3 h-3 text-gray-300 shrink-0" viewBox="0 0 12 12" fill="none">
                          <path d="M4.5 2.5L8 6L4.5 9.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                        </svg>
                      )}
                      <span
                        className={`text-xs px-1.5 py-0.5 rounded ${
                          stop.location_id === 'depot'
                            ? 'bg-brand-primary/10 text-brand-primary font-medium'
                            : 'bg-gray-100 text-gray-600'
                        }`}
                      >
                        {locationLabels[stop.location_id]?.split(' ')[0] || stop.location_id}
                      </span>
                    </span>
                  ))}
                </div>

                {/* Expanded detail when selected */}
                {isSelected && (
                  <div className="mt-3 pt-3 border-t border-gray-100 space-y-2">
                    {route.stops.map((stop, si) => {
                      const arrival = vehicleArrivals?.[stop.location_id]
                      return (
                        <div key={si} className="flex items-start gap-2 text-xs">
                          <div className="w-14 shrink-0 text-gray-400 text-right pt-0.5">
                            {arrival != null ? formatTime(arrival) : '—'}
                          </div>
                          <div
                            className="w-2 h-2 rounded-full mt-1 shrink-0"
                            style={{ backgroundColor: stop.location_id === 'depot' ? '#03344E' : color }}
                          />
                          <div className="flex-1">
                            <div className="font-medium text-gray-700">
                              {locationLabels[stop.location_id] || stop.location_id}
                            </div>
                            {stop.resources_picked_up.length > 0 && (
                              <div className="text-gray-500 mt-0.5">
                                ↑ {stop.resources_picked_up.map((r) => resourceLabels[r] || r).join(', ')}
                              </div>
                            )}
                            {stop.resources_dropped_off.length > 0 && (
                              <div className="text-gray-500 mt-0.5">
                                ↓ {stop.resources_dropped_off.map((r) => resourceLabels[r] || r).join(', ')}
                              </div>
                            )}
                          </div>
                        </div>
                      )
                    })}
                  </div>
                )}
              </button>
            )
          })}
        </div>
      </div>
    </div>
  )
}

export function DetailPanel({
  locations,
  vehicles,
  resources,
  solveResult,
  selectedRoute,
  onSelectRoute,
  onFocusLocation,
  onReset,
  moduleData,
}: DetailPanelProps) {
  return (
    <div className="h-full flex flex-col bg-white/95 backdrop-blur-sm border-l border-gray-200 shadow-lg">
      {/* Panel header */}
      <div className="px-4 py-3 border-b border-gray-100">
        <h3 className="font-heading font-semibold text-brand-primary">
          {solveResult ? 'Route Plan' : 'Dispatch'}
        </h3>
      </div>

      {/* Panel content */}
      <div className="flex-1 overflow-y-auto px-4 py-3">
        {solveResult ? (
          <PostSolveView
            solveResult={solveResult}
            routes={solveResult.routes}
            selectedRoute={selectedRoute}
            onSelectRoute={onSelectRoute}
            onReset={onReset}
          />
        ) : (
          <PreSolveView
            locations={locations}
            vehicles={vehicles}
            resources={resources}
            moduleData={moduleData}
            onFocusLocation={onFocusLocation}
          />
        )}
      </div>
    </div>
  )
}
