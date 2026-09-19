import type {
  Plane,
  SpanNode,
  UsageActivity,
  UsageBreakdown,
  UsageFilters,
  UsageGroup,
  UsageTotals,
} from '../../api/contracts'
import { sumUsage } from './flow'
import { planes } from './usage'

// Set false to open Metrics with the live API. The on-screen toggle overrides this in the URL.
export const HARDCODED_METRICS = true

// Illustrative monthly budgets, not provider tariffs or measured infrastructure charges.
// Execution has infrastructure cost, but never model tokens.
const paths: [Plane, string, string, string, number, number, number, number][] = [
  [
    'ingestion',
    'provider:image_transcription',
    'Helmcode',
    'Qwen 3.6',
    200,
    8_400_000,
    640_000,
    2_400_000,
  ],
  [
    'ingestion',
    'provider:image_transcription',
    'Google',
    'Gemini 3.1 Flash Lite',
    120,
    4_800_000,
    420_000,
    1_600_000,
  ],
  ['ingestion', 'provider:text_selection', 'Jev', 'Jev 1.13', 160, 6_200_000, 520_000, 1_900_000],
  [
    'agents',
    'agent:compiler',
    'Helmcode',
    'DeepSeek V4 Flash',
    240,
    9_200_000,
    1_800_000,
    3_600_000,
  ],
  ['agents', 'agent:compiler', 'Helmcode', 'Qwen 3.6', 80, 2_800_000, 540_000, 1_200_000],
  ['agents', 'agent:tester', 'Helmcode', 'DeepSeek V4 Flash', 120, 5_100_000, 920_000, 2_200_000],
  ['agents', 'agent:tester', 'Helmcode', 'Qwen 3.6', 40, 1_800_000, 280_000, 760_000],
  ['execution', 'evaluate_rule', 'Cloud compute', 'CPU workers', 180, 0, 0, 4_800_000],
  ['execution', 'export_outcomes', 'Cloud storage', 'Object storage', 100, 0, 0, 1_400_000],
]
const dayMs = 86_400_000
const zero = sumUsage([])
type Sample = UsageActivity & { plane: Plane; module: string }

function totals(rows: UsageTotals[]): UsageTotals {
  const durations = rows
    .map((row) => row.p50_ms)
    .filter((n): n is number => n !== null)
    .sort((a, b) => a - b)
  return {
    ...sumUsage(rows),
    p50_ms: durations.length ? durations[Math.floor((durations.length - 1) * 0.5)] : null,
    p95_ms: durations.length ? durations[Math.floor((durations.length - 1) * 0.95)] : null,
  }
}
function partition(rows: Sample[], key: (row: Sample) => string) {
  const result = new Map<string, Sample[]>()
  for (const row of rows) {
    const k = key(row)
    const items = result.get(k) ?? []
    items.push(row)
    result.set(k, items)
  }
  return [...result]
}

/** Deterministic samples: every view and drill-down uses the same dated operations.
 * No API calls, database writes or real trace IDs are used in this mode. */
export function demoBreakdown(processId: number, filters: UsageFilters): UsageBreakdown {
  const until = filters.until ?? new Date().toISOString()
  const end = Date.parse(until)
  const start = filters.since ? Date.parse(filters.since) : end - 90 * dayMs
  const samples: Sample[] = []
  for (let day = Math.floor(start / dayMs); day * dayMs < end; day++) {
    for (let slot = 0; slot < 4; slot++) {
      paths.forEach(([plane, module, provider, model, cost, input, output, time], index) => {
        const timestamp = day * dayMs + slot * 6 * 3_600_000 + (index + 1) * 180_000
        if (timestamp < start || timestamp >= end) return
        const id = day * 100 + slot * paths.length + index
        if (filters.through_id !== undefined && id > filters.through_id) return
        // Fixed daily/weekly variation makes the evolution meaningful and repeatable.
        const weight = (0.7 + (day % 30) / 50 + ((day + index) % 7) / 12) / 120
        const duration = Math.round(time * weight)
        samples.push({
          ...zero,
          id,
          span_id: `demo-span-${id}`,
          trace_id: `demo-trace-${id}`,
          plane,
          module,
          provider,
          model,
          step: module.startsWith('agent:')
            ? 'llm_run'
            : module.startsWith('provider:')
              ? 'provider_call'
              : module,
          status: 'ok',
          started_at: new Date(timestamp).toISOString(),
          duration_ms: duration,
          cost_status: 'known',
          rule_id: null,
          instance_id: null,
          spans: 1,
          requests: plane === 'execution' ? 0 : 1,
          known_cost_usd: Number((cost * weight).toFixed(6)),
          input_tokens: Math.round(input * weight),
          output_tokens: Math.round(output * weight),
          cached_tokens: Math.round(input * weight * 0.3),
          timed_spans: 1,
          self_ms: duration,
          p50_ms: duration,
          p95_ms: duration,
        })
      })
    }
  }
  const through_id = filters.through_id ?? Math.max(0, ...samples.map((row) => row.id))
  const rows = samples
    .filter(
      (row) =>
        (!filters.plane || row.plane === filters.plane) &&
        (!filters.module || row.module === filters.module),
    )
    .sort((a, b) => b.id - a.id)
  const flow: UsageGroup[] = partition(rows, (row) =>
    JSON.stringify([row.plane, row.module, row.provider, row.model]),
  ).map(([key, items]) => ({
    ...totals(items),
    key,
    plane: items[0].plane,
    module: items[0].module,
    provider: items[0].provider,
    model: items[0].model,
  }))
  const groups: UsageGroup[] = !filters.plane
    ? planes.map((plane) => ({
        ...totals(rows.filter((row) => row.plane === plane)),
        key: plane,
        plane,
        module: null,
        provider: null,
        model: null,
      }))
    : partition(rows, (row) =>
        filters.module ? JSON.stringify([row.provider, row.model]) : row.module,
      ).map(([key, items]) => ({
        ...totals(items),
        key,
        plane: items[0].plane,
        module: items[0].module,
        provider: filters.module ? items[0].provider : null,
        model: filters.module ? items[0].model : null,
      }))
  const bucket_seconds =
    end - start <= dayMs ? 3600 : 86400 * Math.max(1, Math.ceil((end - start) / dayMs / 90))
  const bucket = (row: Sample) =>
    Math.floor(Date.parse(row.started_at) / (bucket_seconds * 1000)) * bucket_seconds * 1000
  const series = partition(rows, (row) => `${row.plane}:${bucket(row)}`)
    .map(([, items]) => ({
      ...totals(items),
      started_at: new Date(bucket(items[0])).toISOString(),
      plane: items[0].plane,
    }))
    .sort((a, b) => a.started_at.localeCompare(b.started_at))
  const offset = filters.offset ?? 0
  return {
    process_id: processId,
    through_id,
    plane: filters.plane ?? null,
    module: filters.module ?? null,
    since: filters.since ?? new Date(start).toISOString(),
    until,
    bucket_seconds,
    totals: filters.plane ? totals(rows) : null,
    groups,
    flow,
    series,
    activity: filters.module ? rows.slice(offset, offset + 25) : [],
    activity_total: filters.module ? rows.length : 0,
    offset,
    limit: 25,
  }
}

export function demoTrace(item: UsageActivity): SpanNode[] {
  return [
    {
      id: item.id,
      span_id: item.span_id,
      trace_id: item.trace_id,
      parent_id: null,
      step: item.step,
      status: item.status,
      started_at: item.started_at,
      duration_ms: item.duration_ms,
      instance_id: null,
      process_id: null,
      rule_id: null,
      norm_rule_id: null,
      children: [],
      data: {
        example: true,
        model: item.model,
        provider: item.provider,
        input_tokens: item.input_tokens,
        output_tokens: item.output_tokens,
        cost_usd: item.known_cost_usd,
      },
    },
  ]
}
