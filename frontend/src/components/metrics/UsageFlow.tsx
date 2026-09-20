import { useState } from 'react'
import { ArrowRight, X } from 'lucide-react'
import type { Plane, UsageBreakdown } from '../../api/contracts'
import { getLocale, t } from '../../i18n'
import { cn } from '../../lib/cn'
import { Button, SegmentedRail, SEGMENT_ITEM } from '../shell/Controls'
import { sumUsage, usageFlow, type FlowGrouping, type FlowNode } from './flow'
import { colors, formatted, label, moduleName, number, value, type Measure } from './usage'

function name(node: FlowNode): string {
  if (node.kind === 'total') return label('flowTotal')
  if (node.kind === 'area') return t(`planes.${node.plane}`)
  if (node.kind === 'remaining') return `${label('remaining')} · ${t(`planes.${node.plane}`)}`
  if (node.kind === 'tasks') return moduleName(node.module ?? '')
  return node.rows[0]?.model ?? node.rows[0]?.provider ?? label('local')
}

export function UsageFlow({
  data,
  measure,
  onDrill,
}: {
  data: UsageBreakdown
  measure: Measure
  onDrill: (plane: Plane, module?: string) => void
}) {
  const [grouping, setGrouping] = useState<FlowGrouping>('tasks')
  const [hovered, setHovered] = useState<string | null>(null)
  const [selected, setSelected] = useState<string | null>(null)
  const graph = usageFlow(data.flow, measure, grouping)
  const all = [graph.total, ...graph.areas, ...graph.leaves]
  const detail = graph.leaves.find((node) => node.key === selected)
  const active = all.find((node) => node.key === (hovered ?? selected))
  const related = (node: FlowNode) =>
    !active ||
    node === active ||
    node.kind === 'total' ||
    node.rows.some((row) => active.rows.includes(row))
  const percent = (node: FlowNode) => {
    if (measure === 'cost' && node.totals.unpriced_requests && !node.totals.known_cost_usd)
      return ''
    const total = value(graph.total.totals, measure)
    if (total <= 0) return ''
    return `${((value(node.totals, measure) / total) * 100).toLocaleString(getLocale(), { maximumFractionDigits: 1 })}%`
  }
  const annotation = (node: FlowNode) =>
    [formatted(node.totals, measure), percent(node)].filter(Boolean).join(' · ')
  function inspect(node: FlowNode) {
    if (node.kind === 'area') onDrill(node.plane!)
    if (node.kind === 'tasks') onDrill(node.plane!, node.module)
    if (node.kind === 'models' || node.kind === 'remaining')
      setSelected(selected === node.key ? null : node.key)
  }
  const modules = new Map<string, FlowNode>()
  for (const row of detail?.rows ?? []) {
    const key = JSON.stringify([row.plane, row.module])
    const rows = [...(modules.get(key)?.rows ?? []), row]
    modules.set(key, {
      ...detail!,
      key,
      kind: 'tasks',
      plane: row.plane,
      module: row.module ?? undefined,
      rows,
      totals: sumUsage(rows),
    })
  }

  return (
    <section
      aria-label={label('flow')}
      className="overflow-hidden rounded-2xl border border-line bg-surface"
    >
      <div className="flex flex-wrap items-start justify-between gap-4 px-5 pt-5 sm:px-6">
        <div>
          <h2 className="text-sm font-medium">{label('flow')}</h2>
          <p className="mt-1 text-xs text-muted">{label('flowScope')}</p>
        </div>
        <div role="group" aria-label={label('flowGrouping')}>
          <SegmentedRail value={grouping}>
            {(['tasks', 'models'] as const).map((item) => (
              <button
                key={item}
                data-active={grouping === item || undefined}
                aria-pressed={grouping === item}
                onClick={() => {
                  setGrouping(item)
                  setSelected(null)
                  setHovered(null)
                }}
                className={cn(
                  SEGMENT_ITEM,
                  grouping === item ? 'text-ink' : 'text-muted hover:text-ink',
                )}
              >
                {label(item)}
              </button>
            ))}
          </SegmentedRail>
        </div>
      </div>
      <div className="mt-5 flex flex-wrap items-end gap-x-5 gap-y-2 px-5 sm:px-6">
        <p
          className="text-[30px] font-medium tabular-nums leading-none tracking-tight"
          data-testid="flow-total"
        >
          {formatted(graph.total.totals, measure)}
        </p>
        <p className="text-xs text-muted">
          {label(measure === 'cost' ? 'apiSpend' : measure)}
        </p>
        {measure === 'cost' && graph.total.totals.unpriced_requests > 0 && (
          <span className="text-xs text-escalar">
            {number(graph.total.totals.unpriced_requests)} {label('unknown')}
          </span>
        )}
      </div>
      <div className="mx-5 mt-4 space-y-2 rounded-lg bg-canvas p-3 text-xs text-muted sm:mx-6">
        <p>{label('recordedSource')}</p>
        <p>
          {number(graph.total.totals.requests - graph.total.totals.unpriced_requests)} /{' '}
          {number(graph.total.totals.requests)} {label('pricedCoverage')}
        </p>
        {graph.total.totals.imported_spans > 0 && (
          <p>{number(graph.total.totals.imported_spans)} {label('importedHistory')}</p>
        )}
        <details>
          <summary className="cursor-pointer">{label('methodology')}</summary>
          <div className="mt-2 space-y-2">
            <p>{label('costNote')}</p>
            <p>{label('inputNote')}</p>
            <p>{label('timeNote')}</p>
            <p>{label('engineNote')}</p>
          </div>
        </details>
      </div>
      {measure === 'cost' &&
        graph.leaves.filter((node) => node.totals.known_cost_usd > 0).length === 1 && (
          <p className="mt-3 px-5 text-xs text-muted sm:px-6">{label('singleCostPath')}</p>
        )}
      {data.flow.length === 0 ? (
        <p className="px-6 py-20 text-center text-sm text-muted">{label('noActivity')}</p>
      ) : (
        <>
          <div
            className="mt-5 max-h-[560px] overflow-auto px-2 sm:px-4"
            tabIndex={0}
            aria-label={label('flowScroll')}
          >
            <svg
              viewBox={`0 0 1000 ${graph.height}`}
              className="block w-full min-w-[880px]"
              role="group"
              aria-label={`${label('flow')}: ${label(measure)}`}
            >
              {[label('flowTotal'), label('area'), label(grouping)].map((title, i) => (
                <text
                  key={title}
                  x={[20, 365, 715][i]}
                  y={16}
                  fill="var(--color-muted)"
                  fontSize="11"
                >
                  {title}
                </text>
              ))}
              {graph.links.map((link) => (
                <path
                  key={`${link.source.key}-${link.target.key}`}
                  d={link.path}
                  fill={colors[link.plane]}
                  opacity={
                    related(link.source) && related(link.target) ? (active ? 0.35 : 0.2) : 0.04
                  }
                  className="pointer-events-none transition-opacity duration-150 motion-reduce:transition-none"
                />
              ))}
              {all.map((node) => {
                const title = name(node)
                const color = node.plane ? colors[node.plane] : 'var(--color-ink)'
                const center = node.y + node.height / 2
                const actionable = node.kind !== 'total'
                return (
                  <g
                    key={node.key}
                    role={actionable ? 'button' : 'group'}
                    tabIndex={actionable ? 0 : undefined}
                    aria-label={`${title}: ${annotation(node)}`}
                    aria-pressed={
                      node.kind === 'models' || node.kind === 'remaining'
                        ? selected === node.key
                        : undefined
                    }
                    onMouseEnter={() => setHovered(node.key)}
                    onMouseLeave={() => setHovered(null)}
                    onFocus={() => setHovered(node.key)}
                    onBlur={() => setHovered(null)}
                    onClick={() => inspect(node)}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter' || event.key === ' ') {
                        event.preventDefault()
                        inspect(node)
                      }
                    }}
                    className={cn('rounded outline-offset-2', actionable && 'cursor-pointer')}
                    opacity={related(node) ? 1 : 0.35}
                  >
                    <title>{`${title}\n${annotation(node)}${node.kind === 'models' && node.rows[0]?.provider ? `\n${node.rows[0].provider}` : ''}`}</title>
                    <rect
                      x={node.x - 4}
                      y={Math.min(node.y, center - 24)}
                      width={275}
                      height={Math.max(node.height, 48)}
                      fill="transparent"
                    />
                    {node.height > 0 ? (
                      <rect
                        x={node.x}
                        y={node.y}
                        width={12}
                        height={node.height}
                        rx={2}
                        fill={color}
                      />
                    ) : (
                      <path d={`M ${node.x},${center} h 12`} stroke={color} strokeDasharray="3 3" />
                    )}
                    <text
                      x={node.x + 24}
                      y={center - 5}
                      fontSize="12"
                      fontWeight="500"
                      fill="var(--color-ink)"
                    >
                      {title.length > 31 ? `${title.slice(0, 29)}…` : title}
                    </text>
                    <text x={node.x + 24} y={center + 14} fontSize="11" fill="var(--color-muted)">
                      {annotation(node)}
                    </text>
                  </g>
                )
              })}
            </svg>
          </div>
          {detail && (
            <div
              className="mx-5 mb-5 rounded-xl bg-canvas p-4"
              role="region"
              aria-label={label('modelAllocation')}
            >
              <div className="mb-3 flex items-center justify-between gap-3">
                <div>
                  <h3 className="text-sm font-medium">{name(detail)}</h3>
                  <p className="mt-1 text-xs text-muted">
                    {[
                      detail.kind === 'models' ? detail.rows[0]?.provider : null,
                      label('modelAllocation'),
                    ]
                      .filter(Boolean)
                      .join(' · ')}
                  </p>
                </div>
                <Button tone="ghost" aria-label={label('close')} onClick={() => setSelected(null)}>
                  <X size={14} />
                </Button>
              </div>
              <div className="grid gap-2 sm:grid-cols-2">
                {[...modules.values()].map((node) => (
                  <button
                    key={node.key}
                    onClick={() => onDrill(node.plane!, node.module)}
                    className="flex items-center justify-between gap-4 rounded-lg bg-surface px-3 py-2 text-left text-xs hover:ring-1 hover:ring-line"
                  >
                    <span>
                      <span className="block text-muted">{t(`planes.${node.plane}`)}</span>
                      {name(node)}
                    </span>
                    <span className="flex items-center gap-2 tabular-nums">
                      {formatted(node.totals, measure)} <ArrowRight size={13} />
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </>
      )}
      <div className="flex flex-wrap justify-between gap-2 border-t border-line px-5 py-3 text-[11px] text-muted sm:px-6">
        <span>{label('flowHint')}</span>
        <span>
          {label(
            measure === 'cost'
              ? 'infraMissing'
              : measure === 'time'
                ? 'timeNote'
                : 'tokenNote',
          )}
        </span>
      </div>
    </section>
  )
}
