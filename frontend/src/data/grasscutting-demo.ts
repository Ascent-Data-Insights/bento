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
    latitude: 39.2320,
    longitude: -84.3780,
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
  depot:               { depot: 0, johnson_residence: 9,  oak_hills_community: 12, riverside_park: 16, summit_ave: 3,  crestview_estates: 18 },
  johnson_residence:   { depot: 9, johnson_residence: 0,  oak_hills_community: 18, riverside_park: 8,  summit_ave: 7,  crestview_estates: 12 },
  oak_hills_community: { depot: 12, johnson_residence: 18, oak_hills_community: 0, riverside_park: 24, summit_ave: 10, crestview_estates: 26 },
  riverside_park:      { depot: 16, johnson_residence: 8,  oak_hills_community: 24, riverside_park: 0,  summit_ave: 14, crestview_estates: 17 },
  summit_ave:          { depot: 3,  johnson_residence: 7,  oak_hills_community: 10, riverside_park: 14, summit_ave: 0,  crestview_estates: 16 },
  crestview_estates:   { depot: 18, johnson_residence: 12, oak_hills_community: 26, riverside_park: 17, summit_ave: 16, crestview_estates: 0 },
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

// Time windows (minutes from midnight): generous 4-6 hour windows
const demoTimeWindows = {
  windows: [
    { location_id: 'johnson_residence', earliest: 480, latest: 720 },     // 8am - 12pm
    { location_id: 'oak_hills_community', earliest: 480, latest: 900 },   // 8am - 3pm
    { location_id: 'riverside_park', earliest: 540, latest: 780 },        // 9am - 1pm
    { location_id: 'summit_ave', earliest: 480, latest: 840 },            // 8am - 2pm
    { location_id: 'crestview_estates', earliest: 600, latest: 960 },     // 10am - 4pm
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

export function formatTime(minutes: number): string {
  const h = Math.floor(minutes / 60)
  const m = Math.round(minutes % 60)
  const period = h >= 12 ? 'PM' : 'AM'
  const hour = h > 12 ? h - 12 : h === 0 ? 12 : h
  return `${hour}:${m.toString().padStart(2, '0')} ${period}`
}
