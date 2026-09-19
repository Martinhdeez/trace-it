import { useDeferredValue, useEffect, useMemo, useRef, useState } from 'react'
import { useParams, useSearchParams } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import { ChevronDown } from 'lucide-react'
import { api } from '../api/client'
import { keys } from '../api/queries'
import { QueueList } from '../components/run/QueueList'
import { TracePane } from '../components/run/TracePane'
import { ProcessScreen } from '../components/process/ProcessScreen'
import { ExportButton } from '../components/process/ExportButton'
import { Input } from '../components/shell/Controls'
import { ErrorNotice } from '../components/shell/Notice'
import { cn } from '../lib/cn'
import { t } from '../i18n'
import { paths } from '../lib/paths'

export function Instances() {
  const processId = Number(useParams().processId)
  const [params, setParams] = useSearchParams()
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState('TODAS')

  const process = useQuery({
    queryKey: keys.process(processId),
    queryFn: () => api.getProcess(processId),
  })
  // The server filters; the summary gives the counts for the menu, which the filter must not change.
  const text = useDeferredValue(search.trim())
  const filters = {
    q: text || undefined,
    status: filter === 'PENDING' ? 'PENDING' : undefined,
    decision: filter !== 'TODAS' && filter !== 'PENDING' ? filter : undefined,
  }
  const instances = useQuery({
    queryKey: keys.instances(processId, filters),
    queryFn: () => api.listInstances(processId, filters),
  })
  const summary = useQuery({
    queryKey: keys.summary(processId),
    queryFn: () => api.summary(processId),
  })
  // The engine stores rule ids, not their text: the list puts the words back.
  const rules = useQuery({
    queryKey: keys.rules(processId),
    queryFn: () => api.listRules(processId),
  })

  const rows = useMemo(() => instances.data ?? [], [instances.data])
  const total = summary.data?.instances ?? rows.length

  const selectedId = params.get('i') ? Number(params.get('i')) : rows[0]?.id
  const selectedVisible = rows.some((item) => item.id === selectedId)

  useEffect(() => {
    if (!rows.length || selectedVisible) return
    setParams({ i: String(rows[0].id) })
  }, [rows, selectedVisible, setParams])

  const detail = useQuery({
    queryKey: keys.instance(selectedId ?? 0),
    queryFn: () => api.getInstance(selectedId!),
    enabled: Boolean(selectedId),
  })

  const outcomes = Object.entries(summary.data?.by_decision ?? {}).sort(([a], [b]) =>
    a.localeCompare(b),
  )
  const pending = summary.data?.by_status.PENDING ?? 0

  return (
    <ProcessScreen
      processId={processId}
      crumbs={[
        { label: 'Procesos', to: paths.processes },
        { label: process.data?.nombre ?? '…', to: paths.process(processId) },
        { label: 'Ejecuciones' },
      ]}
      actions={<ExportButton processId={processId} />}
    >

      {instances.isError ? (
        <div className="px-8 py-4">
          <ErrorNotice error={instances.error} />
        </div>
      ) : null}

      <div className="flex min-h-0 flex-1">
        <QueueList
          items={rows}
          decisionTypes={process.data?.tipos_decision}
          total={total}
          selectedId={selectedId}
          onSelect={(item) => setParams({ i: String(item.id) })}
          header={
            <div className="space-y-1.5">
              <Input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Nombre del archivo…"
                className="bg-surface"
              />
              <FilterMenu
                value={filter}
                onChange={setFilter}
                options={[
                  { value: 'TODAS', label: `Todas ${total}` },
                  ...outcomes.map(([key, count]) => ({
                    value: key,
                    label: `${key.replaceAll('_', ' ')} ${count}`,
                  })),
                  ...(pending > 0
                    ? [{ value: 'PENDING', label: `${t('instanceStatus.PENDING')} ${pending}` }]
                    : []),
                ]}
              />
            </div>
          }
        />
        <TracePane instance={detail.data} rules={rules.data ?? []} />
      </div>
    </ProcessScreen>
  )
}

function FilterMenu({
  value,
  onChange,
  options,
}: {
  value: string
  onChange: (value: string) => void
  options: { value: string; label: string }[]
}) {
  const [open, setOpen] = useState(false)
  const root = useRef<HTMLDivElement>(null)
  const current = options.find((option) => option.value === value)?.label ?? options[0]?.label

  useEffect(() => {
    if (!open) return
    const onPointer = (event: MouseEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false)
    }
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', onPointer)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onPointer)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  return (
    <div ref={root} className="relative">
      <button
        type="button"
        aria-expanded={open}
        aria-haspopup="listbox"
        onClick={() => setOpen((next) => !next)}
        className="flex w-full items-center justify-between gap-2 rounded-full bg-surface px-3 py-1.5 text-left ring-1 ring-line"
      >
        <span className="truncate font-mono text-[11px] text-ink">{current}</span>
        <ChevronDown
          size={12}
          strokeWidth={1.75}
          className={cn(
            'shrink-0 text-faint transition-transform duration-150 ease-[cubic-bezier(0.23,1,0.32,1)]',
            open && 'rotate-180',
          )}
        />
      </button>
      {open ? (
        <ul
          role="listbox"
          className="absolute z-20 mt-1 w-full origin-top rounded-[12px] bg-surface p-1 shadow-float ring-1 ring-line"
        >
          {options.map((option) => (
            <li key={option.value}>
              <button
                type="button"
                role="option"
                aria-selected={option.value === value}
                onClick={() => {
                  onChange(option.value)
                  setOpen(false)
                }}
                className={cn(
                  'flex w-full rounded-[8px] px-2.5 py-1.5 text-left font-mono text-[11px]',
                  option.value === value ? 'bg-canvas text-ink' : 'text-muted hover:bg-canvas hover:text-ink',
                )}
              >
                {option.label}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  )
}
