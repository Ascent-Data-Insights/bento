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

export interface TenantResponse {
  id: string
  name: string
  industry: string
  branding: Record<string, unknown> | null
  created_at: string
  updated_at: string
}

export interface LocationResponse {
  id: string
  tenant_id: string
  name: string
  latitude: number
  longitude: number
  service_time: number
  required_resources: ResourceRequirement[]
  external_id: string | null
  created_at: string
  updated_at: string
}

export interface VehicleResponse {
  id: string
  tenant_id: string
  name: string
  start_location_id: string
  end_location_id: string | null
  compartments: Compartment[]
  is_active: boolean
  external_id: string | null
  created_at: string
  updated_at: string
}

export interface ResourceResponse {
  id: string
  tenant_id: string
  name: string
  pickup_location_id: string
  dropoff_location_id: string | null
  compartment_types: string[]
  capacity_consumption: Record<string, number>
  quantity: number
  stays_with_vehicle: boolean
  attributes: Record<string, string | string[] | boolean | number>
  is_active: boolean
  external_id: string | null
  created_at: string
  updated_at: string
}

export interface JobResponse {
  id: string
  tenant_id: string
  location_id: string
  date: string
  name: string
  description: string | null
  service_time: number
  required_resources: ResourceRequirement[]
  time_window_earliest: number | null
  time_window_latest: number | null
  status: string
  external_id: string | null
  created_at: string
  updated_at: string
}

export interface DisplayLabels {
  locations: Record<string, string>
  locationDescriptions: Record<string, string>
  vehicles: Record<string, string>
  resources: Record<string, string>
}

export interface ModuleMetadata {
  key: string
  name: string
  description: string
  dependencies: string[]
  conflicts: string[]
  required_dimensions: Record<string, string[]>
  implemented: boolean
}

export interface OnboardRequest {
  tenant_name: string
  industry: string
  profile_name: string
  dimensions: DimensionSelections
  objective: Record<string, number>
  modules: ModuleConfig[]
}

export interface OnboardResponse {
  tenant: TenantResponse
  profile: Record<string, unknown>
}
