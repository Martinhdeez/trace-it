import { useState } from 'react'
import { ScanSearch } from 'lucide-react'
import type { Plane, UsageBreakdown } from '../../api/contracts'
import { t, getLocale } from '../../i18n'
import { Button } from '../shell/Controls'
import {
  colors,
  dateTime,
  duration,
  label,
  money,
  number,
  planes,
  value,
  type Measure,
} from './usage'

export function UsageTimeline({
  data,
  measure,
  onInterval,
}: {
  data: UsageBreakdown
  measure: Measure
  onInterval: (since: string, until: string) => void
}) {
  const [active, setActive] = useState<number | null>(null)
  const interval = data.bucket_seconds * 1000
  const last = Math.floor((Date.parse(data.until) - 1) / interval) * interval
  const first = data.since
    ? Math.floor(Date.parse(data.since) / interval) * interval
    : data.series.length
      ? Date.parse(data.series[0].started_at)
      : last
  const times = Array.from(
    { length: Math.max(1, Math.round((last - first) / interval) + 1) },
    (_, i) => first + i * interval,
  )
  const seriesPlanes = data.plane ? [data.plane] : planes
  const buckets = new Map(
    data.series.map((item) => [`${item.plane}:${Date.parse(item.started_at)}`, item]),
  )
  const points = times.map(
    (time) =>
      Object.fromEntries(
        seriesPlanes.map((plane) => {
          const row = buckets.get(`${plane}:${time}`)
          return [plane, row ? value(row, measure) : 0]
        }),
      ) as Record<Plane, number>,
  )
  const max = Math.max(0, ...points.flatMap((point) => seriesPlanes.map((plane) => point[plane])))
  const chartMax = max || 1
  const x = (i: number) => 64 + (times.length === 1 ? 266 : (i / (times.length - 1)) * 532)
  const y = (v: number) => 184 - (v / chartMax) * 144
  const display = (v: number) =>
    measure === 'cost' ? money(v) : measure === 'time' ? duration(v) : number(v)
  const selected = active === null ? times.length - 1 : Math.min(active, times.length - 1)
  const date = (time: number) =>
    new Date(time).toLocaleString(
      getLocale(),
      interval < 86400000
        ? { hour: '2-digit', minute: '2-digit' }
        : { month: 'short', day: 'numeric' },
    )
  const inspect = (i: number) =>
    onInterval(
      new Date(Math.max(times[i], data.since ? Date.parse(data.since) : times[i])).toISOString(),
      new Date(Math.min(times[i] + interval, Date.parse(data.until))).toISOString(),
    )

  return (
    <section className="min-w-0" aria-label={label('evolution')}>
      <h2 className="text-[15px] font-medium">{label('evolution')}</h2>

      <svg
        className="mt-3 w-full overflow-visible"
        viewBox="0 0 620 224"
        role="img"
        aria-label={`${label('evolution')}: ${label(measure)}`}
      >
        <title>
          {label('evolution')}: {label(measure)}
        </title>
        {[0, 0.5, 1].map((tick) => (
          <g key={tick}>
            <line
              x1="64"
              x2="596"
              y1={y(chartMax * tick)}
              y2={y(chartMax * tick)}
              stroke="var(--color-hairline)"
            />
            <text
              x="56"
              y={y(chartMax * tick) + 4}
              textAnchor="end"
              fill="var(--color-muted)"
              fontSize="10"
            >
              {display(max * tick)}
            </text>
          </g>
        ))}
        {seriesPlanes.map((plane) => (
          <g key={plane}>
            {data.plane && points.length > 1 && (
              <polygon
                points={`${x(0)},184 ${points.map((point, i) => `${x(i)},${y(point[plane])}`).join(' ')} ${x(points.length - 1)},184`}
                fill={colors[plane]}
                opacity="0.09"
              />
            )}
            <polyline
              points={points.map((point, i) => `${x(i)},${y(point[plane])}`).join(' ')}
              fill="none"
              stroke={colors[plane]}
              strokeWidth="2"
              strokeLinejoin="round"
            />
            {points.map((point, i) => (
              <circle
                key={times[i]}
                cx={x(i)}
                cy={y(point[plane])}
                r={selected === i ? 4 : 2.5}
                fill={colors[plane]}
              >
                <title>
                  {dateTime(new Date(times[i]).toISOString())}: {t(`planes.${plane}`)}{' '}
                  {display(point[plane])}
                </title>
              </circle>
            ))}
          </g>
        ))}
        <line
          x1={x(selected)}
          x2={x(selected)}
          y1="32"
          y2="184"
          stroke="var(--color-muted)"
          strokeDasharray="3 4"
          opacity="0.5"
        />
        {times.map((time, i) => (
          <rect
            key={time}
            x={x(i) - Math.max(5, 532 / times.length / 2)}
            y="32"
            width={Math.max(10, 532 / times.length)}
            height="160"
            fill="transparent"
            onMouseEnter={() => setActive(i)}
            onClick={() => inspect(i)}
            className="cursor-pointer"
          />
        ))}
        {[0, Math.floor((times.length - 1) / 2), times.length - 1]
          .filter((v, i, a) => a.indexOf(v) === i)
          .map((i) => (
            <text
              key={i}
              x={x(i)}
              y="214"
              textAnchor={i === 0 ? 'start' : i === times.length - 1 ? 'end' : 'middle'}
              fill="var(--color-muted)"
              fontSize="11"
            >
              {date(times[i])}
            </text>
          ))}
      </svg>
      {!max && <p className="mb-3 text-xs text-muted">{label('noValues')}</p>}
      <div className="rounded-xl bg-canvas px-3 py-2 text-xs">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <span>{dateTime(new Date(times[selected]).toISOString())}</span>
          <Button
            tone="ghost"
            className="p-1"
            aria-label={label('inspectInterval')}
            title={label('inspectInterval')}
            onClick={() => inspect(selected)}
          >
            <ScanSearch size={15} />
          </Button>
        </div>
        <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1">
          {seriesPlanes.map((plane) => {
            const unpriced = buckets.get(`${plane}:${times[selected]}`)?.unpriced_requests ?? 0
            return (
              <span key={plane} className="flex items-center gap-1.5">
                <i className="h-2 w-2 rounded-full" style={{ background: colors[plane] }} />
                {t(`planes.${plane}`)}{' '}
                <b className="font-medium tabular-nums">{display(points[selected][plane])}</b>
                {measure === 'cost' && unpriced > 0 && (
                  <span className="text-muted">
                    + {number(unpriced)} {label('unknown')}
                  </span>
                )}
              </span>
            )
          })}
        </div>
      </div>
      <input
        type="range"
        min="0"
        max={Math.max(0, times.length - 1)}
        value={selected}
        aria-label={label('selectedPeriod')}
        className="sr-only accent-ink focus:not-sr-only focus:mt-3 focus:w-full"
        onChange={(event) => setActive(Number(event.target.value))}
      />
      <details className="mt-2 text-xs text-muted">
        <summary className="cursor-pointer">{label('data')}</summary>
        <div className="mt-2 max-h-52 overflow-auto">
          <table className="w-full text-left tabular-nums">
            <thead>
              <tr>
                <th>{label('started')}</th>
                {seriesPlanes.map((p) => (
                  <th key={p}>{t(`planes.${p}`)}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {times.map((time, i) => (
                <tr key={time}>
                  <td className="py-1">{dateTime(new Date(time).toISOString())}</td>
                  {seriesPlanes.map((p) => (
                    <td key={p}>
                      {display(points[i][p])}
                      {measure === 'cost' &&
                      (buckets.get(`${p}:${time}`)?.unpriced_requests ?? 0) > 0
                        ? ` (${label('partial')})`
                        : ''}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </section>
  )
}
