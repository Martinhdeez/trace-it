import { useState } from 'react'
import { Link } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import { ChevronDown, ChevronRight } from 'lucide-react'
import { api } from '../../api/client'
import type { SpanNode, UsageActivity as Activity, UsageBreakdown } from '../../api/contracts'
import { paths } from '../../lib/paths'
import { cn } from '../../lib/cn'
import { Button } from '../shell/Controls'
import { ErrorNotice } from '../shell/Notice'
import { dateTime, duration, formatted, label, moduleName, number } from './usage'
import { demoTrace } from './demo'

export function UsageActivity({
  data,
  hardcoded = false,
  onPage,
}: {
  data: UsageBreakdown
  hardcoded?: boolean
  onPage: (offset: number) => void
}) {
  const [selected, setSelected] = useState<number | null>(null)
  const item = data.activity.find((row) => row.id === selected)
  return (
    <section className="mt-8" aria-label={label('activity')}>
      <h2 className="text-[15px] font-medium">{label('activity')}</h2>

      <div className="mt-4 overflow-x-auto rounded-xl ring-1 ring-line">
        <table className="w-full min-w-[720px] text-left text-xs tabular-nums">
          <thead className="border-b border-hairline bg-canvas text-muted">
            <tr>
              {[
                label('started'),
                label('model'),
                label('cost'),
                label('tokens'),
                label('time'),
                label('duration'),
                '',
              ].map((title, i) => (
                <th key={i} className="px-3 py-3 font-medium">
                  {title}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.activity.map((row) => (
              <tr
                key={row.id}
                className={cn(
                  'border-b border-hairline last:border-0',
                  row.id === selected && 'bg-canvas',
                )}
              >
                <td className="px-3 py-3">
                  <span
                    className={cn(
                      'mr-2 inline-block h-1.5 w-1.5 rounded-full',
                      row.status === 'error' ? 'bg-nopagar' : 'bg-pagar',
                    )}
                    title={label(row.status === 'error' ? 'failure' : 'success')}
                  />
                  {dateTime(row.started_at)}
                </td>
                <td className="max-w-48 break-words px-3 py-3">
                  {row.model ?? moduleName(row.step)}
                  {row.provider && <span className="block text-muted">{row.provider}</span>}
                  {row.replays > 0 && <span className="block text-muted">{label('replays')}</span>}
                </td>
                <td className="px-3 py-3">{formatted(row, 'cost')}</td>
                <td className="px-3 py-3">{formatted(row, 'tokens')}</td>
                <td className="px-3 py-3">{formatted(row, 'time')}</td>
                <td className="px-3 py-3">{duration(row.duration_ms)}</td>
                <td className="px-3 py-3">
                  <button
                    className="rounded p-1 hover:bg-well"
                    aria-label={`${label('inspect')} #${row.id}`}
                    aria-expanded={row.id === selected}
                    onClick={() => setSelected(row.id === selected ? null : row.id)}
                  >
                    {row.id === selected ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="mt-3 flex flex-wrap items-center justify-between gap-3 text-xs text-muted">
        <span>
          {number(data.activity_total ? data.offset + 1 : 0)}–
          {number(data.offset + data.activity.length)} {label('of')} {number(data.activity_total)}
        </span>
        <div className="flex gap-2">
          <Button
            disabled={data.offset === 0}
            onClick={() => {
              setSelected(null)
              onPage(Math.max(0, data.offset - data.limit))
            }}
          >
            {label('previous')}
          </Button>
          <Button
            disabled={data.offset + data.limit >= data.activity_total}
            onClick={() => {
              setSelected(null)
              onPage(data.offset + data.limit)
            }}
          >
            {label('next')}
          </Button>
        </div>
      </div>
      {item && (
        <Operation
          key={item.id}
          item={item}
          hardcoded={hardcoded}
          processId={data.process_id}
          onClose={() => setSelected(null)}
        />
      )}
    </section>
  )
}

function Operation({
  item,
  hardcoded,
  processId,
  onClose,
}: {
  item: Activity
  hardcoded: boolean
  processId: number
  onClose: () => void
}) {
  const [showTrace, setShowTrace] = useState(false)
  const trace = useQuery({
    queryKey: ['usage-trace', hardcoded, item.trace_id],
    queryFn: () => (hardcoded ? demoTrace(item) : api.traceSpans(item.trace_id)),
    enabled: showTrace,
  })
  return (
    <div
      className="mt-4 rounded-xl border border-line p-4"
      role="region"
      aria-label={`${label('recorded')} #${item.id}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="font-medium">
            {moduleName(item.step)} #{item.id}
          </h3>
          <p className="mt-1 break-all text-xs text-muted">
            {item.model ?? label('local')} / {dateTime(item.started_at)}
          </p>
        </div>
        <Button tone="ghost" onClick={onClose}>
          {label('close')}
        </Button>
      </div>
      <dl className="my-4 grid grid-cols-2 gap-x-5 gap-y-3 text-xs sm:grid-cols-4">
        {[
          [label('input'), number(item.input_tokens)],
          [label('output'), number(item.output_tokens)],
          [label('cached'), number(item.cached_tokens)],
          [label('requests'), number(item.requests)],
          [label('cost'), formatted(item, 'cost')],
          [label('time'), formatted(item, 'time')],
          [label('duration'), duration(item.duration_ms)],
          [label('errors'), number(item.errors)],
        ].map(([name, content]) => (
          <div key={name}>
            <dt className="text-muted">{name}</dt>
            <dd className="mt-1 tabular-nums">{content}</dd>
          </div>
        ))}
      </dl>
      {item.unpriced_requests > 0 && (
        <p className="mb-3 text-xs text-escalar">
          {number(item.unpriced_requests)} {label('unknown')}
        </p>
      )}
      <div className="flex flex-wrap items-center gap-4 text-xs">
        {item.rule_id !== null && (
          <Link className="underline" to={paths.rule(processId, item.rule_id)}>
            {label('rule')} #{item.rule_id}
          </Link>
        )}
        {item.instance_id !== null && (
          <Link className="underline" to={paths.instance(processId, item.instance_id)}>
            {label('instance')} #{item.instance_id}
          </Link>
        )}
        <Button aria-expanded={showTrace} onClick={() => setShowTrace(!showTrace)}>
          {label('trace')}
          {showTrace ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
        </Button>
      </div>
      {showTrace && (
        <div className="mt-4">
          <p className="mb-3 text-xs text-muted">{label('traceHint')}</p>
          {trace.isPending && (
            <p role="status" className="text-xs text-muted">
              {label('trace')}…
            </p>
          )}
          {trace.isError && (
            <ErrorNotice
              error={trace.error}
              action={<Button onClick={() => void trace.refetch()}>{label('refresh')}</Button>}
            />
          )}
          {trace.data?.map((span) => (
            <TraceStep key={span.span_id} span={span} selected={item.span_id} />
          ))}
        </div>
      )}
    </div>
  )
}

function TraceStep({ span, selected }: { span: SpanNode; selected: string }) {
  return (
    <details
      open={span.span_id === selected || undefined}
      className="my-1 min-w-0 border-l border-line pl-3 text-xs"
    >
      <summary
        className={cn(
          'cursor-pointer py-1',
          span.span_id === selected && 'font-medium text-escalar',
        )}
      >
        {moduleName(span.step)}{' '}
        <span className="ml-2 text-muted">{duration(span.duration_ms)}</span>{' '}
        {span.status === 'error' && <span className="text-nopagar">{label('failure')}</span>}
      </summary>
      {span.data && (
        <pre className="my-2 max-h-64 overflow-auto whitespace-pre-wrap break-all rounded-lg bg-canvas p-3 text-[11px]">
          {JSON.stringify(span.data, null, 2)}
        </pre>
      )}
      {span.children?.map((child) => (
        <TraceStep key={child.span_id} span={child} selected={selected} />
      ))}
    </details>
  )
}
