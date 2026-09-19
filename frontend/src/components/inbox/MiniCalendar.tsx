import { useState } from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { cn } from '../../lib/cn'
import { dayKey, severity, type Triage } from '../../lib/urgency'

const WEEKDAYS = ['L', 'M', 'X', 'J', 'V', 'S', 'D']
/** Six weeks always: every month takes the same room, so the card never jumps. */
const CELLS = 42

const DOT = {
  high: 'bg-nopagar',
  medium: 'bg-urgent-dot',
  low: 'bg-faint',
} as const

const ease = [0.23, 1, 0.32, 1] as const

/**
 * One month, Monday first, padded with the days around it. A day with invoices due carries
 * a dot in the colour of its most urgent one; clicking it filters the list, clicking it
 * again clears the filter.
 */
export function MiniCalendar({
  cases,
  today,
  selected,
  onSelect,
}: {
  cases: Triage[]
  today: Date
  selected: string | null
  onSelect: (day: string | null) => void
}) {
  const [month, setMonth] = useState(() => new Date(today.getFullYear(), today.getMonth(), 1))
  // Which way the last change went, so the new month slides in from that side.
  const [direction, setDirection] = useState(0)
  const reduce = useReducedMotion()

  const byDay = new Map<string, Triage[]>()
  for (const item of cases) {
    if (!item.due) continue
    const key = dayKey(item.due)
    byDay.set(key, [...(byDay.get(key) ?? []), item])
  }

  const offset = (month.getDay() + 6) % 7
  const cells = Array.from(
    { length: CELLS },
    (_, index) => new Date(month.getFullYear(), month.getMonth(), index - offset + 1),
  )
  const todayKey = dayKey(today)
  const monthKey = `${month.getFullYear()}-${month.getMonth()}`
  const onToday = month.getFullYear() === today.getFullYear() && month.getMonth() === today.getMonth()

  const go = (next: Date) => {
    setDirection(Math.sign(next.getTime() - month.getTime()))
    setMonth(next)
  }
  const shift = (by: number) => go(new Date(month.getFullYear(), month.getMonth() + by, 1))

  const slide = reduce ? 0 : 28
  const variants = {
    enter: (dir: number) => ({ x: dir * slide, opacity: 0, filter: reduce ? 'none' : 'blur(2px)' }),
    center: { x: 0, opacity: 1, filter: 'blur(0px)' },
    exit: (dir: number) => ({ x: -dir * slide, opacity: 0, filter: reduce ? 'none' : 'blur(2px)' }),
  }

  return (
    <section className="rounded-[16px] bg-surface p-3 ring-1 ring-line">
      <header className="mb-2 flex items-center justify-between">
        <button
          type="button"
          aria-label="Mes anterior"
          onClick={() => shift(-1)}
          className="grid h-7 w-7 place-items-center rounded-full text-muted hover:bg-canvas hover:text-ink active:scale-90 transition-transform"
        >
          <ChevronLeft size={14} strokeWidth={1.75} />
        </button>
        <button
          type="button"
          onClick={() => go(new Date(today.getFullYear(), today.getMonth(), 1))}
          disabled={onToday}
          title={onToday ? undefined : 'Volver al mes actual'}
          className="relative h-6 min-w-[130px] overflow-hidden rounded-full px-2 text-[13px] font-medium capitalize enabled:hover:bg-canvas"
        >
          <AnimatePresence initial={false} custom={direction} mode="popLayout">
            <motion.span
              key={monthKey}
              custom={direction}
              initial={{ y: reduce ? 0 : direction * 10, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              exit={{ y: reduce ? 0 : -direction * 10, opacity: 0 }}
              transition={{ duration: 0.22, ease }}
              className="block leading-6"
            >
              {month.toLocaleDateString('es-ES', { month: 'long', year: 'numeric' })}
            </motion.span>
          </AnimatePresence>
        </button>
        <button
          type="button"
          aria-label="Mes siguiente"
          onClick={() => shift(1)}
          className="grid h-7 w-7 place-items-center rounded-full text-muted hover:bg-canvas hover:text-ink active:scale-90 transition-transform"
        >
          <ChevronRight size={14} strokeWidth={1.75} />
        </button>
      </header>

      <div className="grid grid-cols-7 gap-0.5 text-center">
        {WEEKDAYS.map((day) => (
          <span key={day} className="py-1 font-mono text-[10px] text-faint">
            {day}
          </span>
        ))}
      </div>

      <div className="relative overflow-hidden">
        <AnimatePresence initial={false} custom={direction} mode="popLayout">
          <motion.div
            key={monthKey}
            custom={direction}
            variants={variants}
            initial="enter"
            animate="center"
            exit="exit"
            transition={{ duration: 0.28, ease }}
            className="grid grid-cols-7 gap-0.5 text-center"
          >
            {cells.map((date, index) => {
              const key = dayKey(date)
              const inMonth = date.getMonth() === month.getMonth()
              const due = byDay.get(key) ?? []
              const worst = due.length
                ? due.map((item) => severity(item.flags)).sort((a, b) => rank(a) - rank(b))[0]
                : null
              const active = selected === key
              return (
                <motion.button
                  key={key}
                  type="button"
                  onClick={() => onSelect(active ? null : key)}
                  initial={reduce ? false : { opacity: 0, scale: 0.85 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ duration: 0.24, ease, delay: reduce ? 0 : (index % 7) * 0.012 + Math.floor(index / 7) * 0.018 }}
                  title={
                    due.length
                      ? `${due.length} factura${due.length === 1 ? '' : 's'} vence${due.length === 1 ? '' : 'n'}`
                      : undefined
                  }
                  className={cn(
                    'relative flex h-8 flex-col items-center justify-center rounded-[8px] font-mono text-[11.5px] tabular-nums transition-colors',
                    active
                      ? 'bg-ink text-on-ink'
                      : key === todayKey
                        ? 'text-ink ring-1 ring-ink/30'
                        : !inMonth
                          ? 'text-faint/45 hover:bg-canvas'
                          : due.length
                            ? 'text-ink hover:bg-canvas'
                            : 'text-faint hover:bg-canvas',
                  )}
                >
                  {date.getDate()}
                  {worst ? (
                    <span
                      className={cn(
                        'absolute bottom-1 h-1 w-1 rounded-full',
                        active ? 'bg-on-ink' : DOT[worst],
                        !inMonth && !active && 'opacity-45',
                      )}
                    />
                  ) : null}
                </motion.button>
              )
            })}
          </motion.div>
        </AnimatePresence>
      </div>

      <footer className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 border-t border-hairline pt-2.5 text-[11px] text-muted">
        <Legend tone="high">Vencida</Legend>
        <Legend tone="medium">Urgente</Legend>
        <Legend tone="low">Resto</Legend>
        {selected ? (
          <button type="button" onClick={() => onSelect(null)} className="ml-auto text-ink underline">
            Quitar filtro
          </button>
        ) : null}
      </footer>
    </section>
  )
}

function rank(level: 'high' | 'medium' | 'low'): number {
  return level === 'high' ? 0 : level === 'medium' ? 1 : 2
}

function Legend({ tone, children }: { tone: keyof typeof DOT; children: string }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className={cn('h-1.5 w-1.5 rounded-full', DOT[tone])} />
      {children}
    </span>
  )
}
