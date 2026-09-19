import { useQuery } from '@tanstack/react-query'
import { api } from '../../api/client'
import type { PlaneHealth } from '../../api/contracts'
import { keys } from '../../api/queries'
import { t } from '../../i18n'
import { cn } from '../../lib/cn'

const HEALTH_ORDER = ['ok', 'degraded', 'down']
const HEALTH_COLOR: Record<string, string> = {
  ok: 'bg-emerald-500',
  degraded: 'bg-amber-500',
  down: 'bg-red-500',
}
const COMMIT = (import.meta.env.VITE_COMMIT_SHA || 'local').slice(0, 7)
const API_BASE = import.meta.env.VITE_API_URL ?? '/api'

/** The most severe status among the planes, or nothing until they are loaded. */
function worstHealth(planes: PlaneHealth[] | undefined): string | undefined {
  if (!planes?.length) return undefined
  return planes
    .map((plane) => plane.status)
    .reduce((worst, status) =>
      HEALTH_ORDER.indexOf(status) > HEALTH_ORDER.indexOf(worst) ? status : worst,
    )
}

function Dot({ status }: { status: string | undefined }) {
  return (
    <span
      className={cn(
        'h-2 w-2 shrink-0 rounded-full',
        status ? (HEALTH_COLOR[status] ?? 'bg-faint') : 'bg-faint',
      )}
    />
  )
}

/** One line under the user: overall health and build. Hover or focus shows each plane. */
export function SystemStatus({ compact = false }: { compact?: boolean }) {
  const planes = useQuery({
    queryKey: keys.planesHealth,
    queryFn: () => api.planesHealth(),
    refetchInterval: 30_000,
  })
  const health = planes.isError ? 'down' : worstHealth(planes.data)
  const label = planes.isError
    ? t('status.offline')
    : health
      ? t(`health.${health}`)
      : t('status.checking')

  return (
    <div className="group relative">
      <button
        type="button"
        aria-label={`${t('status.label')}: ${label}`}
        title={compact ? label : undefined}
        className={
          compact
            ? 'mx-auto grid h-9 w-9 place-items-center rounded-[10px] text-muted outline-none hover:bg-surface/60 hover:text-ink focus-visible:bg-surface/60'
            : 'flex w-full items-center gap-2 rounded-[10px] px-2.5 py-1.5 text-[12px] text-muted outline-none hover:bg-surface/60 hover:text-ink focus-visible:bg-surface/60'
        }
      >
        <Dot status={health} />
        {compact ? null : (
          <>
            <span className="flex-1 truncate text-left">{label}</span>
            <span className="font-mono text-[10px] text-faint">{COMMIT}</span>
          </>
        )}
      </button>

      <div
        role="tooltip"
        className={cn(
          'invisible absolute z-30 w-[220px] rounded-[12px] bg-surface py-1.5 opacity-0 shadow-float ring-1 ring-line transition-[opacity,transform,visibility] duration-150 group-focus-within:visible group-focus-within:translate-x-0 group-focus-within:translate-y-0 group-focus-within:opacity-100 group-hover:visible group-hover:translate-x-0 group-hover:translate-y-0 group-hover:opacity-100 motion-reduce:transition-none',
          compact ? 'bottom-0 left-full ml-1.5 -translate-x-1' : 'bottom-full left-0 mb-1.5 translate-y-1',
        )}
      >
        {planes.isError ? (
          <p className="px-3 py-1 text-[12px] text-nopagar">{t('status.apiDown')}</p>
        ) : (
          (planes.data ?? []).map((plane) => (
            <div
              key={plane.plane}
              title={plane.reason ?? undefined}
              className="flex items-center gap-2 px-3 py-1 text-[12px]"
            >
              <Dot status={plane.status} />
              <span className="flex-1 text-ink">{t(`planes.${plane.plane}`)}</span>
              <span className="text-muted">{t(`health.${plane.status}`)}</span>
            </div>
          ))
        )}
        <p className="mx-3 mt-1.5 truncate border-t border-rule pt-1.5 font-mono text-[10.5px] text-faint">
          {COMMIT} · {API_BASE}
        </p>
      </div>
    </div>
  )
}
