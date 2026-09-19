import { Link } from 'react-router'
import type { ResolvedByPerson, ValidationChange } from '../../api/contracts'
import { t } from '../../i18n'
import { paths } from '../../lib/paths'

function transitions(changes: ValidationChange[]): [string, number][] {
  const totals = new Map<string, number>()
  for (const change of changes) {
    const key = `${change.before} → ${change.after}`
    totals.set(key, (totals.get(key) ?? 0) + 1)
  }
  return [...totals].sort(([a], [b]) => a.localeCompare(b))
}

function Cases({ processId, title, items, link = paths.instance }: {
  processId: number
  title: string
  items: ValidationChange[]
  link?: (processId: number, instanceId: number) => string
}) {
  if (!items.length) return null
  return <details className="rounded-[10px] bg-canvas px-3 py-2">
    <summary className="cursor-pointer text-[12px] text-muted">{title} · {items.length}</summary>
    <ul className="mt-2 max-h-48 space-y-1 overflow-y-auto">
      {items.map(item => <li key={`${item.instance_id}:${item.before}:${item.after}`} className="flex items-baseline gap-2 text-[12px]">
        <Link to={link(processId, item.instance_id)} className="min-w-0 flex-1 truncate text-ink hover:underline">
          {item.name || `Caso ${item.instance_id}`}
        </Link>
        <span className="shrink-0 font-mono text-[10px] text-muted">{item.before} → {item.after}</span>
      </li>)}
    </ul>
  </details>
}

/** The saved simulation report in terms a manager can approve. */
export function ValidationImpact({ processId, validation }: {
  processId: number
  validation: {
    unchanged?: number
    changes?: ValidationChange[]
    conflicts?: ValidationChange[]
    resolved_by_person?: ResolvedByPerson[]
    errors?: { instance_id: number; name?: string; reason?: string }[]
  }
}) {
  const changes = validation.changes ?? []
  const conflicts = validation.conflicts ?? []
  const errors = validation.errors ?? []
  const unchanged = validation.unchanged ?? 0
  const total = unchanged + changes.length + conflicts.length
  // reviewer-agent FE-4 (docs/reviewer-agent.md): the manager sees how the draft treats their own
  // resolutions before publishing. If merging a newer version from Carlos, keep his UI and
  // preserve: agree when after === resolution; contradicting cases link to review?i=<instance>.
  const mine = validation.resolved_by_person ?? []
  const contradicting = mine.filter(item => item.after !== item.resolution)

  return <div className="space-y-3">
    <div className="grid grid-cols-2 overflow-hidden rounded-[10px] bg-canvas ring-1 ring-line sm:grid-cols-4">
      {([
        ['Evaluadas', total],
        ['Sin cambio', unchanged],
        ['Cambiarían', changes.length],
        ['Conflictos', conflicts.length],
      ] satisfies [string, number][]).map(([label, value]) => <div key={label} className="border-b border-r border-hairline px-3 py-2 last:border-r-0 sm:border-b-0">
        <p className="text-[10px] uppercase tracking-[0.08em] text-faint">{label}</p>
        <p className="mt-1 font-mono text-[18px] tabular-nums">{value}</p>
      </div>)}
    </div>

    {changes.length || conflicts.length ? <div className="flex flex-wrap gap-1.5">
      {transitions([...changes, ...conflicts]).map(([label, count]) => <span key={label} className="rounded-full bg-canvas px-2 py-1 font-mono text-[10px] text-muted ring-1 ring-line">
        {label} · {count}
      </span>)}
    </div> : <p className="text-[12px] text-muted">Ninguna decisión cambiaría con esta versión.</p>}

    {mine.length ? <p className="text-[12px] text-muted">
      {t('reviewerAgent.yourDecisions')}: {mine.length} — {t('reviewerAgent.agree')} {mine.length - contradicting.length}, {t('reviewerAgent.contradict')} {contradicting.length}
    </p> : null}
    <Cases processId={processId} title={t('reviewerAgent.contradicting')} items={contradicting} link={paths.reviewCase} />

    <Cases processId={processId} title="Decisiones del motor que cambiarían" items={changes} />
    <Cases processId={processId} title="Decisiones protegidas que entrarían en conflicto" items={conflicts} />
    {errors.length ? <details className="rounded-[10px] bg-canvas px-3 py-2">
      <summary className="cursor-pointer text-[12px] text-nopagar">Errores de evaluación · {errors.length}</summary>
      <ul className="mt-2 list-disc space-y-1 pl-5 text-[11px] text-muted">
        {errors.map(item => <li key={item.instance_id}>{item.name || `Caso ${item.instance_id}`}: {item.reason || 'error desconocido'}</li>)}
      </ul>
    </details> : null}
  </div>
}
