export interface ResourceRequirement {
  attributes: Record<string, string | string[] | boolean | number>
  quantity: number
}

export interface Location {
  id: string
  latitude: number
  longitude: number
  service_time?: number
  required_resources?: ResourceRequirement[]
}

export interface Compartment {
  type: string
  capacity: Record<string, number>
}

export interface Vehicle {
  id: string
  start_location_id: string
  end_location_id?: string | null
  compartments: Compartment[]
}

export interface Resource {
  id: string
  pickup_location_id: string
  dropoff_location_id?: string | null
  compartment_types: string[]
  capacity_consumption: Record<string, number>
  quantity?: number
  attributes?: Record<string, string | string[] | boolean | number>
  stays_with_vehicle?: boolean
}

export interface SolveRequest {
  locations: Location[]
  vehicles: Vehicle[]
  resources: Resource[]
  matrices: Record<string, Record<string, Record<string, number>>>
  module_data?: Record<string, unknown>
}

export interface RouteStop {
  location_id: string
  arrival_time?: number | null
  departure_time?: number | null
  resources_picked_up: string[]
  resources_dropped_off: string[]
}

export interface Route {
  vehicle_id: string
  stops: RouteStop[]
  total_distance: number
  total_time?: number | null
}

export const SolveStatus = {
  OPTIMAL: 'optimal',
  FEASIBLE: 'feasible',
  INFEASIBLE: 'infeasible',
  TIMEOUT: 'timeout',
  ERROR: 'error',
} as const

export type SolveStatus = (typeof SolveStatus)[keyof typeof SolveStatus]

export interface SolveResponse {
  status: SolveStatus
  objective_value: number | null
  routes: Route[]
  unserved_locations: string[]
  unserved_resources: string[]
  module_results: Record<string, unknown>
}

export interface DimensionSelections {
  origin_model: string
  fleet_composition: string
}

export interface ModuleConfig {
  key: string
  enabled?: boolean
  params?: Record<string, unknown>
}

export interface ClientProfile {
  id?: string | null
  tenant_id: string
  name: string
  dimensions: DimensionSelections
  objective: Record<string, number>
  modules?: ModuleConfig[]
}

export interface SolveRequestBody {
  request: SolveRequest
  profile: ClientProfile
}
