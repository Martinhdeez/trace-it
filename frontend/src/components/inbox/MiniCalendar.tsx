import { useState } from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { getLocale, t } from '../../i18n'
import { cn } from '../../lib/cn'
import { dayKey, formatAmount, SOON_DAYS, type Triage } from '../../lib/urgency'

const WEEKDAYS = ['L', 'M', 'X', 'J', 'V', 'S', 'D']
/** Six weeks always: every month takes the same room, so the card never jumps. */
const CELLS = 42

const ease = [0.23, 1, 0.32, 1] as const

/**
 * One month of pending documents, grouped by due date. Heat weighs time (70%),
 * volume (20%, saturated at six documents) and the existing large-amount flag (10%).
 * This only presents the queue; it never changes its order or an engine decision.
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
    <section className="rounded-[16px] bg-surface p-4 ring-1 ring-line">
      <header className="mb-2 flex items-center justify-between">
        <button
          type="button"
          aria-label="Mes anterior"
          onClick={() => shift(-1)}
          className="grid h-10 w-10 place-items-center rounded-full text-muted hover:bg-canvas hover:text-ink active:scale-90 transition-transform"
        >
          <ChevronLeft size={16} strokeWidth={1.75} />
        </button>
        <button
          type="button"
          onClick={() => go(new Date(today.getFullYear(), today.getMonth(), 1))}
          disabled={onToday}
          title={onToday ? undefined : 'Volver al mes actual'}
          className="relative h-10 min-w-[130px] overflow-hidden rounded-full px-2 text-[15px] font-medium capitalize enabled:hover:bg-canvas"
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
          className="grid h-10 w-10 place-items-center rounded-full text-muted hover:bg-canvas hover:text-ink active:scale-90 transition-transform"
        >
          <ChevronRight size={16} strokeWidth={1.75} />
        </button>
      </header>

      <div className="grid grid-cols-7 gap-0.5 text-center">
        {WEEKDAYS.map((day) => (
          <span key={day} className="py-1.5 font-mono text-[12px] text-faint">
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
              const active = selected === key
              const amount = due.every((entry) => entry.amount != null)
                ? due.reduce((sum, entry) => sum + (entry.amount ?? 0), 0)
                : null
              const dateLabel = date.toLocaleDateString(getLocale(), { day: 'numeric', month: 'long', year: 'numeric' })
              const description = due.length
                ? `${dateLabel}: ${due.length} ${t(due.length === 1 ? 'calendar.invoice' : 'calendar.invoices')}${amount == null ? '' : `. ${formatAmount(amount)}`}`
                : `${dateLabel}: ${t('calendar.noInvoices')}`
              return (
                <motion.button
                  key={key}
                  type="button"
                  onClick={() => onSelect(active ? null : key)}
                  aria-label={description}
                  aria-pressed={active}
                  aria-current={key === todayKey ? 'date' : undefined}
                  initial={reduce ? false : { opacity: 0, scale: 0.85 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ duration: 0.24, ease, delay: reduce ? 0 : (index % 7) * 0.012 + Math.floor(index / 7) * 0.018 }}
                  title={description}
                  style={due.length ? { backgroundColor: heatColor(due) } : undefined}
                  className={cn(
                    'relative flex h-11 min-w-0 flex-col items-center justify-center gap-0.5 rounded-[8px] font-mono text-[13px] tabular-nums transition-[background-color,box-shadow] hover:ring-1 hover:ring-ink/40',
                    due.length ? 'font-medium text-ink' : inMonth ? 'text-muted hover:bg-canvas' : 'text-faint/60 hover:bg-canvas',
                    active ? 'ring-2 ring-ink ring-offset-2 ring-offset-surface' : key === todayKey ? 'ring-1 ring-ink/30' : '',
                  )}
                >
                  <span className="leading-4">{date.getDate()}</span>
                  {due.length ? (
                    <span className="font-sans text-[10px] leading-3">
                      {due.length > 99 ? '99+' : due.length} {t('calendar.invoiceShort')}
                    </span>
                  ) : null}
                </motion.button>
              )
            })}
          </motion.div>
        </AnimatePresence>
      </div>

      <footer className="mt-3 space-y-2 border-t border-hairline pt-3 text-[11px] text-muted">
        <div className="flex items-center gap-2" title={t('calendar.heatHint')}>
          <span>{t('calendar.less')}</span>
          <span aria-hidden="true" className="h-2 flex-1 rounded-full bg-linear-to-r from-yellow-400/20 via-orange-500/50 to-red-500/80" />
          <span>{t('calendar.morePriority')}</span>
        </div>
        <p>{t('calendar.byDueDate')}</p>
        {selected ? (
          <button type="button" onClick={() => onSelect(null)} className="text-ink underline">
            {t('calendar.clear')}
          </button>
        ) : null}
      </footer>
    </section>
  )
}

function heatColor(invoices: Triage[]): string {
  const days = invoices[0].daysLeft ?? SOON_DAYS + 1
  const urgency = days < 0
    ? 0.9 + Math.min(-days / 30, 1) * 0.1
    : days <= SOON_DAYS
      ? 0.4 + (1 - days / SOON_DAYS) * 0.35
      : 0.15
  const density = Math.min((invoices.length - 1) / 5, 1)
  const large = invoices.some((entry) => entry.flags.includes('large')) ? 1 : 0
  const score = urgency * 0.7 + density * 0.2 + large * 0.1
  const hue = 48 * (1 - Math.min(score / 0.75, 1))
  return `hsl(${hue} 90% 52% / ${0.16 + score * 0.64})`
}
