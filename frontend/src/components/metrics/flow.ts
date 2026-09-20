import type { Plane, UsageGroup, UsageTotals } from '../../api/contracts'
import { planes, value, type Measure } from './usage'

export type FlowGrouping = 'tasks' | 'models'
export type FlowNode = {
  key: string
  kind: 'total' | 'area' | 'remaining' | FlowGrouping
  rows: UsageGroup[]
  totals: UsageTotals
  plane?: Plane
  module?: string
  x: number
  y: number
  height: number
}
export type FlowLink = {
  source: FlowNode
  target: FlowNode
  plane: Plane
  amount: number
  path: string
}

// Quantiles are intentionally not added. Every other field is additive.
export function sumUsage(rows: UsageTotals[]): UsageTotals {
  return {
    ...Object.fromEntries(
      [
        'spans',
        'imported_spans',
        'errors',
        'requests',
        'replays',
        'input_tokens',
        'output_tokens',
        'cached_tokens',
        'known_cost_usd',
        'estimated_cost_usd',
        'estimated_requests',
        'unpriced_requests',
        'timed_spans',
        'self_ms',
      ].map((key) => [
        key,
        rows.reduce((total, row) => total + (row[key as keyof UsageTotals] ?? 0), 0),
      ]),
    ),
    p50_ms: null,
    p95_ms: null,
  } as UsageTotals
}

/** Three columns with one common scale: ribbon thickness always conserves usage.
 * Minimum label slots create whitespace, never inflate small or zero amounts. */
export function usageFlow(rows: UsageGroup[], measure: Measure, grouping: FlowGrouping) {
  function node(key: string, kind: FlowNode['kind'], items: UsageGroup[], x: number): FlowNode {
    return { key, kind, rows: items, totals: sumUsage(items), x, y: 0, height: 0 }
  }
  const total = node('total', 'total', rows, 20)
  const areas = planes.map((plane) => ({
    ...node(
      plane,
      'area',
      rows.filter((row) => row.plane === plane),
      365,
    ),
    plane,
  }))
  const grouped = new Map<string, UsageGroup[]>()
  for (const row of rows) {
    const key = JSON.stringify(
      grouping === 'tasks' ? [row.plane, row.module] : [row.provider, row.model],
    )
    grouped.set(key, [...(grouped.get(key) ?? []), row])
  }
  const ranked = [...grouped]
    .map(([key, items]) => ({
      ...node(key, grouping, items, 715),
      ...(grouping === 'tasks'
        ? { plane: items[0].plane, module: items[0].module ?? undefined }
        : {}),
    }))
    .filter(
      (n) => value(n.totals, measure) > 0 || (measure === 'cost' && n.totals.unpriced_requests > 0),
    )
    .sort(
      (a, b) => value(b.totals, measure) - value(a.totals, measure) || a.key.localeCompare(b.key),
    )
  // Select the largest branches, then lay them out by their source area. Ranking
  // every task globally by amount interleaves areas and creates avoidable crossings.
  // Keep each area's remaining usage separate for the same reason.
  const leaves: FlowNode[] =
    ranked.length > 7
      ? [
          ...ranked.slice(0, 6),
          ...planes.flatMap((plane) => {
            const remaining = ranked
              .slice(6)
              .flatMap((n) => n.rows)
              .filter((row) => row.plane === plane)
            return remaining.length
              ? [{ ...node(`remaining:${plane}`, 'remaining', remaining, 715), plane }]
              : []
          }),
        ]
      : ranked
  // Shared models stay merged. Place them between the areas that use them, so
  // each area's exclusive models sit together and shared connections travel less.
  function sourceOrder(n: FlowNode) {
    if (n.plane) return planes.indexOf(n.plane)
    const weights = n.rows.map((row) =>
      value(n.totals, measure) > 0 ? value(row, measure) : row.unpriced_requests || row.spans,
    )
    const weight = weights.reduce((sum, amount) => sum + amount, 0)
    return weight
      ? n.rows.reduce((sum, row, i) => sum + planes.indexOf(row.plane) * weights[i], 0) / weight
      : 0
  }
  leaves.sort(
    (a, b) =>
      sourceOrder(a) - sourceOrder(b) ||
      Number(a.kind === 'remaining') - Number(b.kind === 'remaining') ||
      value(b.totals, measure) - value(a.totals, measure) ||
      a.key.localeCompare(b.key),
  )
  const scale = value(total.totals, measure) > 0 ? 240 / value(total.totals, measure) : 0
  const columns = [[total], areas, leaves]
  for (const n of columns.flat()) n.height = value(n.totals, measure) * scale
  const columnHeight = (column: FlowNode[]) =>
    column.reduce((sum, n) => sum + Math.max(n.height, 40) + 14, 0)
  const height = Math.max(410, ...columns.map(columnHeight)) + 50
  for (const column of columns) {
    let y = 30 + (height - 30 - columnHeight(column)) / 2
    for (const n of column) {
      const slot = Math.max(n.height, 40)
      n.y = y + (slot - n.height) / 2
      y += slot + 14
    }
  }
  const links: FlowLink[] = []
  const out = new Map<string, number>(),
    incoming = new Map<string, number>()
  function link(source: FlowNode, target: FlowNode, plane: Plane, amount: number) {
    if (amount <= 0) return
    const width = amount * scale
    const y0 = source.y + (out.get(source.key) ?? 0)
    const y1 = target.y + (incoming.get(target.key) ?? 0)
    const x0 = source.x + 12,
      x1 = target.x,
      mid = (x0 + x1) / 2
    links.push({
      source,
      target,
      plane,
      amount,
      path: `M ${x0},${y0} C ${mid},${y0} ${mid},${y1} ${x1},${y1} L ${x1},${y1 + width} C ${mid},${y1 + width} ${mid},${y0 + width} ${x0},${y0 + width} Z`,
    })
    out.set(source.key, (out.get(source.key) ?? 0) + width)
    incoming.set(target.key, (incoming.get(target.key) ?? 0) + width)
  }
  for (const area of areas) link(total, area, area.plane, value(area.totals, measure))
  for (const area of areas) {
    for (const leaf of leaves) {
      const amount = leaf.rows
        .filter((row) => row.plane === area.plane)
        .reduce((sum, row) => sum + value(row, measure), 0)
      link(area, leaf, area.plane, amount)
    }
  }
  return { total, areas, leaves, links, height }
}
