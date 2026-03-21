import type { SolveRequestBody, Location, Vehicle, Resource } from '../types/api'

// Cincinnati, OH area coordinates
export const demoLocations: Location[] = [
  {
    id: 'depot',
    latitude: 39.2361,
    longitude: -84.3816,
    service_time: 0,
  },
  {
    id: 'johnson_residence',
    latitude: 39.1390,
    longitude: -84.4440,
    service_time: 45,
    required_resources: [
      { attributes: { skill: 'mower_operator' }, quantity: 1 },
      { attributes: { type: 'mower' }, quantity: 1 },
    ],
  },
  {
    id: 'oak_hills_community',
    latitude: 39.1580,
    longitude: -84.6050,
    service_time: 90,
    required_resources: [
      { attributes: { skill: 'mower_operator' }, quantity: 1 },
      { attributes: { type: 'mower' }, quantity: 1 },
    ],
  },
  {
    id: 'riverside_park',
    latitude: 39.0850,
    longitude: -84.3700,
    service_time: 60,
    required_resources: [
      { attributes: { skill: 'mower_operator' }, quantity: 1 },
      { attributes: { type: 'mower' }, quantity: 1 },
    ],
  },
  {
    id: 'summit_ave',
    latitude: 39.1090,
    longitude: -84.4970,
    service_time: 30,
    required_resources: [
      { attributes: { skill: 'mower_operator' }, quantity: 1 },
    ],
  },
  {
    id: 'crestview_estates',
    latitude: 39.0540,
    longitude: -84.6600,
    service_time: 75,
    required_resources: [
      { attributes: { skill: 'mower_operator' }, quantity: 1 },
      { attributes: { type: 'mower' }, quantity: 1 },
    ],
  },
]

export const demoVehicles: Vehicle[] = [
  {
    id: 'truck_alpha',
    start_location_id: 'depot',
    end_location_id: 'depot',
    compartments: [
      { type: 'cab', capacity: { seats: 3 } },
      { type: 'bed', capacity: { weight: 600, volume: 40 } },
    ],
  },
  {
    id: 'truck_bravo',
    start_location_id: 'depot',
    end_location_id: 'depot',
    compartments: [
      { type: 'cab', capacity: { seats: 2 } },
      { type: 'bed', capacity: { weight: 400, volume: 25 } },
    ],
  },
  {
    id: 'truck_charlie',
    start_location_id: 'depot',
    end_location_id: 'depot',
    compartments: [
      { type: 'cab', capacity: { seats: 3 } },
      { type: 'bed', capacity: { weight: 500, volume: 35 } },
      { type: 'trailer', capacity: { weight: 800, volume: 60 } },
    ],
  },
]

export const demoResources: Resource[] = [
  // Workers (stays with vehicle)
  {
    id: 'mike',
    pickup_location_id: 'depot',
    compartment_types: ['cab'],
    capacity_consumption: { seats: 1 },
    attributes: { skill: 'mower_operator' },
    stays_with_vehicle: true,
  },
  {
    id: 'dave',
    pickup_location_id: 'depot',
    compartment_types: ['cab'],
    capacity_consumption: { seats: 1 },
    attributes: { skill: 'mower_operator' },
    stays_with_vehicle: true,
  },
  {
    id: 'sarah',
    pickup_location_id: 'depot',
    compartment_types: ['cab'],
    capacity_consumption: { seats: 1 },
    attributes: { skill: 'mower_operator' },
    stays_with_vehicle: true,
  },
  {
    id: 'tom',
    pickup_location_id: 'depot',
    compartment_types: ['cab'],
    capacity_consumption: { seats: 1 },
    attributes: { skill: 'mower_operator' },
    stays_with_vehicle: true,
  },
  {
    id: 'lisa',
    pickup_location_id: 'depot',
    compartment_types: ['cab'],
    capacity_consumption: { seats: 1 },
    attributes: { skill: 'mower_operator' },
    stays_with_vehicle: true,
  },
  // Mowers (stays with vehicle)
  {
    id: 'mower_1',
    pickup_location_id: 'depot',
    compartment_types: ['bed', 'trailer'],
    capacity_consumption: { weight: 80, volume: 5 },
    attributes: { type: 'mower' },
    stays_with_vehicle: true,
  },
  {
    id: 'mower_2',
    pickup_location_id: 'depot',
    compartment_types: ['bed', 'trailer'],
    capacity_consumption: { weight: 80, volume: 5 },
    attributes: { type: 'mower' },
    stays_with_vehicle: true,
  },
  {
    id: 'mower_3',
    pickup_location_id: 'depot',
    compartment_types: ['bed', 'trailer'],
    capacity_consumption: { weight: 80, volume: 5 },
    attributes: { type: 'mower' },
    stays_with_vehicle: true,
  },
  // Mulch (consumed — dropped off at sites)
  {
    id: 'mulch_oak_hills',
    pickup_location_id: 'depot',
    dropoff_location_id: 'oak_hills_community',
    compartment_types: ['bed', 'trailer'],
    capacity_consumption: { weight: 40, volume: 2 },
    quantity: 5,
    stays_with_vehicle: false,
  },
  {
    id: 'mulch_crestview',
    pickup_location_id: 'depot',
    dropoff_location_id: 'crestview_estates',
    compartment_types: ['bed', 'trailer'],
    capacity_consumption: { weight: 40, volume: 2 },
    quantity: 3,
    stays_with_vehicle: false,
  },
]

// Location IDs for matrix construction
const locIds = demoLocations.map((l) => l.id)

// Hand-crafted distance matrix (km) — roughly realistic for Cincinnati
const distValues: Record<string, Record<string, number>> = {
  depot:               { depot: 0, johnson_residence: 10, oak_hills_community: 16, riverside_park: 15, summit_ave: 15, crestview_estates: 25 },
  johnson_residence:   { depot: 10, johnson_residence: 0, oak_hills_community: 10, riverside_park: 7,  summit_ave: 5,  crestview_estates: 20 },
  oak_hills_community: { depot: 16, johnson_residence: 10, oak_hills_community: 0, riverside_park: 20, summit_ave: 10, crestview_estates: 12 },
  riverside_park:      { depot: 15, johnson_residence: 7,  oak_hills_community: 20, riverside_park: 0,  summit_ave: 12, crestview_estates: 25 },
  summit_ave:          { depot: 15, johnson_residence: 5,  oak_hills_community: 10, riverside_park: 12, summit_ave: 0,  crestview_estates: 15 },
  crestview_estates:   { depot: 25, johnson_residence: 20, oak_hills_community: 12, riverside_park: 25, summit_ave: 15, crestview_estates: 0 },
}

// Time matrix (minutes) — roughly distance * 2 for city driving
const timeValues: Record<string, Record<string, number>> = {}
for (const from of locIds) {
  timeValues[from] = {}
  for (const to of locIds) {
    timeValues[from][to] = distValues[from][to] * 2
  }
}

export const demoMatrices = {
  distance: distValues,
  time: timeValues,
}

// Time windows (minutes from midnight): tight windows force multiple trucks
const demoTimeWindows = {
  windows: [
    { location_id: 'depot', earliest: 420, latest: 1020 },                // 7am - 5pm (operating hours)
    { location_id: 'johnson_residence', earliest: 480, latest: 600 },     // 8am - 10am (east side, morning only)
    { location_id: 'oak_hills_community', earliest: 480, latest: 600 },   // 8am - 10am (west side, same window — forces 2nd truck)
    { location_id: 'riverside_park', earliest: 600, latest: 720 },        // 10am - 12pm
    { location_id: 'summit_ave', earliest: 540, latest: 660 },            // 9am - 11am
    { location_id: 'crestview_estates', earliest: 600, latest: 840 },     // 10am - 2pm (southwest, needs travel time)
  ],
}

export const demoSolveRequestBody: SolveRequestBody = {
  request: {
    locations: demoLocations,
    vehicles: demoVehicles,
    resources: demoResources,
    matrices: demoMatrices,
    module_data: {
      time_windows: demoTimeWindows,
    },
  },
  profile: {
    tenant_id: 'demo',
    name: 'Green Acres Landscaping',
    dimensions: {
      origin_model: 'single_depot',
      fleet_composition: 'heterogeneous',
    },
    objective: { distance: 1.0 },
    modules: [
      { key: 'time_windows', enabled: true },
    ],
  },
}

// Display helpers
export const locationLabels: Record<string, string> = {
  depot: 'Green Acres HQ',
  johnson_residence: 'Johnson Residence',
  oak_hills_community: 'Oak Hills Community Center',
  riverside_park: 'Riverside Park',
  summit_ave: 'Summit Ave Property',
  crestview_estates: 'Crestview Estates',
}

export const locationDescriptions: Record<string, string> = {
  depot: 'Warehouse & dispatch center',
  johnson_residence: 'Weekly mow & edge, front and back yard',
  oak_hills_community: 'Full grounds maintenance, mulch beds and common areas',
  riverside_park: 'Bi-weekly mow, trim along walking paths',
  summit_ave: 'Quote for new landscaping design',
  crestview_estates: 'Spring cleanup, mowing, and mulch delivery',
}

export const resourceLabels: Record<string, string> = {
  mike: 'Mike',
  dave: 'Dave',
  sarah: 'Sarah',
  tom: 'Tom',
  lisa: 'Lisa',
  mower_1: 'Mower #1',
  mower_2: 'Mower #2',
  mower_3: 'Mower #3',
  mulch_oak_hills: 'Mulch (Oak Hills)',
  mulch_crestview: 'Mulch (Crestview)',
}

export const vehicleLabels: Record<string, string> = {
  truck_alpha: 'Truck Alpha',
  truck_bravo: 'Truck Bravo',
  truck_charlie: 'Truck Charlie',
}

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
