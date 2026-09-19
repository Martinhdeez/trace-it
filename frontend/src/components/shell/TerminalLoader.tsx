import { useEffect, useState } from 'react'
import { useReducedMotion } from 'motion/react'
import { cn } from '../../lib/cn'

const FRAMES = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']

/**
 * A terminal spinner: a braille frame, a verb that turns every few seconds and the time
 * spent. The verbs are flavour, not progress: the server reports none while it thinks.
 */
export function TerminalLoader({
  verbs,
  className,
}: {
  /** Shown in turn, a few seconds each; the last one stays. */
  verbs: readonly string[]
  className?: string
}) {
  const reduceMotion = useReducedMotion()
  const [tick, setTick] = useState(0)

  useEffect(() => {
    const timer = window.setInterval(() => setTick((value) => value + 1), 80)
    return () => window.clearInterval(timer)
  }, [])

  const seconds = Math.floor((tick * 80) / 1000)
  const verb = verbs[Math.min(Math.floor(seconds / 4), verbs.length - 1)] ?? ''

  return (
    <p
      role="status"
      aria-live="polite"
      className={cn('flex items-center gap-2 font-mono text-[12px] text-muted', className)}
    >
      <span className="w-3 text-ink" aria-hidden>
        {reduceMotion ? '⠿' : FRAMES[tick % FRAMES.length]}
      </span>
      <span className="text-ink">{verb}…</span>
      <span className="text-faint tabular-nums">{seconds}s</span>
    </p>
  )
}
