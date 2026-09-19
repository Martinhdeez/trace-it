import { useState, type ReactNode } from 'react'
import { useParams } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import { ChevronDown } from 'lucide-react'
import { api } from '../api/client'
import type { AgentsMetrics, ExecutionMetrics, IngestionMetrics, Plane } from '../api/contracts'
import { keys } from '../api/queries'
import { MetricCells } from '../components/process/PlaneDashboards'
import { ProcessScreen } from '../components/process/ProcessScreen'
import { DataTable } from '../components/shell/DataTable'
import { Empty, ErrorNotice } from '../components/shell/Notice'
import { cn } from '../lib/cn'
import { formatEuro, formatMs, humanize } from '../lib/format'
import { paths } from '../lib/paths'

type Step = IngestionMetrics['steps'][number]
type Provider = IngestionMetrics['providers'][number]

/** The sketch's "parts": lectura, the agent roles, and the engine that spends nothing. */
type Group = 'lectura' | 'reglas' | 'asistente' | 'motor'

const GROUP_COLOR: Record<Group, string> = {
  lectura: 'var(--color-ocr)',
  reglas: 'var(--color-escalar)',
  asistente: 'var(--color-faint)',
  motor: 'var(--color-pagar)',
}
const GROUP_LABEL: Record<Group, string> = {
  lectura: 'Lectura',
  reglas: 'Reglas',
  asistente: 'Asistente',
  motor: 'Motor',
}

type Part = {
  id: string
  name: string
  note: string
  group: Group
  /** Reglas rows shade the same orange; index deepens it. */
  shade: number
  tokens: number
  knownCost: number
  unpriced: number
  p95: number | null
}

const ROLE_META: Record<string, { name: string; note: string; group: Group; steps?: string[] }> = {
  compiler: { name: 'Código de las reglas', note: 'el compilador escribe el Python', group: 'reglas', steps: ['coder_attempt'] },
  tester: { name: 'Tests de las reglas', note: 'el tester no ve el código', group: 'reglas', steps: ['run_tests'] },
  normalizer: { name: 'Normalizador', note: 'ordena la norma antes de compilar', group: 'reglas', steps: ['normalize_norm'] },
  assistant: { name: 'Consejos', note: 'el asistente, solo si lo pides', group: 'asistente', steps: ['suggest_escalation', 'propose_decision', 'suggest_rule'] },
  reviewer: { name: 'Revisor', note: 'una segunda lectura de la regla', group: 'reglas' },
  reviewer_agent: { name: 'Revisor', note: 'una segunda lectura de la regla', group: 'reglas' },
  decision_reviewer: { name: 'Revisión de decisiones', note: 'relee lo decidido', group: 'reglas', steps: ['review_decision'] },
  discovery: { name: 'Descubrimiento', note: 'redacta el proceso contigo', group: 'asistente', steps: ['discover_process', 'discuss_process', 'revise_process_draft'] },
  learner: { name: 'Aprendizaje', note: 'propone normas desde casos pasados', group: 'reglas', steps: ['learn_norms'] },
}

const number = (value: number | null | undefined) =>
  value == null ? '—' : value.toLocaleString('es-ES')
const ms = (value: number | null | undefined) => (value == null ? '—' : formatMs(value))
const compact = (value: number) => (value >= 1000 ? `${Math.round(value / 1000)}k` : String(value))
const spent = (row: { input_tokens: number; output_tokens: number }) => row.input_tokens + row.output_tokens

/** A known price, the count of unpriced calls, or nothing — never an invented $ 0. */
const cost = (known: number, unpriced: number) =>
  known > 0 ? `${formatEuro(known, 4)} USD` : unpriced > 0 ? 'sin precio' : '—'

const step = (steps: Step[] | undefined, name: string) => steps?.find((item) => item.step === name)
const p95of = (steps: Step[] | undefined, names: string[] = []) => {
  const values = names
    .map((name) => step(steps, name)?.p95_ms)
    .filter((value): value is number => value != null)
  return values.length ? Math.max(...values) : null
}

function usePlane<P extends Plane>(processId: number, plane: P) {
  return useQuery({
    queryKey: keys.planeMetrics(processId, plane),
    queryFn: () => api.planeMetrics(processId, plane),
    refetchInterval: 10_000,
  })
}

/**
 * The metrics page: where the money and the time go, part by part. Reading and writing
 * rules spend tokens once; deciding never does — the planes are shown side by side,
 * never mixed into one total (docs/observability-dashboards.md).
 */
export function Metrics() {
  const processId = Number(useParams().processId)
  const process = useQuery({
    queryKey: keys.process(processId),
    queryFn: () => api.getProcess(processId),
  })
  const ingestion = usePlane(processId, 'ingestion')
  const agents = usePlane(processId, 'agents')
  const execution = usePlane(processId, 'execution')
  const error = ingestion.error ?? agents.error ?? execution.error ?? process.error

  const parts = buildParts(ingestion.data, agents.data, execution.data)
  const llmTokens = parts.reduce((sum, part) => sum + part.tokens, 0)
  const readTokens = parts.find((part) => part.id === 'lectura')?.tokens ?? 0
  const knownCost =
    (ingestion.data?.providers ?? []).reduce((sum, item) => sum + item.known_cost_usd, 0) +
    (agents.data?.total.known_cost_usd ?? 0)
  const decided = execution.data?.instances_decided ?? 0
  const decision = step(execution.data?.steps, 'decision')

  return (
    <ProcessScreen
      processId={processId}
      crumbs={[
        { label: 'Procesos', to: paths.processes },
        { label: process.data?.name ?? '…', to: paths.process(processId) },
        { label: 'Métricas' },
      ]}
    >
      <div className="min-h-0 flex-1 overflow-y-auto px-6 pb-10 pt-4">
        <div className="max-w-5xl">
          <header className="mb-4">
            <h1 className="text-[20px] font-medium tracking-[-0.03em]">Métricas</h1>
            <p className="mt-1 text-[12.5px] text-muted">
              Dónde se va el dinero y el tiempo, parte a parte. Leer y escribir reglas no se mezclan con decidir.
            </p>
          </header>

          {error ? <div className="mb-4"><ErrorNotice error={error} /></div> : null}

          <MetricCells
            cells={[
              {
                label: 'Coste conocido',
                value: knownCost > 0 ? `${formatEuro(knownCost, 2)} USD` : '—',
                note: 'solo lo que tiene tarifa',
              },
              {
                label: 'Tokens',
                value: ingestion.data || agents.data ? number(llmTokens) : '—',
                note: '0 al decidir · el motor no llama a un modelo',
              },
              {
                label: 'Decidir un caso',
                value: ms(decision?.p50_ms),
                note:
                  decided > 0
                    ? `p50 · ${number(decided)} casos${execution.data?.instances_per_second ? ` · ${execution.data.instances_per_second.toLocaleString('es-ES', { maximumFractionDigits: 1 })} /s` : ''}`
                    : 'todavía sin casos',
              },
            ]}
          />

          <div className="grid items-start gap-10 lg:grid-cols-[1.15fr_0.85fr]">
            <section>
              <h2 className="text-[15px] font-medium tracking-[-0.02em]">Gasto por parte</h2>
              <p className="mt-0.5 text-[12.5px] text-muted">Tokens. Leer y escribir reglas no se mezclan con decidir.</p>
              <div className="mt-3 rounded-[16px] bg-well p-4 ring-1 ring-line">
                <TokenChart parts={parts} />
                <div className="mt-1 flex justify-between text-[11px] text-muted">
                  {parts.map((part) => (
                    <span key={part.id} className="min-w-0 flex-1 px-1 text-center">
                      <b className="block truncate font-medium text-ink">{part.name.split(' ')[0]}</b>
                      {GROUP_LABEL[part.group].toLowerCase()}
                    </span>
                  ))}
                </div>
              </div>
            </section>

            <section>
              <h2 className="text-[15px] font-medium tracking-[-0.02em]">Qué ha gastado cada uno</h2>
              <ul>
                {parts.map((part) => (
                  <li key={part.id} className="flex items-center gap-3 border-b border-hairline py-3 last:border-0">
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-[13.5px] font-medium tracking-[-0.01em]">{part.name}</p>
                      <p className="mt-0.5 truncate text-[12px] text-muted">{part.note}</p>
                    </div>
                    <span className="shrink-0 font-mono text-[13px] tabular-nums">{number(part.tokens)}</span>
                    <span className="flex w-[86px] shrink-0 items-center justify-end gap-1.5 text-[11px] text-muted">
                      <i
                        className="inline-block h-2 w-2 rounded-full"
                        style={{ background: GROUP_COLOR[part.group], opacity: part.shade }}
                      />
                      {GROUP_LABEL[part.group]}
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          </div>

          {llmTokens > 0 ? (
            <p className="mb-5 mt-2 max-w-3xl text-[12px] text-muted">
              {number(llmTokens)} tokens: {number(readTokens)} en lectura (
              {Math.round((readTokens / llmTokens) * 100)} %) y {number(llmTokens - readTokens)} en las
              reglas ({Math.round(((llmTokens - readTokens) / llmTokens) * 100)} %). Decidir{' '}
              {number(decided)} casos: 0 tokens. Lo que no tiene tarifa se muestra «sin precio», nunca
              un $ 0 inventado.
            </p>
          ) : (
            <div className="mb-5 mt-2" />
          )}

          <PartsTable parts={parts} />

          <CostGate ingestion={ingestion.data} agents={agents.data} execution={execution.data} />
          <TimeGate ingestion={ingestion.data} agents={agents.data} execution={execution.data} />
        </div>
      </div>
    </ProcessScreen>
  )
}

function buildParts(
  ingestion: IngestionMetrics | undefined,
  agents: AgentsMetrics | undefined,
  execution: ExecutionMetrics | undefined,
): Part[] {
  const providers = ingestion?.providers ?? []
  const parts: Part[] = [
    {
      id: 'lectura',
      name: 'OCR y visión',
      note: ingestion
        ? `${number(ingestion.files)} documentos · ${number(ingestion.ocr_calls + ingestion.vision_calls)} lecturas`
        : 'leer los documentos, una vez',
      group: 'lectura',
      shade: 1,
      tokens: providers.reduce((sum, item) => sum + spent(item), 0),
      knownCost: providers.reduce((sum, item) => sum + item.known_cost_usd, 0),
      unpriced: providers.reduce((sum, item) => sum + item.unpriced_requests, 0),
      p95: providers.reduce<number | null>(
        (max, item) => (item.network_p95_ms != null && (max == null || item.network_p95_ms > max) ? item.network_p95_ms : max),
        null,
      ),
    },
  ]

  const shades = [1, 0.75, 0.55, 0.45]
  const roles = [...(agents?.by_role ?? [])].sort((a, b) => spent(b) - spent(a))
  roles.forEach((role, index) => {
    const meta = ROLE_META[role.key ?? ''] ?? {
      name: humanize(role.key ?? 'agente'),
      note: 'agente del proceso',
      group: 'reglas' as Group,
    }
    parts.push({
      id: `role-${role.key ?? index}`,
      name: meta.name,
      note: meta.note,
      group: meta.group,
      shade: meta.group === 'reglas' ? shades[Math.min(index, shades.length - 1)] : 1,
      tokens: spent(role),
      knownCost: role.known_cost_usd,
      unpriced: role.unpriced_requests,
      p95: p95of(agents?.steps, meta.steps),
    })
  })

  parts.push({
    id: 'decidir',
    name: 'Decidir',
    note: execution
      ? `${number(execution.instances_decided)} casos · el motor nunca llama a un modelo`
      : 'el motor nunca llama a un modelo',
    group: 'motor',
    shade: 1,
    tokens: 0,
    knownCost: 0,
    unpriced: 0,
    p95: step(execution?.steps, 'decision')?.p95_ms ?? null,
  })
  return parts
}

/** Vertical bars, one per part: height is its tokens, the engine is a line at zero. */
function TokenChart({ parts }: { parts: Part[] }) {
  const TOP = 18
  const BASE = 168
  const LEFT = 48
  const RIGHT = 620
  const max = Math.max(1, ...parts.map((part) => part.tokens))
  const span = (RIGHT - LEFT) / Math.max(1, parts.length)
  const barW = Math.min(70, span * 0.58)
  const grid = [TOP, TOP + (BASE - TOP) / 4, TOP + (BASE - TOP) / 2, TOP + ((BASE - TOP) * 3) / 4, BASE]

  return (
    <svg viewBox="0 0 640 200" className="block h-[190px] w-full" aria-hidden="true">
      {grid.map((y) => (
        <line key={y} x1={LEFT} y1={y} x2={RIGHT} y2={y} stroke="var(--color-hairline)" />
      ))}
      <text x={8} y={TOP + 4} fontSize={11} fill="var(--color-muted)">
        {compact(max)}
      </text>
      <text x={8} y={(TOP + BASE) / 2 + 4} fontSize={11} fill="var(--color-muted)">
        {compact(Math.round(max / 2))}
      </text>
      <text x={14} y={BASE + 4} fontSize={11} fill="var(--color-muted)">
        0
      </text>
      {parts.map((part, index) => {
        const height = part.tokens > 0 ? Math.max(2, (part.tokens / max) * (BASE - TOP)) : 2
        const x = LEFT + span * index + (span - barW) / 2
        const color = GROUP_COLOR[part.group]
        return (
          <g key={part.id}>
            <rect
              x={x}
              y={BASE - height}
              width={barW}
              height={height}
              rx={part.tokens > 0 ? 4 : 1}
              fill={color}
              opacity={part.shade}
            />
            <text
              x={x + barW / 2}
              y={BASE - height - 6}
              textAnchor="middle"
              fontSize={12}
              fontWeight={600}
              fill={part.tokens > 0 ? 'var(--color-ink)' : 'var(--color-pagar)'}
            >
              {compact(part.tokens)}
            </text>
          </g>
        )
      })}
    </svg>
  )
}

/** One row per part: share of the tokens, what it cost if it has a price, and its p95. */
function PartsTable({ parts }: { parts: Part[] }) {
  const max = Math.max(1, ...parts.map((part) => part.tokens))
  return (
    <DataTable
      rows={parts}
      columns={[
        {
          key: 'part',
          header: 'parte',
          width: '34%',
          render: (part) => (
            <span>
              <span className="text-[13px] font-medium">{part.name}</span>{' '}
              <span className="text-[12px] text-muted">{part.note}</span>
            </span>
          ),
        },
        {
          key: 'share',
          header: 'reparto',
          width: '22%',
          render: (part) => (
            <span className="flex h-2 max-w-[160px] overflow-hidden rounded-full bg-well">
              <span
                className="block h-full"
                style={{ width: `${Math.max(1, (part.tokens / max) * 100)}%`, background: GROUP_COLOR[part.group], opacity: part.shade }}
              />
            </span>
          ),
        },
        {
          key: 'tokens',
          header: 'tokens',
          render: (part) => <span className="font-mono text-[12px] tabular-nums">{number(part.tokens)}</span>,
        },
        {
          key: 'cost',
          header: 'coste',
          render: (part) =>
            part.group === 'motor' ? (
              <span className="font-mono text-[12px] tabular-nums text-pagar">0 USD</span>
            ) : (
              <span className="font-mono text-[12px] tabular-nums">{cost(part.knownCost, part.unpriced)}</span>
            ),
        },
        {
          key: 'p95',
          header: 'p95',
          render: (part) => <span className="font-mono text-[12px] tabular-nums">{ms(part.p95)}</span>,
        },
      ]}
    />
  )
}

/** A row that opens: the detail stays behind one click, like the sketch's gates. */
function Gate({
  title,
  desc,
  children,
}: {
  title: string
  desc: string
  children: ReactNode
}) {
  const [open, setOpen] = useState(false)
  return (
    <div className="mt-3 overflow-hidden rounded-[16px] bg-surface ring-1 ring-line">
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
        className="flex w-full items-center justify-between gap-3 px-4 py-3.5 text-left"
      >
        <span className="min-w-0">
          <span className="text-[13.5px] font-medium">{title}</span>
          <span className="ml-2 text-[12.5px] text-muted">{desc}</span>
        </span>
        <ChevronDown size={16} strokeWidth={1.6} className={cn('shrink-0 text-faint transition-transform', open && 'rotate-180')} />
      </button>
      {open ? <div className="border-t border-hairline p-3">{children}</div> : null}
    </div>
  )
}

/** Who charged what: every reading provider and every agent model, and the engine at zero. */
function CostGate({
  ingestion,
  agents,
  execution,
}: {
  ingestion: IngestionMetrics | undefined
  agents: AgentsMetrics | undefined
  execution: ExecutionMetrics | undefined
}) {
  const rows = [
    ...(ingestion?.providers ?? []).map((item: Provider, index) => ({
      id: `p-${index}`,
      parte: `${item.provider ?? '—'} · ${item.model ?? '—'}`,
      detalle: `${item.operation ?? 'lectura'} · ${number(item.network_requests)} llamadas · ${number(spent(item))} tokens`,
      coste: cost(item.known_cost_usd, item.unpriced_requests),
    })),
    ...(agents?.by_model ?? []).map((item, index) => ({
      id: `m-${index}`,
      parte: String(item.key ?? '—'),
      detalle: `${number(item.calls)} llamadas · ${number(spent(item))} tokens`,
      coste: cost(item.known_cost_usd, item.unpriced_requests),
    })),
    {
      id: 'motor',
      parte: 'Motor',
      detalle: `${number(execution?.instances_decided)} decisiones`,
      coste: '0 USD',
    },
  ]
  return (
    <Gate title="Coste por parte" desc="quién cobró qué — y el motor en cero">
      {rows.length > 1 ? (
        <DataTable
          framed={false}
          rows={rows}
          columns={[
            { key: 'parte', header: 'parte', render: (row) => <span className="text-[13px] font-medium">{row.parte}</span> },
            { key: 'detalle', header: 'trabajo', render: (row) => <span className="text-[12px] text-muted">{row.detalle}</span> },
            { key: 'coste', header: 'coste', render: (row) => <span className="font-mono text-[12px] tabular-nums">{row.coste}</span> },
          ]}
        />
      ) : (
        <Empty>Todavía no hay llamadas con coste.</Empty>
      )}
    </Gate>
  )
}

const CLOCKS: { group: string; names: [string, string][] }[] = [
  {
    group: 'Lectura',
    names: [
      ['native_text', 'Texto nativo'],
      ['ocr', 'OCR'],
      ['vision', 'Visión'],
      ['ingest_document', 'Leer un documento'],
    ],
  },
  {
    group: 'Reglas',
    names: [
      ['normalize_norm', 'Normalizar la norma'],
      ['coder_attempt', 'Escribir el código'],
      ['run_tests', 'Tests de la regla'],
      ['compile_rule', 'Compilar una regla'],
      ['suggest_escalation', 'Consejos del asistente'],
    ],
  },
  {
    group: 'Motor',
    names: [
      ['evaluate_rule', 'Evaluar una regla'],
      ['decision', 'Decidir un caso'],
      ['run_process', 'El lote completo'],
    ],
  },
]

/** Three clocks that never add up: read, write the rules, decide — p50 and p95 each. */
function TimeGate({
  ingestion,
  agents,
  execution,
}: {
  ingestion: IngestionMetrics | undefined
  agents: AgentsMetrics | undefined
  execution: ExecutionMetrics | undefined
}) {
  const steps: Record<string, Step[] | undefined> = {
    Lectura: ingestion?.steps,
    Reglas: agents?.steps,
    Motor: execution?.steps,
  }
  const rows = CLOCKS.flatMap(({ group, names }) =>
    names
      .map(([key, label]) => ({ group, key, label, stats: step(steps[group], key) }))
      .filter((row): row is typeof row & { stats: Step } => row.stats != null)
      .map((row) => ({
        id: row.key,
        nucleo: row.label,
        grupo: row.group,
        veces: row.stats.count,
        p50: row.stats.p50_ms,
        p95: row.stats.p95_ms,
      })),
  )
  return (
    <Gate title="Tiempo por núcleo" desc="tres relojes que no se suman: leer, escribir reglas, decidir">
      {rows.length ? (
        <DataTable
          framed={false}
          rows={rows}
          columns={[
            {
              key: 'nucleo',
              header: 'núcleo',
              render: (row) => (
                <span>
                  <span className="text-[13px] font-medium">{row.nucleo}</span>{' '}
                  <span className="text-[12px] text-muted">{row.grupo.toLowerCase()}</span>
                </span>
              ),
            },
            { key: 'veces', header: 'veces', render: (row) => <span className="font-mono text-[12px] tabular-nums">{number(row.veces)}</span> },
            { key: 'p50', header: 'p50', render: (row) => <span className="font-mono text-[12px] tabular-nums">{ms(row.p50)}</span> },
            { key: 'p95', header: 'p95', render: (row) => <span className="font-mono text-[12px] tabular-nums">{ms(row.p95)}</span> },
          ]}
        />
      ) : (
        <Empty>Sin medidas todavía: ni lecturas, ni compilaciones, ni decisiones.</Empty>
      )}
    </Gate>
  )
}
