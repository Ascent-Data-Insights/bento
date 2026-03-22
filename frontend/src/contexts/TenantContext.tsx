import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from 'react'
import type { TenantResponse } from '../types/api'
import { fetchTenants } from '../api/client'

interface TenantContextType {
  tenants: TenantResponse[]
  activeTenant: TenantResponse | null
  setActiveTenant: (tenant: TenantResponse) => void
  addTenant: (tenant: TenantResponse) => void
  removeTenant: (tenantId: string) => void
  loading: boolean
}

const TenantContext = createContext<TenantContextType | null>(null)

const MAX_RETRIES = 10
const RETRY_DELAY_MS = 3000

export function TenantProvider({ children }: { children: ReactNode }) {
  const [tenants, setTenants] = useState<TenantResponse[]>([])
  const [activeTenant, setActiveTenant] = useState<TenantResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const retryCount = useRef(0)

  useEffect(() => {
    let cancelled = false
    let timeoutId: ReturnType<typeof setTimeout>

    const load = async () => {
      try {
        const data = await fetchTenants()
        if (!cancelled) {
          setTenants(data)
          if (data.length > 0) setActiveTenant(data[0])
          setLoading(false)
        }
      } catch {
        if (!cancelled && retryCount.current < MAX_RETRIES) {
          retryCount.current++
          timeoutId = setTimeout(load, RETRY_DELAY_MS)
        } else if (!cancelled) {
          setLoading(false)
        }
      }
    }

    load()
    return () => {
      cancelled = true
      clearTimeout(timeoutId)
    }
  }, [])

  const addTenant = (tenant: TenantResponse) => {
    setTenants((prev) => [...prev, tenant])
    setActiveTenant(tenant)
  }

  const removeTenant = (tenantId: string) => {
    setTenants((prev) => {
      const updated = prev.filter((t) => t.id !== tenantId)
      setActiveTenant((current) => {
        if (current?.id === tenantId) {
          return updated.length > 0 ? updated[0] : null
        }
        return current
      })
      return updated
    })
  }

  return (
    <TenantContext.Provider value={{ tenants, activeTenant, setActiveTenant, addTenant, removeTenant, loading }}>
      {children}
    </TenantContext.Provider>
  )
}

export function useTenant(): TenantContextType {
  const context = useContext(TenantContext)
  if (!context) throw new Error('useTenant must be used within a TenantProvider')
  return context
}
