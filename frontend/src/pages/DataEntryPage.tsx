import { useState } from 'react'

type Tab = 'vehicles' | 'locations' | 'resources' | 'jobs'

const TABS: { id: Tab; label: string }[] = [
  { id: 'vehicles', label: 'Vehicles' },
  { id: 'locations', label: 'Locations' },
  { id: 'resources', label: 'Resources' },
  { id: 'jobs', label: 'Jobs' },
]

// Static demo rows — illustrate what real data looks like
const DEMO_VEHICLES = [
  { name: 'Truck Alpha', start: 'Green Acres HQ', compartments: 'Cab (3 seats), Bed (600 lb)', status: 'Active' },
  { name: 'Truck Bravo', start: 'Green Acres HQ', compartments: 'Cab (2 seats), Bed (400 lb)', status: 'Active' },
  { name: 'Truck Charlie', start: 'Green Acres HQ', compartments: 'Cab (3 seats), Bed, Trailer', status: 'Active' },
]

const DEMO_LOCATIONS = [
  { name: 'Green Acres HQ', lat: '39.2361', lng: '-84.3816', serviceTime: '0 min', type: 'Depot' },
  { name: 'Johnson Residence', lat: '39.1390', lng: '-84.4440', serviceTime: '45 min', type: 'Job Site' },
  { name: 'Oak Hills Community Center', lat: '39.1580', lng: '-84.6050', serviceTime: '90 min', type: 'Job Site' },
  { name: 'Riverside Park', lat: '39.0850', lng: '-84.3700', serviceTime: '60 min', type: 'Job Site' },
]

const DEMO_RESOURCES = [
  { name: 'Mike', type: 'Worker', attributes: 'mower_operator', staysWithVehicle: 'Yes' },
  { name: 'Dave', type: 'Worker', attributes: 'mower_operator', staysWithVehicle: 'Yes' },
  { name: 'Mower #1', type: 'Equipment', attributes: 'mower', staysWithVehicle: 'Yes' },
  { name: 'Mulch (Oak Hills)', type: 'Consumable', attributes: '—', staysWithVehicle: 'No (delivered)' },
]

const DEMO_JOBS = [
  { name: 'Mow Johnson Residence', location: 'Johnson Residence', date: 'Today', window: '8:00 AM – 10:00 AM', status: 'Scheduled' },
  { name: 'Oak Hills Grounds Maintenance', location: 'Oak Hills Community Center', date: 'Today', window: '8:00 AM – 10:00 AM', status: 'Scheduled' },
  { name: 'Mow Riverside Park', location: 'Riverside Park', date: 'Today', window: '10:00 AM – 12:00 PM', status: 'Scheduled' },
  { name: 'Crestview Spring Cleanup', location: 'Crestview Estates', date: 'Today', window: '10:00 AM – 2:00 PM', status: 'Scheduled' },
]

function ComingSoonOverlay() {
  return (
    <div className="absolute inset-0 flex flex-col items-center justify-center bg-white/60 backdrop-blur-[2px] rounded-b-xl">
      <span className="inline-flex items-center gap-2 rounded-full border border-brand-accent/30 bg-brand-accent/10 px-4 py-2 text-sm font-semibold text-brand-accent">
        <svg className="w-4 h-4" viewBox="0 0 20 20" fill="currentColor">
          <path fillRule="evenodd" d="M10 1a4.5 4.5 0 0 0-4.5 4.5V9H5a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-6a2 2 0 0 0-2-2h-.5V5.5A4.5 4.5 0 0 0 10 1Zm3 8V5.5a3 3 0 1 0-6 0V9h6Z" clipRule="evenodd" />
        </svg>
        Coming Soon
      </span>
      <p className="mt-2 text-xs text-gray-500">Request access to enable data management</p>
    </div>
  )
}

function VehiclesTab() {
  return (
    <div className="relative rounded-b-xl border border-t-0 border-gray-200 overflow-hidden">
      <table className="w-full opacity-40 select-none pointer-events-none">
        <thead className="bg-gray-50 border-b border-gray-200">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Name</th>
            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Start Location</th>
            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider hidden sm:table-cell">Compartments</th>
            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Status</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 bg-white">
          {DEMO_VEHICLES.map((v) => (
            <tr key={v.name}>
              <td className="px-4 py-3 text-sm font-medium text-gray-900">{v.name}</td>
              <td className="px-4 py-3 text-sm text-gray-500">{v.start}</td>
              <td className="px-4 py-3 text-sm text-gray-500 hidden sm:table-cell">{v.compartments}</td>
              <td className="px-4 py-3">
                <span className="inline-flex rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">{v.status}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <ComingSoonOverlay />
    </div>
  )
}

function LocationsTab() {
  return (
    <div className="relative rounded-b-xl border border-t-0 border-gray-200 overflow-hidden">
      <table className="w-full opacity-40 select-none pointer-events-none">
        <thead className="bg-gray-50 border-b border-gray-200">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Name</th>
            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider hidden md:table-cell">Lat / Lng</th>
            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider hidden sm:table-cell">Service Time</th>
            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Type</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 bg-white">
          {DEMO_LOCATIONS.map((l) => (
            <tr key={l.name}>
              <td className="px-4 py-3 text-sm font-medium text-gray-900">{l.name}</td>
              <td className="px-4 py-3 text-sm text-gray-500 font-mono hidden md:table-cell">{l.lat}, {l.lng}</td>
              <td className="px-4 py-3 text-sm text-gray-500 hidden sm:table-cell">{l.serviceTime}</td>
              <td className="px-4 py-3">
                <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${l.type === 'Depot' ? 'bg-brand-primary/10 text-brand-primary' : 'bg-sky-100 text-sky-700'}`}>
                  {l.type}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <ComingSoonOverlay />
    </div>
  )
}

function ResourcesTab() {
  return (
    <div className="relative rounded-b-xl border border-t-0 border-gray-200 overflow-hidden">
      <table className="w-full opacity-40 select-none pointer-events-none">
        <thead className="bg-gray-50 border-b border-gray-200">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Name</th>
            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Type</th>
            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider hidden sm:table-cell">Attributes</th>
            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider hidden md:table-cell">Stays With Vehicle</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 bg-white">
          {DEMO_RESOURCES.map((r) => (
            <tr key={r.name}>
              <td className="px-4 py-3 text-sm font-medium text-gray-900">{r.name}</td>
              <td className="px-4 py-3 text-sm text-gray-500">{r.type}</td>
              <td className="px-4 py-3 text-sm text-gray-500 hidden sm:table-cell">{r.attributes}</td>
              <td className="px-4 py-3 text-sm text-gray-500 hidden md:table-cell">{r.staysWithVehicle}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <ComingSoonOverlay />
    </div>
  )
}

function JobsTab() {
  return (
    <div className="relative rounded-b-xl border border-t-0 border-gray-200 overflow-hidden">
      <table className="w-full opacity-40 select-none pointer-events-none">
        <thead className="bg-gray-50 border-b border-gray-200">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Job Name</th>
            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider hidden sm:table-cell">Location</th>
            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider hidden md:table-cell">Time Window</th>
            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Status</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 bg-white">
          {DEMO_JOBS.map((j) => (
            <tr key={j.name}>
              <td className="px-4 py-3 text-sm font-medium text-gray-900">{j.name}</td>
              <td className="px-4 py-3 text-sm text-gray-500 hidden sm:table-cell">{j.location}</td>
              <td className="px-4 py-3 text-sm text-gray-500 hidden md:table-cell">{j.window}</td>
              <td className="px-4 py-3">
                <span className="inline-flex rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700">{j.status}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <ComingSoonOverlay />
    </div>
  )
}

export function DataEntryPage() {
  const [activeTab, setActiveTab] = useState<Tab>('vehicles')

  return (
    <div>
      {/* Page header */}
      <div className="mb-6">
        <h1 className="font-heading text-2xl font-bold text-brand-primary">Data Entry</h1>
        <p className="mt-1 text-sm text-gray-500">Manage your fleet, locations, resources, and scheduled jobs.</p>
      </div>

      {/* Coming soon hero banner */}
      <div className="mb-8 rounded-2xl bg-gradient-to-br from-brand-primary to-brand-secondary p-6 text-white">
        <div className="flex flex-col sm:flex-row sm:items-center gap-4">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <svg className="w-5 h-5 opacity-80" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 1a4.5 4.5 0 0 0-4.5 4.5V9H5a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-6a2 2 0 0 0-2-2h-.5V5.5A4.5 4.5 0 0 0 10 1Zm3 8V5.5a3 3 0 1 0-6 0V9h6Z" clipRule="evenodd" />
              </svg>
              <span className="text-xs font-semibold uppercase tracking-wider opacity-80">Coming Soon</span>
            </div>
            <h2 className="font-heading text-lg font-bold">Data management is on the roadmap</h2>
            <p className="mt-1 text-sm opacity-80 max-w-lg">
              Currently, demo data is pre-loaded for each scenario. Full data entry — and API integrations with your existing fleet management or job scheduling systems — is coming soon.
            </p>
          </div>
          <div className="shrink-0">
            <a
              href="mailto:info@ascentdi.com?subject=Bento%20Data%20Entry%20Access"
              className="inline-flex items-center gap-2 rounded-full bg-white px-5 py-2.5 text-sm font-bold text-brand-primary shadow hover:bg-white/90 transition-colors"
            >
              Request Early Access
              <svg className="w-4 h-4" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M3 10a.75.75 0 0 1 .75-.75h10.638L10.23 5.29a.75.75 0 1 1 1.04-1.08l5.5 5.25a.75.75 0 0 1 0 1.08l-5.5 5.25a.75.75 0 1 1-1.04-1.08l4.158-3.96H3.75A.75.75 0 0 1 3 10Z" clipRule="evenodd" />
              </svg>
            </a>
          </div>
        </div>

        {/* Feature preview pills */}
        <div className="mt-5 flex flex-wrap gap-2">
          {['Manual data entry', 'CSV / Excel import', 'REST API integration', 'Webhook sync', 'Real-time updates'].map((f) => (
            <span key={f} className="inline-flex items-center gap-1.5 rounded-full bg-white/15 px-3 py-1 text-xs font-medium">
              <svg className="w-3 h-3 opacity-70" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 1 0 0-16 8 8 0 0 0 0 16Zm3.857-9.809a.75.75 0 0 0-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 1 0-1.06 1.061l2.5 2.5a.75.75 0 0 0 1.137-.089l4-5.5Z" clipRule="evenodd" />
              </svg>
              {f}
            </span>
          ))}
        </div>
      </div>

      {/* Tabs */}
      <div>
        <div className="flex border-b border-gray-200 mb-0">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors ${
                activeTab === tab.id
                  ? 'border-brand-accent text-brand-primary'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab add button (grayed out) */}
        <div className="flex items-center justify-end py-2 px-1 border border-t-0 border-b-0 border-gray-200 bg-gray-50/50">
          <button
            disabled
            className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-xs font-medium text-gray-400 cursor-not-allowed opacity-50"
          >
            <svg className="w-3.5 h-3.5" viewBox="0 0 20 20" fill="currentColor">
              <path d="M10.75 4.75a.75.75 0 0 0-1.5 0v4.5h-4.5a.75.75 0 0 0 0 1.5h4.5v4.5a.75.75 0 0 0 1.5 0v-4.5h4.5a.75.75 0 0 0 0-1.5h-4.5v-4.5Z" />
            </svg>
            Add {TABS.find((t) => t.id === activeTab)?.label.slice(0, -1)}
          </button>
        </div>

        {activeTab === 'vehicles' && <VehiclesTab />}
        {activeTab === 'locations' && <LocationsTab />}
        {activeTab === 'resources' && <ResourcesTab />}
        {activeTab === 'jobs' && <JobsTab />}
      </div>
    </div>
  )
}
