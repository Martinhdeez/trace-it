import { useEffect, useRef, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Check, ChevronDown } from 'lucide-react'
import { api } from '../../api/client'
import type { Finding, Rule, ValidationReport, VersionOut } from '../../api/contracts'
import { keys } from '../../api/queries'
import { cn } from '../../lib/cn'
import { formatRunDate } from '../../lib/format'
import { ruleLabel } from '../../lib/process'
import { useSession } from '../../state/session'
import { Button } from '../shell/Controls'
import { ErrorNotice, Notice } from '../shell/Notice'
import { ExpandableText } from '../shell/ExpandableText'
import { HistoricalCoverage } from './HistoricalCoverage'
import { ValidationImpact } from './ValidationImpact'
import { useDraft } from './useDraft'

export function VersionChip({
  versions,
  selected,
  onSelect,
  findings,
}: {
  /** Newest first. */
  versions: VersionOut[]
  selected: VersionOut | undefined
  onSelect: (version: VersionOut) => void
  findings: Finding[]
}) {
  const label = selected ? `v${selected.number}` : 'borrador'
  const current = versions[0]
  const [open, setOpen] = useState(false)
  const root = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const onPointer = (event: MouseEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false)
    }
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', onPointer)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onPointer)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  return (
    <div ref={root} className="relative shrink-0">
      <button
        type="button"
        aria-expanded={open}
        aria-haspopup="menu"
        onClick={() => setOpen((next) => !next)}
        className="inline-flex items-center gap-1 rounded-full bg-canvas px-2.5 py-1 font-mono text-[11px] text-ink ring-1 ring-line hover:bg-surface"
      >
        {label}
        <ChevronDown
          size={11}
          strokeWidth={1.75}
          className={cn('text-faint transition-transform', open && 'rotate-180')}
        />
      </button>
      {open ? (
        <div
          role="menu"
          className="absolute right-0 z-20 mt-1 w-72 origin-top-right rounded-[12px] bg-surface p-1 shadow-float ring-1 ring-line"
        >
          <p className="px-2.5 pb-1 pt-2 font-mono text-[10px] tracking-[0.12em] text-faint">
            VERSIONES · {versions.length}
          </p>
          {versions.length ? (
            <ul className="max-h-64 overflow-y-auto">
              {versions.map((version) => (
                <li key={version.id}>
                  <button
                    type="button"
                    role="menuitemradio"
                    aria-checked={version === selected}
                    onClick={() => {
                      onSelect(version)
                      setOpen(false)
                    }}
                    className={cn(
                      'flex w-full items-start gap-2 rounded-[8px] px-2.5 py-1.5 text-left hover:bg-canvas',
                      version === selected && 'bg-canvas',
                    )}
                  >
                    <span className="w-3 shrink-0 pt-0.5">
                      {version === selected ? <Check size={11} strokeWidth={2} /> : null}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="flex items-baseline justify-between gap-2">
                        <span className="font-mono text-[12px] text-ink">
                          v{version.number}
                          {version === current ? (
                            <span className="ml-1.5 text-pagar">en vigor</span>
                          ) : null}
                        </span>
                        <span className="shrink-0 font-mono text-[10px] text-faint">
                          {formatRunDate(version.created_at)}
                        </span>
                      </span>
                      <span className="block truncate text-[11px] text-muted" title={version.reason}>
                        {version.reason || version.author}
                      </span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="px-2.5 py-1.5 text-[12px] text-muted">Aún no hay versiones publicadas.</p>
          )}
          <div className="my-1 border-t border-hairline" />
          <p className="px-2.5 py-1.5 text-[12px] text-muted">
            {findings.length
              ? `Impacto histórico · ${findings.length} aviso${findings.length === 1 ? '' : 's'}`
              : 'Sin avisos sobre decisiones anteriores'}
          </p>
          {findings.length ? (
            <ul className="max-h-40 overflow-y-auto border-t border-hairline py-1">
              {findings.slice(0, 6).map((finding) => (
                <li key={finding.id} className="px-2.5 py-1 text-[11px] leading-4 text-muted">
                  {finding.type.replaceAll('_', ' ')}
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}

type SnapshotRule = { id?: number; text: string; decision: string; type: string }
type SnapshotSymbol = { name: string; type: string; description?: string }

/** A published version as it was: what it decided with, never editable from here. */
export function VersionView({
  processId,
  version,
  current,
  rules,
  onBack,
}: {
  processId: number
  version: VersionOut
  current: VersionOut
  rules: Rule[]
  onBack: () => void
}) {
  const queryClient = useQueryClient()
  const { isManager } = useSession()
  const { revision, pending } = useDraft(processId, isManager)
  const backtest = useMutation({
    mutationFn: () => api.backtestVersion(version.id),
  })
  const [restored, setRestored] = useState(false)
  const restore = useMutation({
    mutationFn: () => api.saveDraft(processId, {
      expected_revision: null,
      restore_version_id: version.id,
      refresh_agents: false,
    }),
    onSuccess: async () => {
      setRestored(true)
      await queryClient.invalidateQueries({ queryKey: keys.execution(processId) })
      await queryClient.invalidateQueries({ queryKey: keys.draft(processId) })
    },
  })
  const process = (version.snapshot.process ?? {}) as {
    description?: string
    symbols?: SnapshotSymbol[]
  }
  const snapshotRules = (version.snapshot.rules ?? []) as SnapshotRule[]
  // Summaries live on the rules; a version keeps each rule's id.
  const live = new Map(rules.map((rule) => [rule.id, rule]))

  return (
    <div className="space-y-6">
      <Notice
        title={version === current ? `v${version.number} en vigor` : `Estás viendo v${version.number}, solo lectura`}
        action={
          <button type="button" onClick={onBack} className="text-[12px] text-muted hover:text-ink">
            Volver a la definición
          </button>
        }
      >
        {formatRunDate(version.created_at)} · {version.author}
        {version.reason ? ` · ${version.reason}` : ''}
      </Notice>

      {isManager && version !== current ? <section className="space-y-2">
        {restored ? <Notice title={`v${version.number} restaurada como borrador`}>
          Valida y publica el borrador para ponerla en vigor como una versión nueva.
        </Notice> : pending ? <p className="text-[12px] text-muted">Comprobando el borrador…</p> : revision != null ? <p className="text-[12px] text-muted">
          Ya existe un borrador. Descártalo o publícalo antes de restaurar esta versión.
        </p> : <Button disabled={restore.isPending} onClick={() => restore.mutate()}>
          Restaurar como borrador
        </Button>}
        {restore.isError ? <ErrorNotice error={restore.error} /> : null}
      </section> : null}

      <section>
        <p className="mb-2 font-mono text-[11px] tracking-[0.12em] text-faint">IMPACTO HISTÓRICO AL PUBLICAR</p>
        <ValidationImpact processId={processId} validation={version.validation as ValidationReport} />
      </section>

      {isManager ? <section className="space-y-3">
        <h3 className="text-sm font-medium">Backtest v{version.number}</h3>
        <p className="text-[12px] text-muted">
          Compare this version with previous engine decisions using saved facts and the latest
          loaded sources. Original decisions stay unchanged. OCR is not repeated.
        </p>
        <Button disabled={backtest.isPending} onClick={() => backtest.mutate()}>
          {backtest.isPending ? 'Running backtest…' : 'Run backtest'}
        </Button>
        {backtest.isError ? <ErrorNotice error={backtest.error} /> : null}
        {backtest.data && !backtest.isPending ? <div role="status" className="space-y-3">
          {backtest.data.error ? <p className="text-sm text-nopagar">{backtest.data.error}</p> : <>
            <HistoricalCoverage validation={backtest.data} />
            {backtest.data.coverage?.total === 0
              ? <p className="text-[12px] text-muted">No previous decisions are available to compare.</p>
              : <ValidationImpact processId={processId} validation={backtest.data} />}
          </>}
        </div> : null}
      </section> : null}

      {process.description ? (
        <section>
          <p className="mb-2 font-mono text-[11px] tracking-[0.12em] text-faint">CONTEXTO</p>
          <ExpandableText text={process.description} className="text-[13px] leading-6 text-ink" />
        </section>
      ) : null}

      <section>
        <p className="mb-2 font-mono text-[11px] tracking-[0.12em] text-faint">
          NORMA · {snapshotRules.length}
        </p>
        <ul className="divide-y divide-hairline">
          {snapshotRules.map((rule, index) => {
            const known = rule.id != null ? live.get(rule.id) : undefined
            return (
              <li key={rule.id ?? index} className="flex h-9 items-center gap-2">
                <span className="min-w-0 flex-1 truncate text-[13px] text-ink" title={rule.text}>
                  {ruleLabel({ text: rule.text, summary: known?.summary })}
                </span>
                <span className="shrink-0 font-mono text-[10px] text-faint">{rule.decision}</span>
              </li>
            )
          })}
        </ul>
      </section>

      {process.symbols?.length ? (
        <section>
          <p className="mb-2 font-mono text-[11px] tracking-[0.12em] text-faint">
            ENTRADAS · {process.symbols.length}
          </p>
          <div className="flex flex-wrap gap-1.5">
            {process.symbols.map((symbol) => (
              <span
                key={symbol.name}
                title={symbol.description}
                className="rounded-full bg-canvas px-2 py-0.5 font-mono text-[11px] text-muted ring-1 ring-line"
              >
                {symbol.name}
              </span>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  )
}
