import { useState } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import { AlertTriangle, CheckCircle2, ChevronDown, FileSearch, XCircle } from 'lucide-react'
import type { InstanceDetail, Rule, RuleResult, SymbolReading } from '../../api/contracts'
import { formatMs } from '../../lib/format'
import { cn } from '../../lib/cn'
import { t } from '../../i18n'
import { label, tone } from '../../lib/status'
import { JsonHighlight } from '../../lib/jsonHighlight'
import { StatusBadge } from '../shell/StatusBadge'
import { DocumentPopup } from './DocumentPopup'

const ease = [0.23, 1, 0.32, 1] as const

/**
 * Why this instance ended where it did: the decision, the result of every rule
 * the engine ran, the symbols with their origin, and the trace of every step.
 */
export function TracePane({
  instance,
  rules,
}: {
  instance: InstanceDetail | undefined
  rules: Rule[]
}) {
  if (!instance) {
    return (
      <aside className="flex h-full min-h-0 min-w-0 flex-1 flex-col px-5 py-4 text-[13px] text-muted">
        Decisión
      </aside>
    )
  }

  const current = label(instance)
  const shown =
    current === instance.status
      ? t(`instanceStatus.${instance.status}`)
      : current.replaceAll('_', ' ')
  const latest = instance.decisions.at(-1)
  const results = (latest?.results ?? []) as RuleResult[]
  const symbols = Object.entries(instance.symbols ?? {}) as [string, SymbolReading][]
  const fired = results.filter((result) => result.fires === true).length
  const errors = results.filter((result) => result.fires === null).length
  const DecisionIcon =
    current === 'PAGAR' || current === 'APROBAR'
      ? CheckCircle2
      : current === 'NO_PAGAR' || current === 'RECHAZAR'
        ? XCircle
        : AlertTriangle
  const ruleText = (outcome: RuleResult) =>
    outcome.rule_text ?? rules.find((rule) => rule.id === outcome.rule_id)?.texto ?? `Regla ${outcome.rule_id}`

  return (
    <aside className="flex h-full min-h-0 min-w-0 flex-1 flex-col overflow-y-auto px-6 pb-4">
      <DocumentHeader instance={instance} />

      <div className="mx-auto w-full max-w-[820px] rounded-[16px] bg-surface px-6 py-6 ring-1 ring-line">
        <div className="flex items-start gap-4">
          <span
            className={cn(
              'grid h-10 w-10 shrink-0 place-items-center rounded-[12px]',
              (current === 'PAGAR' || current === 'APROBAR') && 'bg-pagar-soft text-pagar',
              (current === 'NO_PAGAR' || current === 'RECHAZAR') && 'bg-nopagar-soft text-nopagar',
              (current === 'ESCALAR' || current === 'PENDING') && 'bg-escalar-soft text-escalar',
            )}
          >
            <DecisionIcon size={19} strokeWidth={1.8} />
          </span>
          <div className="min-w-0 flex-1">
            <p className="text-[11px] text-muted">Decisión final</p>
            <p
              className={cn(
                'mt-1 text-[26px] font-medium leading-none tracking-[-0.045em]',
                (current === 'PAGAR' || current === 'APROBAR') && 'text-pagar',
                (current === 'NO_PAGAR' || current === 'RECHAZAR') && 'text-nopagar',
                (current === 'ESCALAR' || current === 'PENDING') && 'text-escalar',
              )}
            >
              {shown}
            </p>
            <p className="mt-2 text-[12.5px] leading-5 text-muted">
              {latest?.reason || 'El proceso todavía no ha emitido una decisión.'}
            </p>
          </div>
        </div>

        {latest ? (
          <div className="mt-5 grid grid-cols-3 gap-px overflow-hidden rounded-[10px] bg-rule ring-1 ring-line">
            <DecisionStat label="Reglas evaluadas" value={results.length} />
            <DecisionStat label="Activadas" value={fired} />
            <DecisionStat label="Errores" value={errors} />
          </div>
        ) : null}
        <div className="mt-4 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-muted">
          <span>{latest?.author === 'engine' ? 'Decidido por el motor' : latest?.author}</span>
          {latest ? <span className="font-mono text-faint">{latest.rules_hash.slice(0, 12)}</span> : null}
        </div>
      </div>

      <div className="mx-auto w-full max-w-[820px]">
        {results.length ? (
        <Block title={`reglas · ${results.length}`} openByDefault>
          <ul className="divide-y divide-hairline">
            {results.map((outcome) => (
              <li key={outcome.rule_id} className="px-3 py-2">
                <div className="flex items-baseline justify-between gap-2">
                  <span className="text-[12px] text-ink">{ruleText(outcome)}</span>
                  <span
                    className={cn(
                      'shrink-0 rounded-full px-1.5 py-0.5 font-mono text-[10px]',
                      outcome.fires === null && 'bg-nopagar-soft text-nopagar',
                      outcome.fires === true && tone('ESCALAR'),
                      outcome.fires === false && 'text-faint',
                    )}
                  >
                    {outcome.fires === null ? 'error' : outcome.fires ? 'salta' : 'ok'}
                  </span>
                </div>
                {outcome.fires !== false ? (
                  <p
                    className={cn(
                      'mt-0.5 font-mono text-[11px]',
                      outcome.fires === null ? 'text-nopagar' : 'text-muted',
                    )}
                  >
                    {outcome.reason}
                  </p>
                ) : null}
              </li>
            ))}
          </ul>
        </Block>
        ) : null}

        <Block title={`símbolos · ${symbols.length}`}>
        {symbols.length === 0 ? (
          <p className="px-3 py-3 text-[12px] text-muted">
            Nadie ha extraído los símbolos de esta instancia todavía.
          </p>
        ) : (
          <ul className="divide-y divide-hairline">
            {symbols.map(([name, symbol]) => (
              <li key={name} className="px-3 py-1.5">
                <div className="flex items-baseline justify-between gap-2">
                  <span className="font-mono text-[11px] text-muted">{name}</span>
                  <span className="truncate font-mono text-[12px] text-ink">
                    {symbol.value === null || symbol.value === undefined
                      ? '—'
                      : String(symbol.value)}
                  </span>
                </div>
                {symbol.origin ? <p className="text-[10.5px] text-faint">{symbol.origin}</p> : null}
              </li>
            ))}
          </ul>
        )}
        </Block>

        <Block title={`traza · ${instance.events.length} pasos`}>
        <ol className="divide-y divide-hairline">
          {instance.events.map((event, index) => (
            <li key={`${event.step}-${index}`} className="px-3 py-2">
              <div className="flex items-baseline justify-between gap-2">
                <span className="font-mono text-[11px] text-ink">{event.step}</span>
                <span className="font-mono text-[10.5px] text-faint">
                  {event.duration_ms == null ? '—' : formatMs(event.duration_ms)}
                </span>
              </div>
              {event.data ? (
                <p className="break-words text-[11.5px] text-muted">
                  {Object.entries(event.data)
                    .map(([key, value]) => `${key} ${String(value)}`)
                    .join(' · ')}
                </p>
              ) : null}
            </li>
          ))}
        </ol>
        </Block>

        {instance.decisions.length > 1 ? (
        <Block title={`histórico · ${instance.decisions.length}`}>
          <ul className="divide-y divide-hairline">
            {instance.decisions.map((decision) => (
              <li key={decision.id} className="flex items-baseline gap-2 px-3 py-2">
                <StatusBadge value={decision.decision} />
                <span className="min-w-0 flex-1 truncate text-[11.5px] text-muted">
                  {decision.reason}
                </span>
                <span className="shrink-0 text-[10.5px] text-faint">{decision.author}</span>
              </li>
            ))}
          </ul>
        </Block>
        ) : null}

        <Block title="línea de la exportación">
          <JsonHighlight value={{ file_id: instance.name, result: instance.decision }} />
        </Block>
      </div>
    </aside>
  )
}

function DocumentHeader({ instance }: { instance: InstanceDetail }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="mx-auto flex w-full max-w-[820px] items-center justify-between gap-3 py-3">
      <div className="min-w-0">
        <p className="text-[11px] text-muted">Resultado del proceso</p>
        <h2 className="mt-0.5 truncate font-mono text-[13px]">{instance.name}</h2>
      </div>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="inline-flex h-7 shrink-0 items-center gap-1.5 rounded-full bg-ink px-3 text-[12px] font-medium text-on-ink hover:bg-ink/90"
      >
        <FileSearch size={13} strokeWidth={1.7} />
        Abrir documento
      </button>
      {open ? <DocumentPopup instance={instance} onClose={() => setOpen(false)} /> : null}
    </div>
  )
}

function DecisionStat({ label: text, value }: { label: string; value: number }) {
  return (
    <div className="bg-surface px-3 py-2.5">
      <p className="font-mono text-[17px] tracking-[-0.04em] tabular-nums">{value}</p>
      <p className="mt-0.5 text-[10px] text-muted">{text}</p>
    </div>
  )
}

function Block({
  title,
  children,
  openByDefault,
}: {
  title: string
  children: React.ReactNode
  openByDefault?: boolean
}) {
  const [open, setOpen] = useState(Boolean(openByDefault))
  return (
    <div className="mt-2 overflow-hidden rounded-[16px] ring-1 ring-line">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="flex w-full items-center justify-between px-3 py-2 text-left"
      >
        <span className="font-mono text-[11px] text-faint">{title}</span>
        <motion.span animate={{ rotate: open ? 180 : 0 }} transition={{ duration: 0.18, ease }}>
          <ChevronDown size={14} strokeWidth={1.5} className="text-muted" />
        </motion.span>
      </button>
      <AnimatePresence initial={false}>
        {open ? (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.22, ease }}
            className="overflow-hidden"
          >
            {children}
          </motion.div>
        ) : null}
      </AnimatePresence>
    </div>
  )
}
