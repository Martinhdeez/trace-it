import { AnimatePresence, motion } from 'motion/react'
import type { DecisionType } from '../../api/contracts'
import { cn } from '../../lib/cn'
import {
  flagLabel,
  formatAmount,
  formatDay,
  plainReason,
  severity,
  type Flag,
  type Triage,
} from '../../lib/urgency'

const ease = [0.23, 1, 0.32, 1] as const

const TILE = {
  high: 'bg-nopagar-soft text-nopagar',
  medium: 'bg-urgent-soft text-urgent',
  low: 'bg-canvas text-muted',
} as const

/** The date flags live in the tile; the rest read as small words beside the reason. */
const EXTRA: Flag[] = ['large', 'reviewer', 'unread']

/**
 * The manager's work, most urgent first. Rows animate to their place when the list
 * changes, so a dropped invoice is seen arriving and taking its position.
 */
export function CaseList({
  cases,
  decisionTypes,
  selectedId,
  fresh,
  onSelect,
}: {
  cases: Triage[]
  decisionTypes: DecisionType[]
  selectedId: number | undefined
  /** Cases that just arrived from a drop: highlighted, with why they sit where they do. */
  fresh: Set<number>
  onSelect: (id: number) => void
}) {
  return (
    <ul className="space-y-1.5">
      <AnimatePresence initial={false}>
        {cases.map((entry, index) => {
          const level = severity(entry.flags)
          const isFresh = fresh.has(entry.item.id)
          const active = entry.item.id === selectedId
          return (
            <motion.li
              key={entry.item.id}
              layout
              initial={{ opacity: 0, y: -12, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, x: 24, transition: { duration: 0.2 } }}
              transition={{ duration: 0.45, ease }}
            >
              <button
                type="button"
                onClick={() => onSelect(entry.item.id)}
                className={cn(
                  'flex w-full items-center gap-4 rounded-[16px] bg-surface px-4 py-3.5 text-left ring-1 transition-shadow',
                  active ? 'shadow-float ring-ink/20' : 'ring-line hover:shadow-lift',
                  isFresh && 'ring-2 ring-focus/60',
                )}
              >
                <DueTile entry={entry} level={level} />
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-[14px] font-medium tracking-[-0.015em] text-ink">
                    {entry.party ?? entry.item.name}
                  </span>
                  <span className="mt-0.5 block truncate text-[12.5px] text-muted">
                    {plainReason(entry.item, decisionTypes).title}
                    {entry.flags
                      .filter((flag) => EXTRA.includes(flag))
                      .map((flag) => (
                        <span key={flag} className="text-escalar"> · {flagLabel(flag, entry.daysLeft)}</span>
                      ))}
                  </span>
                  {isFresh ? (
                    <motion.span
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      transition={{ delay: 0.35, duration: 0.3, ease }}
                      className="mt-2 block overflow-hidden rounded-[8px] bg-canvas px-2 py-1.5 text-[11.5px] text-ink"
                    >
                      <span>
                        Nueva · puesto {index + 1} de {cases.length}. {placement(entry)}
                      </span>
                    </motion.span>
                  ) : null}
                </span>
                <span className="shrink-0 text-right">
                  <span className="block font-mono text-[14px] tabular-nums text-ink">
                    {formatAmount(entry.amount)}
                  </span>
                  <span className="mt-0.5 block text-[11.5px] text-faint">vence {formatDay(entry.due)}</span>
                </span>
              </button>
            </motion.li>
          )
        })}
      </AnimatePresence>
    </ul>
  )
}

/** How late, or how close, in one glance: the number of days and the tone of the tier. */
function DueTile({ entry, level }: { entry: Triage; level: keyof typeof TILE }) {
  const days = entry.daysLeft
  return (
    <span
      className={cn(
        'flex h-12 w-14 shrink-0 flex-col items-center justify-center rounded-[12px]',
        TILE[level],
      )}
    >
      {days == null ? (
        <span className="text-[11px]">—</span>
      ) : (
        <>
          <span className="font-mono text-[16px] font-medium leading-none tabular-nums">
            {Math.abs(days)}
          </span>
          <span className="mt-1 text-[9.5px] leading-none">
            {days < 0 ? 'días tarde' : days === 0 ? 'hoy' : 'días'}
          </span>
        </>
      )}
    </span>
  )
}

/** Why a new case landed where it did, in the order the sort weighs it. */
function placement(entry: Triage): string {
  const why = entry.flags
    .filter((flag) => flag !== 'unread')
    .map((flag) => flagLabel(flag, entry.daysLeft).toLowerCase())
  return why.length
    ? `Sube por: ${why.join(', ')}.`
    : 'Sin urgencia: va detrás de las vencidas, las próximas y las de importe alto.'
}
