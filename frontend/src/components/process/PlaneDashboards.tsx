import { useState } from 'react'
import { Link } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import { api } from '../../api/client'
import type {
  AgentsMetrics,
  DecisionType,
  ExecutionMetrics,
  IngestionMetrics,
  Plane,
} from '../../api/contracts'
import { keys } from '../../api/queries'
import { t } from '../../i18n'
import { cn } from '../../lib/cn'
import { formatEuro, formatMs } from '../../lib/format'
import { paths } from '../../lib/paths'
import { Segmented } from '../shell/Controls'
import { DataTable } from '../shell/DataTable'
import { Empty, ErrorNotice } from '../shell/Notice'
import { StatusBadge } from '../shell/StatusBadge'
import { NestedCard } from '../shell/Well'

export type Cell = { label: string; value: string; note: string }

const COLUMNS = ['', 'sm:grid-cols-1', 'sm:grid-cols-2', 'sm:grid-cols-3', 'sm:grid-cols-4', 'sm:grid-cols-5']

/** The Panel's row of figures. Up to five per row, as the Panel draws them. */
export function MetricCells({ cells }: { cells: Cell[] }) {
  const rows: Cell[][] = []
  for (let index = 0; index < cells.length; index += 5) rows.push(cells.slice(index, index + 5))
  return (
    <>
      {rows.map((row) => (
        <section
          key={row[0].label}
          className={cn(
            'mb-6 grid overflow-hidden rounded-[16px] bg-surface ring-1 ring-line',
            COLUMNS[rows.length > 1 ? 5 : row.length],
          )}
        >
          {row.map((cell) => (
            <div
              key={cell.label}
              className="border-b border-hairline px-3.5 py-3 last:border-0 sm:border-b-0 sm:border-r sm:last:border-r-0"
            >
              <p className="text-[11px] text-muted">{cell.label}</p>
              <p className="mt-2 font-mono text-[22px] tracking-[-0.04em] tabular-nums">{cell.value}</p>
              <p className="mt-0.5 font-mono text-[10px] text-faint">{cell.note}</p>
            </div>
          ))}
        </section>
      ))}
    </>
  )
}

const PLANES: Plane[] = ['ingestion', 'agents', 'execution']

const number = (value: number | null | undefined) =>
  value == null ? '—' : value.toLocaleString('es-ES')
const ms = (value: number | null | undefined) => (value == null ? '—' : formatMs(value))

/** A known price in the currency the backend reports; otherwise how many calls have none, never 0. */
function cost(known: number, unpriced: number): string {
  if (known > 0) return `${formatEuro(known, 4)} USD`
  if (unpriced > 0) return `${unpriced} sin precio`
  return '—'
}

const mono = (text: string) => <span className="font-mono text-[12px]">{text}</span>
const muted = (text: string) => <span className="text-[12px] text-muted">{text}</span>

/**
 * Traceability, one plane at a time: reading the data, writing the rules, and running
 * them. Tokens and cost are never added across planes (docs/observability-dashboards.md).
 */
export function PlaneDashboards({
  processId,
  decisionTypes,
}: {
  processId: number
  decisionTypes: DecisionType[] | undefined
}) {
  const [plane, setPlane] = useState<Plane>('execution')
  const health = useQuery({ queryKey: keys.planesHealth, queryFn: () => api.planesHealth() })
  const status = health.data?.find((item) => item.plane === plane)

  return (
    <section className="mt-8">
      <div className="mb-3 flex items-end justify-between gap-4">
        <div>
          <h2 className="text-[18px] font-medium tracking-[-0.03em]">Trazabilidad</h2>
          <p className="mt-1 text-[12.5px] text-muted">
            Un panel por plano. Leer, escribir reglas y decidir cuestan distinto y no se suman.
          </p>
        </div>
        <Segmented
          value={plane}
          onChange={setPlane}
          options={PLANES.map((value) => ({ value, label: t(`planes.${value}`) }))}
        />
      </div>
      <NestedCard
        label={t(`planes.${plane}`)}
        action={
          status ? (
            <span title={status.reason ?? undefined}>
              <StatusBadge value={status.status}>{t(`health.${status.status}`)}</StatusBadge>
            </span>
          ) : null
        }
      >
        <div className="px-3.5 py-3">
          {health.isError ? <ErrorNotice error={health.error} /> : null}
          {plane === 'ingestion' ? <IngestionDashboard processId={processId} /> : null}
          {plane === 'agents' ? <AgentsDashboard processId={processId} /> : null}
          {plane === 'execution' ? (
            <ExecutionDashboard processId={processId} decisionTypes={decisionTypes} />
          ) : null}
        </div>
      </NestedCard>
    </section>
  )
}

function usePlane<P extends Plane>(processId: number, plane: P) {
  return useQuery({
    queryKey: keys.planeMetrics(processId, plane),
    queryFn: () => api.planeMetrics(processId, plane),
    refetchInterval: 10_000,
  })
}

function IngestionDashboard({ processId }: { processId: number }) {
  const metrics = usePlane(processId, 'ingestion')
  if (metrics.isError) return <ErrorNotice error={metrics.error} />
  const data: IngestionMetrics | undefined = metrics.data
  if (!data) return null
  const priced = data.providers.reduce((sum, item) => sum + item.known_cost_usd, 0)
  const unpriced = data.providers.reduce((sum, item) => sum + item.unpriced_requests, 0)

  return (
    <>
      <MetricCells
        cells={[
          { label: 'Documentos', value: number(data.files), note: `${number(data.pages)} páginas` },
          { label: 'OCR', value: number(data.ocr_calls), note: `${number(data.vision_calls)} visión` },
          { label: 'Caché', value: number(data.cache_hits), note: 'lecturas repetidas, 0 tokens' },
          { label: 'Sin adivinar', value: number(data.abstentions), note: 'campos que no se leyeron' },
          { label: 'Coste de lectura', value: cost(priced, unpriced), note: `${number(data.errors)} errores` },
        ]}
      />
      {data.providers.length ? (
        <DataTable
          rows={data.providers.map((item, index) => ({ ...item, id: `${item.provider}-${item.model}-${index}` }))}
          columns={[
            { key: 'model', header: 'Proveedor', render: (row) => mono(`${row.provider ?? '—'} · ${row.model ?? '—'}`) },
            { key: 'requests', header: 'Llamadas', render: (row) => mono(`${number(row.network_requests)} · ${number(row.replays)} caché`) },
            { key: 'tokens', header: 'Tokens', render: (row) => mono(`${number(row.input_tokens)} in · ${number(row.output_tokens)} out · ${number(row.cached_tokens)} caché`) },
            { key: 'errors', header: 'Errores', render: (row) => mono(number(row.errors)) },
            { key: 'cost', header: 'Coste', render: (row) => mono(cost(row.known_cost_usd, row.unpriced_requests)) },
            { key: 'latency', header: 'p50 / p95', render: (row) => muted(`${ms(row.network_p50_ms)} / ${ms(row.network_p95_ms)}`) },
          ]}
        />
      ) : (
        <Empty>Ningún proveedor todavía: el texto nativo no llama a ninguno.</Empty>
      )}
    </>
  )
}

function AgentsDashboard({ processId }: { processId: number }) {
  const metrics = usePlane(processId, 'agents')
  if (metrics.isError) return <ErrorNotice error={metrics.error} />
  const data: AgentsMetrics | undefined = metrics.data
  if (!data) return null
  const total = data.total
  const cacheRate = total.input_tokens ? Math.round((total.cached_tokens / total.input_tokens) * 100) : null
  const columns = (first: string) => [
    { key: 'key', header: first, render: (row: AgentRow) => row.link ? <Link to={row.link} className="underline">{mono(row.key ?? '—')}</Link> : mono(row.key ?? '—') },
    { key: 'calls', header: 'Llamadas', render: (row: AgentRow) => mono(`${number(row.calls)} · ${number(row.requests)} peticiones`) },
    { key: 'tokens', header: 'Tokens', render: (row: AgentRow) => mono(`${number(row.input_tokens)} in · ${number(row.output_tokens)} out · ${number(row.cached_tokens)} caché`) },
    { key: 'retries', header: 'Reintentos', render: (row: AgentRow) => mono(`${number(row.retries)} · ${number(row.fallbacks)} fallback`) },
    { key: 'errors', header: 'Errores', render: (row: AgentRow) => mono(number(row.errors)) },
    { key: 'cost', header: 'Coste', render: (row: AgentRow) => mono(cost(row.known_cost_usd, row.unpriced_requests)) },
  ]

  return (
    <>
      <MetricCells
        cells={[
          { label: 'Llamadas', value: number(total.calls), note: `${number(total.requests)} peticiones` },
          { label: 'Tokens', value: number(total.input_tokens + total.output_tokens), note: 'se gastan por versión de la norma' },
          { label: 'Caché', value: cacheRate == null ? '—' : `${cacheRate} %`, note: 'tokens de entrada en caché' },
          {
            label: 'Compila a la primera',
            value: data.compile.success_rate == null ? '—' : `${Math.round(data.compile.success_rate * 100)} %`,
            note: `${number(data.compile.valid)} de ${number(data.compile.compilations)} válidas`,
          },
          { label: 'Coste de las reglas', value: cost(total.known_cost_usd, total.unpriced_requests), note: `${number(total.errors)} errores` },
        ]}
      />
      {data.by_role.length ? (
        <DataTable rows={data.by_role.map((item, index) => ({ ...item, id: `role-${item.key}-${index}` }))} columns={columns('Papel')} />
      ) : (
        <Empty>Ningún agente ha trabajado en este proceso todavía.</Empty>
      )}
      {data.by_rule.length ? (
        <div className="mt-3">
          <DataTable
            rows={data.by_rule.map((item, index) => ({
              ...item,
              id: `rule-${item.key}-${index}`,
              link: item.key && /^\d+$/.test(item.key) ? paths.rule(processId, item.key) : undefined,
            }))}
            columns={columns('Regla')}
          />
        </div>
      ) : null}
    </>
  )
}

type AgentRow = AgentsMetrics['by_role'][number] & { id: string; link?: string }

function ExecutionDashboard({
  processId,
  decisionTypes,
}: {
  processId: number
  decisionTypes: DecisionType[] | undefined
}) {
  const metrics = usePlane(processId, 'execution')
  if (metrics.isError) return <ErrorNotice error={metrics.error} />
  const data: ExecutionMetrics | undefined = metrics.data
  if (!data) return null
  const outcomes = Object.entries(data.decisions_by_outcome)
  // traceability-gaps (fix/traceability-gaps): this table is the human queue by first reason.
  // If merging a newer version from Carlos, keep his UI and preserve: it reads escalation_reasons, not failures.
  const failures = Object.entries(data.escalation_reasons)

  return (
    <>
      <MetricCells
        cells={[
          { label: 'Ejecuciones', value: number(data.runs), note: `${number(data.instances_decided)} decididos` },
          {
            label: 'Por segundo',
            value: data.instances_per_second == null ? '—' : data.instances_per_second.toLocaleString('es-ES', { maximumFractionDigits: 1 }),
            note: `${number(data.pending)} pendientes`,
          },
          { label: 'Escalados', value: number(data.escalated), note: `${number(data.resolutions)} resueltos por una persona` },
          { label: 'Alertas', value: number(data.open_alerts), note: 'decisiones que podrían cambiar' },
          { label: 'Coste de decidir', value: '0 tokens · 0 €', note: 'el motor nunca llama a un LLM' },
        ]}
      />
      {outcomes.length ? (
        <DataTable
          rows={outcomes.map(([name, count]) => ({ id: name, name, count }))}
          columns={[
            { key: 'name', header: 'Decisión', render: (row) => <StatusBadge value={row.name} decisionTypes={decisionTypes} /> },
            { key: 'count', header: 'Casos', render: (row) => <Link to={paths.instances(processId)}>{mono(number(row.count))}</Link> },
          ]}
        />
      ) : (
        <Empty>Aún no se ha decidido ningún caso.</Empty>
      )}
      {failures.length ? (
        <div className="mt-3">
          <DataTable
            rows={failures.map(([reason, count]) => ({ id: reason, reason, count }))}
            columns={[
              { key: 'reason', header: 'Motivo de escalado', render: (row) => mono(row.reason) },
              { key: 'count', header: 'Casos', render: (row) => mono(number(row.count)) },
            ]}
          />
        </div>
      ) : null}
      {data.rules.length ? (
        <div className="mt-3">
          <DataTable
            rows={data.rules.map((item, index) => ({ ...item, id: `r-${item.rule_id}-${index}` }))}
            columns={[
              {
                key: 'rule',
                header: 'Regla',
                render: (row) =>
                  row.rule_id != null ? (
                    <Link to={paths.rule(processId, row.rule_id)} className="underline">{mono(`#${row.rule_id}`)}</Link>
                  ) : mono('—'),
              },
              { key: 'evaluations', header: 'Evaluaciones', render: (row) => mono(number(row.evaluations)) },
              { key: 'fired', header: 'Salta', render: (row) => mono(number(row.fired)) },
              { key: 'errors', header: 'Errores', render: (row) => mono(number(row.errors)) },
              { key: 'latency', header: 'p50 / p95', render: (row) => muted(`${ms(row.p50_ms)} / ${ms(row.p95_ms)}`) },
            ]}
          />
        </div>
      ) : null}
      {data.steps.length ? (
        <div className="mt-3">
          <DataTable
            rows={data.steps.map((item) => ({ ...item, id: item.step }))}
            columns={[
              { key: 'step', header: 'Paso', render: (row) => mono(row.step) },
              { key: 'count', header: 'Veces', render: (row) => mono(`${number(row.count)} · ${number(row.errors)} errores`) },
              { key: 'latency', header: 'p50 / p95', render: (row) => muted(`${ms(row.p50_ms)} / ${ms(row.p95_ms)}`) },
            ]}
          />
        </div>
      ) : null}
    </>
  )
}
