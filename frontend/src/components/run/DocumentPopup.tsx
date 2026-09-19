import { X } from 'lucide-react'
import { useState } from 'react'
import type { InstanceDetail, TraceEvent } from '../../api/contracts'
import { formatMs } from '../../lib/format'
import { label } from '../../lib/status'
import { Overlay } from '../shell/Overlay'
import { StatusBadge } from '../shell/StatusBadge'
import { DocumentPane } from './DocumentPane'

export function DocumentPopup({
  instance,
  onClose,
  initialSymbol,
}: {
  instance: InstanceDetail
  onClose: () => void
  initialSymbol?: string
}) {
  const [showInfo, setShowInfo] = useState(false)
  const cost = processingCost(instance.eventos)
  const current = label(instance)

  return (
    <Overlay onClose={onClose} size="xl">
      <div role="dialog" aria-modal="true" aria-label="Original document" className="flex h-full min-h-0 flex-col overflow-hidden rounded-[20px] bg-surface shadow-pop ring-1 ring-line md:flex-row">
        <div className="flex min-h-0 min-w-0 flex-1 flex-col">
          <header className="flex shrink-0 items-center justify-between gap-3 border-b border-hairline px-4 py-3">
            <div className="min-w-0">
              <p className="text-[11px] text-muted">Documento</p>
              <h2 className="truncate font-mono text-[13px]">{instance.nombre}</h2>
            </div>
            <button
              type="button"
              aria-expanded={showInfo}
              aria-controls="document-info"
              onClick={() => setShowInfo((value) => !value)}
              className="ml-auto shrink-0 rounded-full px-3 py-1 text-[12px] text-muted ring-1 ring-line hover:bg-canvas"
            >
              Info
            </button>
            <button
              type="button"
              onClick={onClose}
              aria-label="Cerrar"
              className="grid h-7 w-7 shrink-0 place-items-center rounded-full text-muted hover:bg-canvas hover:text-ink"
            >
              <X size={14} strokeWidth={1.75} />
            </button>
          </header>
          <DocumentPane instanceId={instance.id} name={instance.nombre} embedded initialSymbol={initialSymbol} />
        </div>

        {showInfo ? <aside id="document-info" aria-label="Document information" className="max-h-[35%] shrink-0 overflow-y-auto border-t border-hairline px-4 py-4 md:max-h-none md:w-[220px] md:border-t-0 md:border-l">
          <Section title="Info">
            <div className="flex items-center justify-between gap-2">
              <span className="text-[12px] text-muted">Resultado</span>
              <StatusBadge value={current} />
            </div>
            <Row label="hash" value={instance.fichero_hash.slice(0, 12)} mono />
            <Row
              label="símbolos"
              value={String(Object.keys(instance.simbolos ?? {}).length)}
            />
          </Section>

          <Section title="Coste de procesamiento">
            <p className="font-mono text-[22px] tracking-[-0.04em] tabular-nums">
              {cost.totalMs ? formatMs(cost.totalMs) : '—'}
            </p>
            {cost.input || cost.output ? (
              <p className="mt-1 font-mono text-[11px] text-muted">
                {cost.input.toLocaleString('es-ES')} in · {cost.output.toLocaleString('es-ES')} out
              </p>
            ) : null}
            {cost.usd ? (
              <p className="mt-0.5 font-mono text-[11px] text-muted">
                ${cost.usd.toLocaleString('en-US', { minimumFractionDigits: 4, maximumFractionDigits: 4 })}
              </p>
            ) : null}
          </Section>

          <Section title={`Runs · ${instance.eventos.length}`}>
            {instance.eventos.length === 0 ? (
              <p className="text-[12px] text-muted">Este documento aún no tiene pasos.</p>
            ) : (
              <ol className="-mx-1">
                {instance.eventos.map((event, index) => (
                  <li
                    key={`${event.paso}-${index}`}
                    className="flex items-baseline justify-between gap-2 rounded-[8px] px-1 py-1.5"
                  >
                    <span className="min-w-0 truncate font-mono text-[11px] text-ink">{event.paso}</span>
                    <span className="shrink-0 font-mono text-[10.5px] text-faint">
                      {event.latencia_ms == null ? '—' : formatMs(event.latencia_ms)}
                    </span>
                  </li>
                ))}
              </ol>
            )}
            {instance.decisiones.length > 1 ? (
              <ul className="mt-2 border-t border-hairline pt-2">
                {instance.decisiones.map((decision) => (
                  <li key={decision.id} className="flex items-baseline justify-between gap-2 py-1">
                    <StatusBadge value={decision.decision} />
                    <span className="truncate text-[10.5px] text-faint">{decision.autor}</span>
                  </li>
                ))}
              </ul>
            ) : null}
          </Section>
        </aside> : null}
      </div>
    </Overlay>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mb-5 last:mb-0">
      <p className="mb-2 font-mono text-[11px] text-faint">{title}</p>
      {children}
    </section>
  )
}

function Row({
  label,
  value,
  mono,
}: {
  label: string
  value: string
  mono?: boolean
}) {
  return (
    <div className="flex items-baseline justify-between gap-3 py-0.5">
      <span className="text-[12px] text-muted">{label}</span>
      <span className={mono ? 'font-mono text-[11px] text-ink' : 'text-[12px] text-ink'}>{value}</span>
    </div>
  )
}

function processingCost(events: TraceEvent[]) {
  let totalMs = 0
  let input = 0
  let output = 0
  let usd = 0
  for (const event of events) {
    totalMs += event.latencia_ms ?? 0
    const data = event.datos
    if (!data) continue
    input += asNumber(data.input_tokens)
    output += asNumber(data.output_tokens)
    usd += asNumber(data.cost)
  }
  return { totalMs, input, output, usd }
}

function asNumber(value: unknown): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : 0
}
