import { useEffect, useState, useCallback, useRef } from 'react'
import { createPortal } from 'react-dom'
import { useNavigate, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'motion/react'
import { useTour } from '../contexts/TourContext'
import type { TourPlacement } from '../config/tour-steps'

interface Rect {
  top: number
  left: number
  width: number
  height: number
}

const TOOLTIP_WIDTH = 300
const TOOLTIP_OFFSET = 12
const PADDING = 12

const TOOLTIP_HEIGHT_ESTIMATE = 280

function getTooltipPosition(
  target: Rect,
  placement: TourPlacement,
  vw: number,
  vh: number,
): { top: number; left: number } {
  const isMobile = vw < 1024

  if (isMobile) {
    const centeredLeft = Math.max(PADDING, (vw - TOOLTIP_WIDTH) / 2)
    // For 'top' placement (e.g. optimize button near bottom), prefer above target
    if (placement === 'top') {
      const above = target.top - TOOLTIP_HEIGHT_ESTIMATE - TOOLTIP_OFFSET
      const fitsAbove = above >= PADDING
      if (fitsAbove) return { top: above, left: centeredLeft }
    }
    const below = target.top + target.height + TOOLTIP_OFFSET
    const fitsBelow = below + TOOLTIP_HEIGHT_ESTIMATE < vh
    return {
      top: fitsBelow ? below : Math.max(PADDING, target.top - TOOLTIP_HEIGHT_ESTIMATE - TOOLTIP_OFFSET),
      left: centeredLeft,
    }
  }

  let top = 0
  let left = 0

  switch (placement) {
    case 'right':
      top = target.top + target.height / 2 - 80
      left = target.left + target.width + TOOLTIP_OFFSET
      if (left + TOOLTIP_WIDTH > vw - PADDING) {
        left = target.left - TOOLTIP_WIDTH - TOOLTIP_OFFSET
      }
      break
    case 'left':
      top = target.top + target.height / 2 - 80
      left = target.left - TOOLTIP_WIDTH - TOOLTIP_OFFSET
      if (left < PADDING) {
        left = target.left + target.width + TOOLTIP_OFFSET
      }
      break
    case 'bottom':
      top = target.top + target.height + TOOLTIP_OFFSET
      left = target.left + target.width / 2 - TOOLTIP_WIDTH / 2
      break
    case 'top':
      top = target.top - TOOLTIP_OFFSET - 160
      left = target.left + target.width / 2 - TOOLTIP_WIDTH / 2
      break
  }

  left = Math.max(PADDING, Math.min(left, vw - TOOLTIP_WIDTH - PADDING))
  top = Math.max(PADDING, Math.min(top, vh - TOOLTIP_HEIGHT_ESTIMATE - PADDING))

  return { top, left }
}

function SpotlightOverlay({ target }: { target: Rect }) {
  const { dismiss } = useTour()
  return (
    <div className="fixed inset-0 z-[900] pointer-events-none" aria-hidden="true">
      <div className="absolute bg-black/50 pointer-events-auto"
        style={{ top: 0, left: 0, right: 0, height: Math.max(0, target.top - 4) }}
        onClick={dismiss} />
      <div className="absolute bg-black/50 pointer-events-auto"
        style={{ top: target.top + target.height + 4, left: 0, right: 0, bottom: 0 }}
        onClick={dismiss} />
      <div className="absolute bg-black/50 pointer-events-auto"
        style={{ top: Math.max(0, target.top - 4), left: 0, width: Math.max(0, target.left - 4), height: target.height + 8 }}
        onClick={dismiss} />
      <div className="absolute bg-black/50 pointer-events-auto"
        style={{ top: Math.max(0, target.top - 4), left: target.left + target.width + 4, right: 0, height: target.height + 8 }}
        onClick={dismiss} />
      <div className="absolute rounded-lg ring-2 ring-brand-accent"
        style={{ top: target.top - 4, left: target.left - 4, width: target.width + 8, height: target.height + 8, pointerEvents: 'none' }} />
    </div>
  )
}

export function TourTooltip() {
  const { active, currentStep, stepIndex, steps, ready, setReady, next, prev, dismiss, runPrepareHandler } = useTour()
  const navigate = useNavigate()
  const location = useLocation()
  const [targetRect, setTargetRect] = useState<Rect | null>(null)
  const [vp, setVp] = useState({ w: window.innerWidth, h: window.innerHeight })
  const preparingRef = useRef(false)

  const measureTarget = useCallback(() => {
    if (!currentStep) return
    // Pick the first element with this tour id that is actually visible on screen
    const els = document.querySelectorAll<HTMLElement>(`[data-tour="${currentStep.id}"]`)
    const el = Array.from(els).find((e) => {
      const r = e.getBoundingClientRect()
      return r.width > 0 && r.height > 0 && r.top >= 0 && r.left >= 0
    }) ?? els[0] ?? null
    if (!el) { setTargetRect(null); return }
    const r = el.getBoundingClientRect()
    setVp({ w: window.innerWidth, h: window.innerHeight })
    setTargetRect({ top: r.top, left: r.left, width: r.width, height: r.height })
  }, [currentStep])

  // Run preparation sequence whenever step changes (ready goes false)
  useEffect(() => {
    if (!active || ready || preparingRef.current) return
    if (!currentStep) return

    preparingRef.current = true

    const run = async () => {
      const isMobile = window.innerWidth < 1024
      const needsNav = currentStep.route && location.pathname !== currentStep.route

      // Step 1: navigate if needed
      if (needsNav) {
        navigate(currentStep.route!)
        // Wait for React to render the new route
        await new Promise((r) => setTimeout(r, 120))
      }

      // Step 2: run prepare actions in order (open sidebar, close sheet, etc.)
      const sidebarActions = new Set<string>(['sidebar', 'close-sidebar'])
      if (currentStep.prepare?.length) {
        let needsWait = false
        for (const action of currentStep.prepare) {
          // On desktop, sidebar is always visible — skip sidebar open/close
          if (!isMobile && sidebarActions.has(action)) continue
          runPrepareHandler(action)
          needsWait = true
        }
        if (needsWait) {
          // Wait for HeadlessUI dialog (300ms) + animation to fully settle
          await new Promise((r) => setTimeout(r, 450))
        }
      }

      // Step 3: measure the target element (prefer visible/on-screen element)
      const els = document.querySelectorAll<HTMLElement>(`[data-tour="${currentStep.id}"]`)
      const el = Array.from(els).find((e) => {
        const r = e.getBoundingClientRect()
        return r.width > 0 && r.height > 0 && r.top >= 0 && r.left >= 0
      }) ?? els[0] ?? null
      if (el) {
        const rect = el.getBoundingClientRect()
        setVp({ w: window.innerWidth, h: window.innerHeight })
        setTargetRect({ top: rect.top, left: rect.left, width: rect.width, height: rect.height })
      } else {
        setTargetRect(null)
      }

      preparingRef.current = false
      setReady(true)
    }

    run()
  }, [active, ready, currentStep, location.pathname, navigate, runPrepareHandler, setReady])

  // Keep position in sync while tooltip is shown
  useEffect(() => {
    if (!active || !ready) return
    measureTarget()
    const ro = new ResizeObserver(measureTarget)
    ro.observe(document.documentElement)
    window.addEventListener('scroll', measureTarget, { passive: true })
    window.addEventListener('resize', measureTarget)
    return () => {
      ro.disconnect()
      window.removeEventListener('scroll', measureTarget)
      window.removeEventListener('resize', measureTarget)
    }
  }, [active, ready, measureTarget])

  // Dismiss on Escape
  useEffect(() => {
    if (!active) return
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') dismiss() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [active, dismiss])

  if (!active || !currentStep || !ready) return null

  const fallback: Rect = { top: vp.h / 2 - 100, left: vp.w / 2 - 150, width: 0, height: 0 }
  const rect = targetRect ?? fallback
  const { top, left } = getTooltipPosition(rect, currentStep.placement, vp.w, vp.h)
  const isFirst = stepIndex === 0
  const isLast = stepIndex === steps.length - 1

  return createPortal(
    <>
      <SpotlightOverlay target={rect} />
      <AnimatePresence mode="wait">
        <motion.div
          key={stepIndex}
          initial={{ opacity: 0, scale: 0.95, y: 4 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 4 }}
          transition={{ duration: 0.15 }}
          className="fixed z-[901] bg-white rounded-xl shadow-2xl border border-gray-100 p-4"
          style={{ top, left, width: TOOLTIP_WIDTH }}
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-brand-secondary">
              Step {stepIndex + 1} of {steps.length}
            </span>
            <button onClick={dismiss} className="text-gray-400 hover:text-gray-600 transition-colors -mr-1" aria-label="Close tour">
              <svg className="w-4 h-4" viewBox="0 0 20 20" fill="currentColor">
                <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
              </svg>
            </button>
          </div>

          <div className="flex gap-1 mb-3">
            {steps.map((_, i) => (
              <div key={i} className={`h-1 rounded-full transition-all duration-200 ${
                i === stepIndex ? 'bg-brand-accent flex-[2]' : i < stepIndex ? 'bg-brand-secondary/40 flex-1' : 'bg-gray-200 flex-1'
              }`} />
            ))}
          </div>

          <h4 className="font-heading font-semibold text-brand-primary text-sm mb-1">{currentStep.title}</h4>
          <p className="text-xs text-gray-600 leading-relaxed">{currentStep.body}</p>

          <div className="flex items-center justify-between mt-4 pt-3 border-t border-gray-100">
            <button
              onClick={prev}
              disabled={isFirst}
              className="text-xs font-medium text-gray-500 hover:text-gray-700 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              ← Back
            </button>
            <button
              onClick={next}
              className="inline-flex items-center gap-1.5 rounded-full bg-brand-accent px-4 py-1.5 text-xs font-bold text-white hover:bg-brand-accent/90 transition-colors"
            >
              {isLast ? 'Finish' : 'Next →'}
            </button>
          </div>
        </motion.div>
      </AnimatePresence>
    </>,
    document.body,
  )
}
