import { useState, type ReactNode } from 'react'
import { useParams, useSearchParams } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import { ChevronRight, RefreshCw, X, Clock3, Coins, DollarSign } from 'lucide-react'
import { api } from '../api/client'
import type { Plane, UsageGroup, UsageTotals, UsageBreakdown } from '../api/contracts'
import { keys } from '../api/queries'
import { UsageFlow } from '../components/metrics/UsageFlow'
import { UsageActivity } from '../components/metrics/UsageActivity'
import { UsageTimeline } from '../components/metrics/UsageTimeline'
import {
  colors,
  dateTime,
  duration,
  formatted,
  groupName,
  label,
  measures,
  moduleName,
  number,
  planes,
  value,
  type Measure,
} from '../components/metrics/usage'
import { ProcessScreen } from '../components/process/ProcessScreen'
import { Button, SegmentedRail, SEGMENT_ITEM } from '../components/shell/Controls'
import { Empty, ErrorNotice } from '../components/shell/Notice'
import { getLocale, t } from '../i18n'
import { cn } from '../lib/cn'
import { paths } from '../lib/paths'

const windows: Record<string, number> = { day: 86400000, week: 7 * 86400000, month: 30 * 86400000 }

export function Metrics() {
  const processId = Number(useParams().processId)
  // The URL preserves drill-down on reload and supports browser back/forward.
  const [params, setParams] = useSearchParams()
  const planeParam = params.get('plane')
  const plane = planes.includes(planeParam as Plane) ? (planeParam as Plane) : undefined
  const module = plane ? (params.get('module') ?? undefined) : undefined
  const measureParam = params.get('measure')
  const measure: Measure = measures.includes(measureParam as Measure)
    ? (measureParam as Measure)
    : 'cost'
  const requestedPeriod = params.get('period') ?? 'all'
  const period =
    Object.hasOwn(windows, requestedPeriod) || requestedPeriod === 'all'
      ? requestedPeriod
      : 'thisMonth'
  const [snapshot, setSnapshot] = useState(() => new Date().toISOString())
  const validDate = (key: string) => {
    const raw = params.get(key)
    return raw && Number.isFinite(Date.parse(raw)) ? new Date(raw).toISOString() : undefined
  }
  const until = validDate('until') ?? snapshot
  const monthStart = new Date(until)
  monthStart.setDate(1)
  monthStart.setHours(0, 0, 0, 0)
  const requestedSince = validDate('since')
  const since =
    requestedSince && requestedSince < until
      ? requestedSince
      : period === 'thisMonth'
        ? monthStart.toISOString()
        : windows[period]
          ? new Date(Date.parse(until) - windows[period]).toISOString()
          : undefined
  const requestedOffset = Number(params.get('offset'))
  const offset = Number.isSafeInteger(requestedOffset) ? Math.max(0, requestedOffset) : 0
  const through = params.has('through_id') ? Number(params.get('through_id')) : undefined
  const through_id =
    through !== undefined && Number.isSafeInteger(through) && through >= 0 ? through : undefined
  const filters = { plane, module, since, until, offset, through_id }
  const usage = useQuery({
    queryKey: ['usage-breakdown', processId, filters],
    queryFn: () => api.usageBreakdown(processId, filters),
  })
  const process = useQuery({
    queryKey: keys.process(processId),
    queryFn: () => api.getProcess(processId),
  })
  const data = usage.data
  const level = !plane ? 'plane' : !module ? 'module' : 'model'
  const groups = [...(data?.groups ?? [])].sort(
    (a, b) => value(b, measure) - value(a, measure) || a.key.localeCompare(b.key),
  )
  const title = module ? moduleName(module) : plane ? t(`planes.${plane}`) : label('overview')
  function navigate(changes: Record<string, string | undefined>, replace = false) {
    const next = new URLSearchParams(params)
    next.delete('offset')
    if (!Object.hasOwn(changes, 'through_id') && data)
      next.set('through_id', String(data.through_id))
    for (const [key, val] of Object.entries(changes)) {
      if (val === undefined) next.delete(key)
      else next.set(key, val)
    }
    // Freeze the snapshot so navigating backwards and pagination retain the same sample.
    if (!next.has('until')) next.set('until', until)
    setParams(next, { replace })
  }
  function drill(row: UsageGroup) {
    navigate(!plane ? { plane: row.plane, module: undefined } : { module: row.module ?? row.key })
  }
  function refresh() {
    const now = new Date().toISOString()
    setSnapshot(now)
    navigate({ until: now, since: undefined, through_id: undefined }, true)
  }

  return (
    <ProcessScreen
      processId={processId}
      crumbs={[
        { label: t('nav.processes'), to: paths.processes },
        { label: process.data?.name ?? '…', to: paths.process(processId) },
        { label: label('title') },
      ]}
    >
      <div className="min-h-0 flex-1 overflow-y-auto px-4 pb-12 pt-5 sm:px-6">
        <div className="max-w-6xl">
          <header className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <h1 className="text-xl font-medium tracking-tight">{label('title')}</h1>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <select
                aria-label={label('period')}
                value={period}
                onChange={(e) => {
                  const now = new Date().toISOString()
                  setSnapshot(now)
                  navigate({
                    period: e.target.value,
                    since: undefined,
                    until: now,
                    through_id: undefined,
                  })
                }}
                className="rounded-lg bg-canvas px-3 py-2 text-xs ring-1 ring-line"
              >
                {['thisMonth', 'day', 'week', 'month', 'all'].map((key) => (
                  <option key={key} value={key}>
                    {label(key)}
                  </option>
                ))}
              </select>
              <Button aria-label={label('refresh')} onClick={refresh} disabled={usage.isFetching}>
                <RefreshCw
                  size={14}
                  className={usage.isFetching ? 'animate-spin motion-reduce:animate-none' : ''}
                />
              </Button>
            </div>
          </header>
          <nav
            aria-label={label('overview')}
            className="mb-5 mt-6 flex flex-wrap items-center gap-2 text-[13px]"
          >
            <button
              onClick={() => navigate({ plane: undefined, module: undefined })}
              aria-current={!plane ? 'page' : undefined}
              className={cn('rounded py-1 hover:underline', plane ? 'text-muted' : 'font-medium')}
            >
              {label('overview')}
            </button>
            {plane && (
              <>
                <ChevronRight size={13} className="text-faint" />
                <button
                  onClick={() => navigate({ module: undefined })}
                  aria-current={!module ? 'page' : undefined}
                  className={cn(
                    'rounded py-1 hover:underline',
                    module ? 'text-muted' : 'font-medium',
                  )}
                >
                  {t(`planes.${plane}`)}
                </button>
              </>
            )}
            {module && (
              <>
                <ChevronRight size={13} className="text-faint" />
                <span aria-current="page" className="font-medium">
                  {moduleName(module)}
                </span>
              </>
            )}
          </nav>
          {requestedSince === since && since && (
            <div className="mb-4 flex flex-wrap items-center gap-2 text-xs">
              <span>
                {label('selectedPeriod')}: {dateTime(since!)} – {dateTime(until)}
              </span>
              <Button
                aria-label={label('clearPeriod')}
                onClick={() => navigate({ since: undefined, until: snapshot })}
              >
                <X size={12} />
                {label('clearPeriod')}
              </Button>
            </div>
          )}
          {process.isError && <ErrorNotice error={process.error} />}
          {usage.isError ? (
            <ErrorNotice
              error={usage.error}
              action={<Button onClick={() => void usage.refetch()}>{t('common.retry')}</Button>}
            />
          ) : usage.isPending ? (
            <p role="status" className="py-10 text-sm text-muted">
              {t('common.loading')}
            </p>
          ) : (
            data && (
              <>
                <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
                  {plane ? <h2 className="text-base font-medium">{title}</h2> : <span />}
                  <div role="group" aria-label={label('distribution')}>
                    <SegmentedRail value={measure}>
                      {measures.map((m) => (
                        <button
                          key={m}
                          data-active={measure === m || undefined}
                          aria-pressed={measure === m}
                          onClick={() => navigate({ measure: m }, true)}
                          className={cn(
                            SEGMENT_ITEM,
                            measure === m ? 'text-ink' : 'text-muted hover:text-ink',
                          )}
                        >
                          {label(m)}
                        </button>
                      ))}
                    </SegmentedRail>
                  </div>
                </div>
                {!plane && (
                  <UsageFlow
                    key={`${since}-${until}`}
                    data={data}
                    measure={measure}
                    onDrill={(nextPlane, nextModule) =>
                      navigate({ plane: nextPlane, module: nextModule })
                    }
                  />
                )}
                <SecondaryMetrics collapsed={!plane}>
                  {!plane ? (
                    <div className="grid gap-3 md:grid-cols-3">
                      {planes.map((p) => {
                        const row = data.groups.find((group) => group.plane === p)!
                        return (
                          <button
                            key={p}
                            onClick={() => drill(row)}
                            className="group flex flex-col items-stretch rounded-xl border border-line p-4 text-left hover:bg-canvas"
                          >
                            <div className="flex items-center justify-between gap-3">
                              <h2 className="flex items-center gap-2 font-medium">
                                <i
                                  className="h-2 w-2 rounded-full"
                                  style={{ background: colors[p] }}
                                />
                                {t(`planes.${p}`)}
                              </h2>
                              <ChevronRight size={15} className="text-faint group-hover:text-ink" />
                            </div>
                            <div className="mt-4 flex items-center justify-between gap-3">
                              <div>
                                <p className="text-xs text-muted">{label(measure)}</p>
                                <p className="mt-1 text-[22px] font-medium tabular-nums tracking-tight">
                                  {formatted(row, measure)}
                                </p>
                              </div>
                              <MiniTrend data={data} plane={p} measure={measure} />
                            </div>
                            <dl className="mt-4 flex flex-wrap gap-x-5 gap-y-2 text-xs">
                              {measures
                                .filter((m) => m !== measure)
                                .map((m) => (
                                  <div key={m}>
                                    <dt className="text-muted">{label(m)}</dt>
                                    <dd className="mt-1 tabular-nums">{formatted(row, m)}</dd>
                                  </div>
                                ))}
                            </dl>
                            {row.unpriced_requests > 0 && (
                              <p className="mt-3 text-xs text-escalar">
                                {number(row.unpriced_requests)} {label('unknown')}
                              </p>
                            )}
                          </button>
                        )
                      })}
                    </div>
                  ) : (
                    data.totals && <Summary totals={data.totals} />
                  )}
                  <div className="mt-5">
                    {data.groups.every((row) => !row.spans) ? (
                      <Empty>{label('noActivity')}</Empty>
                    ) : (
                      <>
                        <div className="grid gap-8 rounded-2xl border border-line p-4 sm:p-5 lg:grid-cols-[0.85fr_1.15fr]">
                          <section aria-label={label('distribution')}>
                            <h2 className="text-[15px] font-medium">{label('distribution')}</h2>

                            <div className="mt-5 max-h-[360px] space-y-4 overflow-y-auto pr-2">
                              {groups.map((row) => {
                                const max = Math.max(...groups.map((g) => value(g, measure)), 1e-10)
                                const sum = groups.reduce((n, g) => n + value(g, measure), 0)
                                const content = (
                                  <>
                                    <div className="mb-1.5 flex items-start justify-between gap-3 text-xs">
                                      <span className="flex min-w-0 items-start gap-1.5 break-words font-medium">
                                        {groupName(row, level)}
                                        {!module && (
                                          <ChevronRight
                                            size={13}
                                            className="mt-0.5 shrink-0 text-faint"
                                          />
                                        )}
                                      </span>
                                      <span className="shrink-0 text-right tabular-nums">
                                        {formatted(row, measure)}
                                        <small className="ml-2 text-muted">
                                          {sum > 0
                                            ? `${((value(row, measure) / sum) * 100).toLocaleString(getLocale(), { maximumFractionDigits: 1 })}%`
                                            : ''}
                                        </small>
                                      </span>
                                    </div>
                                    <div className="h-3 overflow-hidden rounded-full bg-well">
                                      <div
                                        className="h-full rounded-full"
                                        style={{
                                          width: `${(value(row, measure) / max) * 100}%`,
                                          background: colors[row.plane],
                                        }}
                                      />
                                    </div>
                                  </>
                                )
                                return module ? (
                                  <div key={row.key}>{content}</div>
                                ) : (
                                  <button
                                    key={row.key}
                                    onClick={() => drill(row)}
                                    className="block w-full rounded text-left"
                                  >
                                    {content}
                                  </button>
                                )
                              })}
                            </div>
                          </section>
                          <UsageTimeline
                            key={`${plane}-${module}-${since}-${until}-${measure}`}
                            data={data}
                            measure={measure}
                            onInterval={(start, end) => navigate({ since: start, until: end })}
                          />
                        </div>
                        <details className="mt-5 rounded-xl border border-line">
                          <summary className="cursor-pointer px-4 py-3 text-[13px] font-medium">
                            {label('breakdown')}{' '}
                            <span className="ml-2 text-muted">{groups.length}</span>
                          </summary>
                          <div className="overflow-x-auto">
                            <table className="w-full min-w-[800px] text-left text-xs tabular-nums">
                              <thead className="border-b border-hairline bg-canvas text-muted">
                                <tr>
                                  {[
                                    label(level === 'plane' ? 'area' : level),
                                    label('cost'),
                                    label('input'),
                                    label('output'),
                                    label('cached'),
                                    label('time'),
                                    label('latency'),
                                    label('operations'),
                                  ].map((name) => (
                                    <th key={name} className="px-3 py-3 font-medium">
                                      {name}
                                    </th>
                                  ))}
                                </tr>
                              </thead>
                              <tbody>
                                {groups.map((row) => (
                                  <tr
                                    key={row.key}
                                    className="border-b border-hairline last:border-0"
                                  >
                                    <td className="max-w-56 px-3 py-3">
                                      {module ? (
                                        <span className="break-words">{groupName(row, level)}</span>
                                      ) : (
                                        <button
                                          onClick={() => drill(row)}
                                          className="flex items-center gap-2 text-left font-medium hover:underline"
                                        >
                                          {groupName(row, level)}
                                          <ChevronRight size={13} className="shrink-0 text-faint" />
                                        </button>
                                      )}
                                    </td>
                                    <td className="px-3 py-3">
                                      {formatted(row, 'cost')}
                                      {row.unpriced_requests > 0 && (
                                        <span className="mt-1 block text-[11px] text-escalar">
                                          {number(row.unpriced_requests)} {label('unknown')}
                                        </span>
                                      )}
                                    </td>
                                    <td className="px-3 py-3">{number(row.input_tokens)}</td>
                                    <td className="px-3 py-3">{number(row.output_tokens)}</td>
                                    <td className="px-3 py-3">{number(row.cached_tokens)}</td>
                                    <td className="px-3 py-3">{formatted(row, 'time')}</td>
                                    <td className="whitespace-nowrap px-3 py-3">
                                      {duration(row.p50_ms)} / {duration(row.p95_ms)}
                                    </td>
                                    <td className="px-3 py-3">
                                      {number(row.spans)}
                                      {row.errors > 0 && (
                                        <span className="block text-nopagar">
                                          {row.errors} {label('errors')}
                                        </span>
                                      )}
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </details>
                        <details className="mt-3 text-xs text-muted">
                          <summary className="cursor-pointer">{label('methodology')}</summary>
                          <div className="mt-2 max-w-3xl space-y-2">
                            <p>{label('costNote')}</p>
                            <p>{label('inputNote')}</p>
                            <p>{label('timeNote')}</p>
                            <p>{label('evolutionHint')}</p>
                            {plane === 'execution' && <p>{label('engineNote')}</p>}
                          </div>
                        </details>
                        {module && (
                          <UsageActivity
                            key={`${plane}-${module}-${since}-${until}`}
                            data={data}
                            onPage={(next) => navigate({ offset: String(next) })}
                          />
                        )}
                      </>
                    )}
                  </div>
                </SecondaryMetrics>
                <p className="mt-7 text-[11px] text-muted">
                  {label('updated')} {dateTime(data.until)}
                </p>
              </>
            )
          )}
        </div>
      </div>
    </ProcessScreen>
  )
}

function SecondaryMetrics({ collapsed, children }: { collapsed: boolean; children: ReactNode }) {
  return collapsed ? (
    <details className="mt-6">
      <summary className="cursor-pointer border-b border-line pb-3 text-sm font-medium">
        {label('secondary')}
      </summary>
      <div className="pt-5">{children}</div>
    </details>
  ) : (
    <>{children}</>
  )
}

function Summary({ totals }: { totals: UsageTotals }) {
  const icons = { cost: DollarSign, tokens: Coins, time: Clock3 }
  const tokens = totals.input_tokens + totals.output_tokens
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
      {measures.map((m) => {
        const Icon = icons[m]
        return (
          <div key={m} className="rounded-xl border border-line p-4">
            <p className="flex items-center gap-2 text-xs text-muted">
              <Icon size={14} />
              {label(m)}
            </p>
            <p className="mt-2 text-[24px] font-medium tabular-nums tracking-tight">
              {formatted(totals, m)}
            </p>
            {m === 'cost' && totals.unpriced_requests > 0 && (
              <p className="mt-2 text-[11px] text-escalar">
                {number(totals.unpriced_requests)} {label('unknown')}
              </p>
            )}
            {m === 'tokens' && tokens > 0 && (
              <div
                className="mt-3 flex h-1.5 overflow-hidden rounded-full bg-well"
                role="img"
                aria-label={`${label('input')}: ${number(totals.input_tokens)}, ${label('output')}: ${number(totals.output_tokens)}`}
              >
                <span
                  className="bg-escalar"
                  style={{ width: `${(totals.input_tokens / tokens) * 100}%` }}
                  title={`${label('input')}: ${number(totals.input_tokens)}`}
                />
                <span
                  className="bg-pagar"
                  style={{ width: `${(totals.output_tokens / tokens) * 100}%` }}
                  title={`${label('output')}: ${number(totals.output_tokens)}`}
                />
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

function MiniTrend({
  data,
  plane,
  measure,
}: {
  data: UsageBreakdown
  plane: Plane
  measure: Measure
}) {
  const interval = data.bucket_seconds * 1000
  const end = Math.floor((Date.parse(data.until) - 1) / interval) * interval
  const start =
    Math.floor(Date.parse(data.since ?? data.series[0]?.started_at ?? data.until) / interval) *
    interval
  const buckets = new Map(
    data.series
      .filter((row) => row.plane === plane)
      .map((row) => [Date.parse(row.started_at), value(row, measure)]),
  )
  const values = Array.from(
    { length: Math.max(1, Math.round((end - start) / interval) + 1) },
    (_, i) => buckets.get(start + i * interval) ?? 0,
  )
  const max = Math.max(...values, 1e-10)
  const points = values
    .map(
      (v, i) =>
        `${2 + (values.length === 1 ? 44 : (i / (values.length - 1)) * 88)},${34 - (v / max) * 30}`,
    )
    .join(' ')
  return (
    <svg width="92" height="38" viewBox="0 0 92 38" className="shrink-0" aria-hidden="true">
      <polyline
        points={
          values.length === 1
            ? `2,${34 - (values[0] / max) * 30} 90,${34 - (values[0] / max) * 30}`
            : points
        }
        fill="none"
        stroke={colors[plane]}
        strokeWidth="2"
        strokeLinejoin="round"
      />
    </svg>
  )
}
