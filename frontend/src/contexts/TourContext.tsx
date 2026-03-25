import { createContext, useContext, useRef, useState, type ReactNode } from 'react'
import { TOUR_STEPS, type TourPrepare, type TourStep } from '../config/tour-steps'

type PrepareHandler = () => void

interface TourContextType {
  active: boolean
  stepIndex: number
  steps: TourStep[]
  currentStep: TourStep | null
  /** False while beforeStep preparation (navigation, sidebar open) is in flight */
  ready: boolean
  setReady: (ready: boolean) => void
  start: () => void
  dismiss: () => void
  next: () => void
  prev: () => void
  /** Register a handler that runs when a specific prepare action is needed */
  registerPrepareHandler: (type: TourPrepare, handler: PrepareHandler) => () => void
  /** Internal: run the handler registered for a prepare type */
  runPrepareHandler: (type: TourPrepare) => void
}

const TourContext = createContext<TourContextType | null>(null)

export function TourProvider({ children }: { children: ReactNode }) {
  const [active, setActive] = useState(false)
  const [stepIndex, setStepIndex] = useState(0)
  const [ready, setReady] = useState(false)
  const handlers = useRef<Partial<Record<NonNullable<TourPrepare>, PrepareHandler>>>({})

  const registerPrepareHandler = (type: TourPrepare, handler: PrepareHandler) => {
    if (!type) return () => {}
    handlers.current[type] = handler
    return () => { delete handlers.current[type as NonNullable<TourPrepare>] }
  }

  const runPrepareHandler = (type: TourPrepare) => {
    if (!type) return
    handlers.current[type]?.()
  }

  const start = () => {
    setStepIndex(0)
    setReady(false)
    setActive(true)
  }

  const dismiss = () => {
    setActive(false)
    setStepIndex(0)
    setReady(false)
  }

  const next = () => {
    if (stepIndex < TOUR_STEPS.length - 1) {
      setReady(false)
      setStepIndex((i) => i + 1)
    } else {
      dismiss()
    }
  }

  const prev = () => {
    if (stepIndex > 0) {
      setReady(false)
      setStepIndex((i) => i - 1)
    }
  }

  const currentStep = active ? TOUR_STEPS[stepIndex] : null

  return (
    <TourContext.Provider value={{
      active, stepIndex, steps: TOUR_STEPS, currentStep,
      ready, setReady,
      start, dismiss, next, prev,
      registerPrepareHandler, runPrepareHandler,
    }}>
      {children}
    </TourContext.Provider>
  )
}

export function useTour(): TourContextType {
  const context = useContext(TourContext)
  if (!context) throw new Error('useTour must be used within a TourProvider')
  return context
}
