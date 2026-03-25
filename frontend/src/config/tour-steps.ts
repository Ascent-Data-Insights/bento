export type TourPlacement = 'top' | 'bottom' | 'left' | 'right'
export type TourPrepare = 'sidebar' | 'sheet' | 'close-sidebar' | null

export interface TourStep {
  id: string
  title: string
  body: string
  placement: TourPlacement
  /** Route to navigate to before showing this step. Only navigates if not already there. */
  route?: string
  /** UI state to set up before spotlighting the target. */
  prepare?: TourPrepare
}

export const TOUR_STEPS: TourStep[] = [
  {
    id: 'tenant-selector',
    title: 'Switch tenants',
    body: 'Each tenant represents a different client or scenario. Use this dropdown to switch between demo scenarios — try "Green Acres Landscaping" for a grasscutting workflow, or "Fresh Fleet Delivery" for a food delivery use case.',
    placement: 'right',
    route: '/',
    prepare: 'sidebar',
  },
  {
    id: 'dashboard-map',
    title: 'Your map view',
    body: 'This map shows all job sites and the depot for today. Markers are color-coded: the depot anchor shows where vehicles start and end their day, while pins show job sites. After optimizing, colored route lines appear connecting each vehicle\'s stops.',
    placement: 'right',
    route: '/',
    prepare: 'close-sidebar',
  },
  {
    id: 'optimize-button',
    title: 'One-click optimization',
    body: 'Hit "Optimize Routes" to run the solver. It assigns workers, equipment, and vehicles to jobs while respecting capacity constraints, time windows, and skill requirements — all in seconds.',
    placement: 'top',
    route: '/',
    prepare: 'close-sidebar',
  },
  {
    id: 'detail-panel',
    title: 'Dispatch & route details',
    body: 'Before solving, this panel shows today\'s jobs, fleet summary, and resources. After solving, it shows each vehicle\'s optimized route with arrival times. Click a route card to highlight it on the map.',
    placement: 'left',
    route: '/',
    prepare: 'sheet',
  },
  {
    id: 'crew-schedule-nav',
    title: 'Crew schedule view',
    body: 'The Crew Schedule page shows each worker\'s day as a card — which vehicle they\'re on, what stops they\'ll make, and when they arrive. Great for dispatcher handoff or a morning briefing.',
    placement: 'right',
    route: '/crew',
    prepare: 'sidebar',
  },
  {
    id: 'onboard-nav',
    title: 'Configure a new tenant',
    body: 'The New Tenant flow lets you configure a routing profile — choose your depot model, fleet composition, constraint modules (like time windows or EV charging), and set objective weights to balance distance vs. time.',
    placement: 'right',
    route: '/onboard',
    prepare: 'sidebar',
  },
  {
    id: 'data-entry-nav',
    title: 'Your data, your way',
    body: 'Data entry is coming soon. You\'ll be able to manage your own vehicles, locations, resources, and jobs directly — or connect via API to your existing systems.',
    placement: 'right',
    route: '/data',
    prepare: 'sidebar',
  },
]
