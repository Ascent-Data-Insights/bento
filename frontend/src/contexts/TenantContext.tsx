import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import type { TenantResponse } from '../types/api'
import { fetchTenants } from '../api/client'

interface TenantContextType {
  tenants: TenantResponse[]
  activeTenant: TenantResponse | null
  setActiveTenant: (tenant: TenantResponse) => void
  loading: boolean
}

const TenantContext = createContext<TenantContextType | null>(null)

export function TenantProvider({ children }: { children: ReactNode }) {
  const [tenants, setTenants] = useState<TenantResponse[]>([])
  const [activeTenant, setActiveTenant] = useState<TenantResponse | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    fetchTenants()
      .then((data) => {
        if (!cancelled) {
          setTenants(data)
          if (data.length > 0) setActiveTenant(data[0])
          setLoading(false)
        }
      })
      .catch(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [])

  return (
    <TenantContext.Provider value={{ tenants, activeTenant, setActiveTenant, loading }}>
      {children}
    </TenantContext.Provider>
  )
}

export function useTenant(): TenantContextType {
  const context = useContext(TenantContext)
  if (!context) throw new Error('useTenant must be used within a TenantProvider')
  return context
}
