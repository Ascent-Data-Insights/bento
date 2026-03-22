import { useState, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'motion/react'
import clsx from 'clsx'
import { fetchModules, onboardTenant } from '../api/client'
import { useTenant } from '../contexts/TenantContext'
import { Input } from '../components/input'
import { Button } from '../components/button'
import { Badge } from '../components/badge'
import { Switch } from '../components/switch'
import type { ModuleMetadata } from '../types/api'

// ─── Dimension definitions ───────────────────────────────────────────────────

const ORIGIN_MODELS = [
  {
    value: 'single_depot',
    label: 'Single Depot',
    description: 'All vehicles start and return to one location',
    icon: (
      <svg viewBox="0 0 32 32" fill="none" className="size-8">
        <circle cx="16" cy="16" r="5" fill="currentColor" opacity="0.2" />
        <circle cx="16" cy="16" r="3" fill="currentColor" />
        <path d="M16 8v-3M16 27v-3M8 16H5M27 16h-3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
    ),
  },
  {
    value: 'multi_depot',
    label: 'Multi Depot',
    description: 'Vehicles dispatch from multiple depots',
    icon: (
      <svg viewBox="0 0 32 32" fill="none" className="size-8">
        <circle cx="10" cy="10" r="3" fill="currentColor" />
        <circle cx="22" cy="10" r="3" fill="currentColor" />
        <circle cx="16" cy="22" r="3" fill="currentColor" />
        <circle cx="10" cy="10" r="5" fill="currentColor" opacity="0.15" />
        <circle cx="22" cy="10" r="5" fill="currentColor" opacity="0.15" />
        <circle cx="16" cy="22" r="5" fill="currentColor" opacity="0.15" />
      </svg>
    ),
  },
  {
    value: 'depot_intermediate',
    label: 'Depot + Intermediate',
    description: 'Vehicles reload at intermediate stops mid-route',
    icon: (
      <svg viewBox="0 0 32 32" fill="none" className="size-8">
        <circle cx="8" cy="16" r="3" fill="currentColor" />
        <circle cx="8" cy="16" r="5" fill="currentColor" opacity="0.15" />
        <rect x="19" y="13" width="6" height="6" rx="1.5" fill="currentColor" opacity="0.5" />
        <path d="M13 16h6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeDasharray="2 2" />
      </svg>
    ),
  },
]

const FLEET_COMPOSITIONS = [
  {
    value: 'homogeneous',
    label: 'Homogeneous',
    description: 'All vehicles are identical in capacity and type',
    icon: (
      <svg viewBox="0 0 32 32" fill="none" className="size-8">
        <rect x="4" y="12" width="10" height="8" rx="2" fill="currentColor" opacity="0.3" />
        <rect x="18" y="12" width="10" height="8" rx="2" fill="currentColor" opacity="0.3" />
        <path d="M6 22v2M12 22v2M20 22v2M26 22v2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
    ),
  },
  {
    value: 'heterogeneous',
    label: 'Heterogeneous',
    description: 'Mixed fleet with different vehicle types and capacities',
    icon: (
      <svg viewBox="0 0 32 32" fill="none" className="size-8">
        <rect x="3" y="14" width="8" height="6" rx="1.5" fill="currentColor" opacity="0.3" />
        <rect x="13" y="10" width="8" height="10" rx="1.5" fill="currentColor" opacity="0.5" />
        <rect x="23" y="12" width="6" height="8" rx="1.5" fill="currentColor" opacity="0.3" />
        <path d="M5 22v2M9 22v2M15 22v2M19 22v2M24 22v2M28 22v2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
    ),
  },
]

const MODULE_ICONS: Record<string, React.ReactNode> = {
  time_windows: (
    <svg viewBox="0 0 24 24" fill="none" className="size-5">
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.5" />
      <path d="M12 7v5l3 3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  ),
  co_delivery: (
    <svg viewBox="0 0 24 24" fill="none" className="size-5">
      <path d="M8 8h8v8H8z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
      <path d="M4 4l4 4M20 4l-4 4M4 20l4-4M20 20l-4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  ),
  ev_fuel: (
    <svg viewBox="0 0 24 24" fill="none" className="size-5">
      <path d="M13 2L4 14h6l-1 8 9-12h-6l1-8z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
    </svg>
  ),
  shift_limits: (
    <svg viewBox="0 0 24 24" fill="none" className="size-5">
      <rect x="3" y="6" width="18" height="12" rx="2" stroke="currentColor" strokeWidth="1.5" />
      <path d="M7 10v4M12 10v4M17 10v4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  ),
  priority_sla: (
    <svg viewBox="0 0 24 24" fill="none" className="size-5">
      <path d="M12 2l3 6h6l-5 4 2 6-6-4-6 4 2-6-5-4h6l3-6z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
    </svg>
  ),
}

const DEFAULT_OBJECTIVES = [
  { key: 'distance', label: 'Distance', description: 'Minimize total distance traveled' },
  { key: 'time', label: 'Time', description: 'Minimize total route time' },
  { key: 'vehicles', label: 'Vehicles', description: 'Minimize number of vehicles used' },
]

// ─── Section wrapper ─────────────────────────────────────────────────────────

function Section({
  number,
  title,
  subtitle,
  delay = 0,
  children,
}: {
  number: string
  title: string
  subtitle: string
  delay?: number
  children: React.ReactNode
}) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay, ease: [0.25, 0.46, 0.45, 0.94] }}
    >
      <div className="flex items-start gap-4 mb-5">
        <span className="flex-none flex items-center justify-center size-7 rounded-md bg-brand-primary/10 text-brand-primary font-heading text-xs font-bold">
          {number}
        </span>
        <div>
          <h3 className="font-heading text-sm font-semibold text-zinc-950">{title}</h3>
          <p className="text-xs text-zinc-500 mt-0.5">{subtitle}</p>
        </div>
      </div>
      {children}
    </motion.section>
  )
}

// ─── Dimension card ──────────────────────────────────────────────────────────

function DimensionCard({
  label,
  description,
  icon,
  selected,
  onClick,
}: {
  label: string
  description: string
  icon: React.ReactNode
  selected: boolean
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={clsx(
        'group relative flex items-start gap-3 rounded-lg border p-3.5 text-left transition-all duration-150',
        'focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-secondary focus-visible:ring-offset-2',
        selected
          ? 'border-brand-primary bg-brand-primary ring-1 ring-brand-primary/30'
          : 'border-zinc-200 hover:border-zinc-300 hover:bg-zinc-50'
      )}
    >
      <div
        className={clsx(
          'flex-none text-brand-primary transition-colors',
          selected ? 'text-white' : 'text-zinc-400 group-hover:text-zinc-500'
        )}
      >
        {icon}
      </div>
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <span className={clsx('text-sm font-medium', selected ? 'text-brand-accent' : 'text-zinc-950')}>{label}</span>
          {selected && (
            <motion.span
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              className="flex-none size-1.5 rounded-full bg-brand-accent"
            />
          )}
        </div>
        <p className={clsx('text-xs mt-0.5 leading-relaxed', selected ? 'text-white/70' : 'text-zinc-500')}>{description}</p>
      </div>
    </button>
  )
}

// ─── Module card ─────────────────────────────────────────────────────────────

function ModuleCard({
  module,
  enabled,
  onToggle,
  disabled,
}: {
  module: ModuleMetadata
  enabled: boolean
  onToggle: () => void
  disabled: boolean
}) {
  const icon = MODULE_ICONS[module.key]
  const isComingSoon = !module.implemented

  return (
    <div
      className={clsx(
        'relative rounded-lg border p-4 transition-all duration-150',
        disabled || isComingSoon
          ? 'border-zinc-100 bg-zinc-50/50 opacity-60'
          : enabled
            ? 'border-brand-primary/30 bg-brand-primary'
            : 'border-zinc-200 hover:border-zinc-300'
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3 min-w-0">
          <div
            className={clsx(
              'flex-none mt-0.5 transition-colors',
              enabled && !disabled && !isComingSoon ? 'text-brand-accent' : 'text-zinc-400'
            )}
          >
            {icon || (
              <svg viewBox="0 0 24 24" fill="none" className="size-5">
                <rect x="3" y="3" width="18" height="18" rx="3" stroke="currentColor" strokeWidth="1.5" />
              </svg>
            )}
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className={clsx('text-sm font-medium', enabled && !isComingSoon ? 'text-brand-accent' : 'text-zinc-950')}>{module.name}</span>
              {isComingSoon && <Badge color="zinc">Soon</Badge>}
            </div>
            <p className={clsx('text-xs mt-1 leading-relaxed', enabled && !isComingSoon ? 'text-white/70' : 'text-zinc-500')}>{module.description}</p>
            {module.dependencies.length > 0 && (
              <p className={clsx('text-[10px] mt-1.5', enabled && !isComingSoon ? 'text-white/50' : 'text-zinc-400')}>
                Requires: {module.dependencies.join(', ')}
              </p>
            )}
          </div>
        </div>
        <div className="flex-none">
          <Switch
            color="orange"
            checked={enabled}
            onChange={onToggle}
            disabled={disabled || isComingSoon}
          />
        </div>
      </div>
    </div>
  )
}

// ─── Linked objective sliders ─────────────────────────────────────────────────

function LinkedObjectiveSliders({
  objectives,
  onChange,
}: {
  objectives: Record<string, number>
  onChange: (updated: Record<string, number>) => void
}) {
  const total = Object.values(objectives).reduce((s, v) => s + v, 0)

  const handleSlide = (changedKey: string, rawPercent: number) => {
    const otherKeys = DEFAULT_OBJECTIVES.map((o) => o.key).filter((k) => k !== changedKey)
    const newPercent = Math.min(100, Math.max(0, rawPercent))
    const remaining = 100 - newPercent

    // Current total of the other sliders
    const otherTotal = otherKeys.reduce((s, k) => s + (objectives[k] ?? 0) * 100, 0)

    const updated: Record<string, number> = { ...objectives, [changedKey]: newPercent / 100 }

    if (otherTotal === 0) {
      // Distribute remaining equally among others
      for (const k of otherKeys) updated[k] = remaining / otherKeys.length / 100
    } else {
      // Scale others proportionally to fill the remainder
      for (const k of otherKeys) {
        const share = ((objectives[k] ?? 0) * 100) / otherTotal
        updated[k] = Math.max(0, (remaining * share) / 100)
      }
    }

    // Fix floating point drift — normalize to exactly 1.0
    const sum = Object.values(updated).reduce((s, v) => s + v, 0)
    if (sum > 0) {
      for (const k of Object.keys(updated)) updated[k] = updated[k] / sum
    }

    onChange(updated)
  }

  return (
    <div className="space-y-5 max-w-lg">
      {/* Stacked bar showing the mix */}
      <div className="flex h-2.5 rounded-full overflow-hidden bg-zinc-100">
        {DEFAULT_OBJECTIVES.map((obj, i) => {
          const pct = total > 0 ? ((objectives[obj.key] ?? 0) / total) * 100 : 0
          const colors = ['bg-brand-primary', 'bg-brand-secondary', 'bg-brand-accent']
          return pct > 0 ? (
            <div
              key={obj.key}
              className={clsx('transition-all duration-200', colors[i])}
              style={{ width: `${pct}%` }}
            />
          ) : null
        })}
      </div>

      {/* Individual sliders */}
      {DEFAULT_OBJECTIVES.map((obj, i) => {
        const pct = total > 0 ? ((objectives[obj.key] ?? 0) / total) * 100 : 0
        const dotColors = ['bg-brand-primary', 'bg-brand-secondary', 'bg-brand-accent']
        const thumbHexes = ['#03344E', '#4785BF', '#FB8500']
        return (
          <div key={obj.key} className="flex items-center gap-4">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className={clsx('size-2 rounded-full flex-none', dotColors[i])} />
                <span className="text-sm font-medium text-zinc-950">{obj.label}</span>
              </div>
              <p className="text-xs text-zinc-500 ml-4">{obj.description}</p>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="range"
                min={0}
                max={100}
                step={1}
                value={Math.round(pct)}
                onChange={(e) => handleSlide(obj.key, parseInt(e.target.value))}
                className="w-28 h-1.5 appearance-none rounded-full bg-zinc-200 cursor-pointer
                  [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:size-3.5 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:shadow-sm [&::-webkit-slider-thumb]:border-2 [&::-webkit-slider-thumb]:border-white
                  [&::-moz-range-thumb]:appearance-none [&::-moz-range-thumb]:size-3.5 [&::-moz-range-thumb]:rounded-full [&::-moz-range-thumb]:shadow-sm [&::-moz-range-thumb]:border-2 [&::-moz-range-thumb]:border-white"
                style={{
                  // @ts-expect-error -- CSS custom property for thumb color
                  '--thumb-color': thumbHexes[i],
                  WebkitAppearance: 'none',
                }}
                ref={(el) => {
                  if (el) {
                    const color = thumbHexes[i]
                    const style = document.createElement('style')
                    style.textContent = `
                      input[data-thumb="${obj.key}"]::-webkit-slider-thumb { background-color: ${color} !important; }
                      input[data-thumb="${obj.key}"]::-moz-range-thumb { background-color: ${color} !important; }
                    `
                    el.setAttribute('data-thumb', obj.key)
                    // Remove old injected style if any
                    const prev = document.getElementById(`thumb-style-${obj.key}`)
                    if (prev) prev.remove()
                    style.id = `thumb-style-${obj.key}`
                    document.head.appendChild(style)
                  }
                }}
              />
              <span className="w-10 text-right text-xs font-mono text-zinc-600 tabular-nums">
                {Math.round(pct)}%
              </span>
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ─── Preview panel ───────────────────────────────────────────────────────────

function PreviewPanel({
  tenantName,
  industry,
  originModel,
  fleetComposition,
  modules,
  objectives,
}: {
  tenantName: string
  industry: string
  originModel: string
  fleetComposition: string
  modules: { key: string; enabled: boolean }[]
  objectives: Record<string, number>
}) {
  const enabledModules = modules.filter((m) => m.enabled)
  const activeObjectives = Object.entries(objectives).filter(([, v]) => v > 0)

  return (
    <div className="rounded-lg border border-zinc-200 bg-white overflow-hidden">
      <div className="px-4 py-3 border-b border-zinc-100 bg-zinc-50/50">
        <div className="flex items-center gap-2">
          <div className="size-1.5 rounded-full bg-brand-accent" />
          <span className="font-heading text-xs font-semibold text-zinc-700 uppercase tracking-wider">
            Configuration Preview
          </span>
        </div>
      </div>
      <div className="p-4 space-y-3">
        <PreviewRow label="Tenant" value={tenantName || '—'} muted={!tenantName} />
        <PreviewRow label="Industry" value={industry || '—'} muted={!industry} />
        <div className="border-t border-zinc-100 my-2" />
        <PreviewRow
          label="Origin"
          value={ORIGIN_MODELS.find((m) => m.value === originModel)?.label || '—'}
        />
        <PreviewRow
          label="Fleet"
          value={FLEET_COMPOSITIONS.find((f) => f.value === fleetComposition)?.label || '—'}
        />
        <div className="border-t border-zinc-100 my-2" />
        <div>
          <span className="text-[10px] font-medium text-zinc-400 uppercase tracking-wider">
            Modules
          </span>
          <div className="mt-1.5 flex flex-wrap gap-1">
            {enabledModules.length > 0 ? (
              enabledModules.map((m) => (
                <Badge key={m.key} color="blue">
                  {m.key.replace(/_/g, ' ')}
                </Badge>
              ))
            ) : (
              <span className="text-xs text-zinc-400 italic">None selected</span>
            )}
          </div>
        </div>
        <div>
          <span className="text-[10px] font-medium text-zinc-400 uppercase tracking-wider">
            Objective
          </span>
          <div className="mt-1.5 space-y-1">
            {activeObjectives.length > 0 ? (
              activeObjectives.map(([key, weight]) => {
                const pct = Math.round(weight * 100)
                return (
                  <div key={key} className="flex items-center gap-2">
                    <div
                      className="h-1.5 rounded-full bg-brand-secondary/70"
                      style={{ width: `${pct}%`, maxWidth: '80px' }}
                    />
                    <span className="text-xs text-zinc-600">
                      {key.charAt(0).toUpperCase() + key.slice(1)} <span className="text-zinc-400">{pct}%</span>
                    </span>
                  </div>
                )
              })
            ) : (
              <span className="text-xs text-zinc-400 italic">No weights set</span>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function PreviewRow({
  label,
  value,
  muted = false,
}: {
  label: string
  value: string
  muted?: boolean
}) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <span className="text-[10px] font-medium text-zinc-400 uppercase tracking-wider flex-none">
        {label}
      </span>
      <span
        className={clsx(
          'text-xs text-right truncate',
          muted ? 'text-zinc-400 italic' : 'text-zinc-700 font-medium'
        )}
      >
        {value}
      </span>
    </div>
  )
}

// ─── Main page ───────────────────────────────────────────────────────────────

export function ProfileBuilderPage() {
  const navigate = useNavigate()
  const { addTenant } = useTenant()

  // Form state
  const [tenantName, setTenantName] = useState('')
  const [industry, setIndustry] = useState('')
  const profileName = 'Default'
  const [originModel, setOriginModel] = useState('single_depot')
  const [fleetComposition, setFleetComposition] = useState('homogeneous')
  const [moduleStates, setModuleStates] = useState<Record<string, boolean>>({})
  const [objectives, setObjectives] = useState<Record<string, number>>({
    distance: 0.6,
    time: 0.3,
    vehicles: 0.1,
  })

  // Module data from API
  const [availableModules, setAvailableModules] = useState<ModuleMetadata[]>([])
  const [modulesLoading, setModulesLoading] = useState(true)

  // Submission state
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchModules()
      .then((modules) => {
        setAvailableModules(modules)
        const initial: Record<string, boolean> = {}
        for (const m of modules) initial[m.key] = false
        setModuleStates(initial)
      })
      .catch(() => {
        // Fall back to empty — modules section will show nothing
      })
      .finally(() => setModulesLoading(false))
  }, [])

  const toggleModule = (key: string) => {
    setModuleStates((prev) => ({ ...prev, [key]: !prev[key] }))
  }

  const activeObjectives = useMemo(
    () => Object.fromEntries(Object.entries(objectives).filter(([, v]) => v > 0)),
    [objectives]
  )

  const canSubmit =
    tenantName.trim() !== '' &&
    industry.trim() !== '' &&
    Object.keys(activeObjectives).length > 0

  const handleSubmit = async () => {
    if (!canSubmit) return
    setSubmitting(true)
    setError(null)

    try {
      const enabledModules = Object.entries(moduleStates)
        .filter(([, enabled]) => enabled)
        .map(([key]) => ({ key, enabled: true, params: {} }))

      const result = await onboardTenant({
        tenant_name: tenantName.trim(),
        industry: industry.trim(),
        profile_name: profileName.trim(),
        dimensions: {
          origin_model: originModel,
          fleet_composition: fleetComposition,
        },
        objective: activeObjectives,
        modules: enabledModules,
      })

      addTenant(result.tenant)
      navigate('/')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create tenant')
    } finally {
      setSubmitting(false)
    }
  }

  const modulesList = useMemo(
    () =>
      Object.entries(moduleStates).map(([key, enabled]) => ({ key, enabled })),
    [moduleStates]
  )

  return (
    <div className="min-h-full bg-gradient-to-b from-zinc-50/80 to-white">
      <div className="max-w-6xl mx-auto px-6 py-8 lg:px-8">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="mb-10"
        >
          <h1 className="font-heading text-2xl font-bold text-brand-primary">
            New Tenant
          </h1>
          <p className="text-sm text-zinc-500 mt-1">
            Configure dimensions, select modules, and set optimization objectives.
          </p>
        </motion.div>

        <div className="grid grid-cols-1 lg:grid-cols-[1fr_280px] gap-8 items-start">
          {/* Left column — Form */}
          <div className="space-y-10">
            {/* Section 1: Tenant Info */}
            <Section number="1" title="Tenant Info" subtitle="Company details for this configuration" delay={0.05}>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-zinc-700 mb-1.5">
                    Tenant Name
                  </label>
                  <Input
                    value={tenantName}
                    onChange={(e) => setTenantName(e.target.value)}
                    placeholder="Acme Landscaping"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-zinc-700 mb-1.5">
                    Industry
                  </label>
                  <Input
                    value={industry}
                    onChange={(e) => setIndustry(e.target.value)}
                    placeholder="Landscaping"
                  />
                </div>
              </div>
            </Section>

            {/* Section 2: Dimensions */}
            <Section number="2" title="Dimensions" subtitle="Structural choices that shape the model" delay={0.1}>
              <div className="space-y-5">
                <div>
                  <span className="text-xs font-medium text-zinc-500 uppercase tracking-wider">
                    Origin Model
                  </span>
                  <div className="mt-2 grid grid-cols-1 sm:grid-cols-3 gap-3">
                    {ORIGIN_MODELS.map((model) => (
                      <DimensionCard
                        key={model.value}
                        label={model.label}
                        description={model.description}
                        icon={model.icon}
                        selected={originModel === model.value}
                        onClick={() => setOriginModel(model.value)}
                      />
                    ))}
                  </div>
                </div>
                <div>
                  <span className="text-xs font-medium text-zinc-500 uppercase tracking-wider">
                    Fleet Composition
                  </span>
                  <div className="mt-2 grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {FLEET_COMPOSITIONS.map((comp) => (
                      <DimensionCard
                        key={comp.value}
                        label={comp.label}
                        description={comp.description}
                        icon={comp.icon}
                        selected={fleetComposition === comp.value}
                        onClick={() => setFleetComposition(comp.value)}
                      />
                    ))}
                  </div>
                </div>
              </div>
            </Section>

            {/* Section 3: Modules */}
            <Section number="3" title="Modules" subtitle="Composable constraint rules — toggle what you need" delay={0.15}>
              {modulesLoading ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {[0, 1, 2, 3].map((i) => (
                    <div
                      key={i}
                      className="h-24 rounded-lg border border-zinc-100 bg-zinc-50 animate-pulse"
                    />
                  ))}
                </div>
              ) : availableModules.length === 0 ? (
                <p className="text-sm text-zinc-400 italic">No modules available</p>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {availableModules.map((mod) => (
                    <ModuleCard
                      key={mod.key}
                      module={mod}
                      enabled={moduleStates[mod.key] ?? false}
                      onToggle={() => toggleModule(mod.key)}
                      disabled={false}
                    />
                  ))}
                </div>
              )}
            </Section>

            {/* Section 4: Objective Weights */}
            <Section number="4" title="Objective" subtitle="What should the solver optimize for? Drag to rebalance." delay={0.2}>
              <LinkedObjectiveSliders
                objectives={objectives}
                onChange={setObjectives}
              />
            </Section>

            {/* Submit */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.3 }}
              className="pt-2 pb-8"
            >
              <AnimatePresence>
                {error && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
                  >
                    {error}
                  </motion.div>
                )}
              </AnimatePresence>
              <Button
                color="orange"
                onClick={handleSubmit}
                disabled={!canSubmit || submitting}
                className="w-full sm:w-auto"
              >
                {submitting ? (
                  <span className="flex items-center gap-2">
                    <svg className="size-4 animate-spin" viewBox="0 0 24 24" fill="none">
                      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" className="opacity-25" />
                      <path d="M4 12a8 8 0 018-8" stroke="currentColor" strokeWidth="3" strokeLinecap="round" className="opacity-75" />
                    </svg>
                    Creating…
                  </span>
                ) : (
                  'Create Tenant'
                )}
              </Button>
            </motion.div>
          </div>

          {/* Right column — Preview (sticky) */}
          <div className="hidden lg:block">
            <div className="sticky top-20">
              <motion.div
                initial={{ opacity: 0, x: 12 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.4, delay: 0.15 }}
              >
                <PreviewPanel
                  tenantName={tenantName}
                  industry={industry}
                  originModel={originModel}
                  fleetComposition={fleetComposition}
                  modules={modulesList}
                  objectives={objectives}
                />
              </motion.div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
