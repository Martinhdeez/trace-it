import { useState } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import { ChevronDown } from 'lucide-react'
import type { InstanceDetail, Rule, RuleOutcome } from '../../api/contracts'
import { formatMs } from '../../lib/format'
import { cn } from '../../lib/cn'
import { label, tone } from '../../lib/status'
import { JsonHighlight } from '../../lib/jsonHighlight'
import { StatusBadge } from '../shell/StatusBadge'

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
      <aside className="flex h-full min-h-0 w-[340px] shrink-0 flex-col px-5 py-4 text-[13px] text-muted">
        Decisión
      </aside>
    )
  }

  const current = label(instance)
  const latest = instance.decisiones.at(-1)
  const symbols = Object.entries(instance.simbolos ?? {})
  const ruleText = (outcome: RuleOutcome) =>
    rules.find((rule) => rule.id === outcome.regla_id)?.texto ?? `Regla ${outcome.regla_id}`

  return (
      <aside className="flex h-full min-h-0 w-[340px] shrink-0 flex-col overflow-y-auto px-2 pb-3">
      <div className="px-3 py-3">
        <h2 className="text-[13px] font-medium">Decisión</h2>
      </div>

      <div className="rounded-[16px] bg-well px-4 py-4 ring-1 ring-black/[0.04]">
        <p className="font-mono text-[12px] text-muted">{latest?.motivo || instance.estado}</p>
        <p
          className={cn(
            'mt-2 text-[28px] font-medium leading-none tracking-[-0.045em]',
            current === 'PAGAR' && 'text-pagar',
            current === 'NO_PAGAR' && 'text-nopagar',
            (current === 'ESCALAR' || current === 'REVISION') && 'text-escalar',
          )}
        >
          {current.replaceAll('_', ' ')}
        </p>
        {latest ? (
          <p className="mt-2 truncate text-[12px] text-muted">
            {latest.autor === 'motor' ? 'Motor' : latest.autor} ·{' '}
            <span className="font-mono">{latest.reglas_hash.slice(0, 12) || '—'}</span>
          </p>
        ) : null}
      </div>

      {latest?.resultados.length ? (
        <Block title={`reglas · ${latest.resultados.length}`} openByDefault>
          <ul className="divide-y divide-hairline">
            {latest.resultados.map((outcome) => (
              <li key={outcome.regla_id} className="px-3 py-2">
                <div className="flex items-baseline justify-between gap-2">
                  <span className="text-[12px] text-ink">{ruleText(outcome)}</span>
                  <span
                    className={cn(
                      'shrink-0 rounded-full px-1.5 py-0.5 font-mono text-[10px]',
                      outcome.salta === null && 'bg-nopagar-soft text-nopagar',
                      outcome.salta === true && tone('ESCALAR'),
                      outcome.salta === false && 'text-faint',
                    )}
                  >
                    {outcome.salta === null ? 'error' : outcome.salta ? 'salta' : 'ok'}
                  </span>
                </div>
                {outcome.salta !== false ? (
                  <p
                    className={cn(
                      'mt-0.5 font-mono text-[11px]',
                      outcome.salta === null ? 'text-nopagar' : 'text-muted',
                    )}
                  >
                    {outcome.motivo}
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
                    {symbol.valor === null || symbol.valor === undefined
                      ? '—'
                      : String(symbol.valor)}
                  </span>
                </div>
                {symbol.origen ? <p className="text-[10.5px] text-faint">{symbol.origen}</p> : null}
              </li>
            ))}
          </ul>
        )}
      </Block>

      <Block title={`traza · ${instance.eventos.length} pasos`}>
        <ol className="divide-y divide-hairline">
          {instance.eventos.map((event, index) => (
            <li key={`${event.paso}-${index}`} className="px-3 py-2">
              <div className="flex items-baseline justify-between gap-2">
                <span className="font-mono text-[11px] text-ink">{event.paso}</span>
                <span className="font-mono text-[10.5px] text-faint">
                  {event.latencia_ms == null ? '—' : formatMs(event.latencia_ms)}
                </span>
              </div>
              {event.datos ? (
                <p className="break-words text-[11.5px] text-muted">
                  {Object.entries(event.datos)
                    .map(([key, value]) => `${key} ${String(value)}`)
                    .join(' · ')}
                </p>
              ) : null}
            </li>
          ))}
        </ol>
      </Block>

      {instance.decisiones.length > 1 ? (
        <Block title={`histórico · ${instance.decisiones.length}`}>
          <ul className="divide-y divide-hairline">
            {instance.decisiones.map((decision) => (
              <li key={decision.id} className="flex items-baseline gap-2 px-3 py-2">
                <StatusBadge value={decision.decision} />
                <span className="min-w-0 flex-1 truncate text-[11.5px] text-muted">
                  {decision.motivo}
                </span>
                <span className="shrink-0 text-[10.5px] text-faint">{decision.autor}</span>
              </li>
            ))}
          </ul>
        </Block>
      ) : null}

      <Block title="línea de la exportación">
        <JsonHighlight value={{ file_id: instance.nombre, result: instance.decision }} />
      </Block>
    </aside>
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
    <div className="mt-2 overflow-hidden rounded-[16px] ring-1 ring-black/[0.06]">
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
