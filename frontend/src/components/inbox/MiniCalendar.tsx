import { useState } from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { cn } from '../../lib/cn'
import { dayKey, severity, type Triage } from '../../lib/urgency'

const WEEKDAYS = ['L', 'M', 'X', 'J', 'V', 'S', 'D']

const DOT = {
  high: 'bg-nopagar',
  medium: 'bg-escalar',
  low: 'bg-faint',
} as const

/**
 * One month, Monday first. A day with invoices due carries a dot in the colour of its most
 * urgent one; clicking it filters the list, clicking it again clears the filter.
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

  const byDay = new Map<string, Triage[]>()
  for (const item of cases) {
    if (!item.due) continue
    const key = dayKey(item.due)
    byDay.set(key, [...(byDay.get(key) ?? []), item])
  }

  const first = (month.getDay() + 6) % 7
  const length = new Date(month.getFullYear(), month.getMonth() + 1, 0).getDate()
  const cells = [
    ...Array.from({ length: first }, () => null),
    ...Array.from({ length }, (_, index) => new Date(month.getFullYear(), month.getMonth(), index + 1)),
  ]
  const todayKey = dayKey(today)
  const shift = (by: number) => setMonth(new Date(month.getFullYear(), month.getMonth() + by, 1))

  return (
    <section className="rounded-[16px] bg-surface p-3 ring-1 ring-line">
      <header className="mb-2 flex items-center justify-between">
        <button
          type="button"
          aria-label="Mes anterior"
          onClick={() => shift(-1)}
          className="grid h-7 w-7 place-items-center rounded-full text-muted hover:bg-canvas hover:text-ink"
        >
          <ChevronLeft size={14} strokeWidth={1.75} />
        </button>
        <p className="text-[13px] font-medium capitalize">
          {month.toLocaleDateString('es-ES', { month: 'long', year: 'numeric' })}
        </p>
        <button
          type="button"
          aria-label="Mes siguiente"
          onClick={() => shift(1)}
          className="grid h-7 w-7 place-items-center rounded-full text-muted hover:bg-canvas hover:text-ink"
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
        {cells.map((date, index) => {
          if (!date) return <span key={`blank-${index}`} />
          const key = dayKey(date)
          const due = byDay.get(key) ?? []
          const worst = due.length
            ? due.map((item) => severity(item.flags)).sort((a, b) => rank(a) - rank(b))[0]
            : null
          const active = selected === key
          return (
            <button
              key={key}
              type="button"
              onClick={() => onSelect(active ? null : key)}
              title={due.length ? `${due.length} factura${due.length === 1 ? '' : 's'} vence${due.length === 1 ? '' : 'n'}` : undefined}
              className={cn(
                'relative flex h-8 flex-col items-center justify-center rounded-[8px] font-mono text-[11.5px] tabular-nums',
                active
                  ? 'bg-ink text-on-ink'
                  : key === todayKey
                    ? 'text-ink ring-1 ring-ink/30'
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
                  )}
                />
              ) : null}
            </button>
          )
        })}
      </div>

      <footer className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 border-t border-hairline pt-2.5 text-[11px] text-muted">
        <Legend tone="high">Vencida</Legend>
        <Legend tone="medium">Pronto o alta</Legend>
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
