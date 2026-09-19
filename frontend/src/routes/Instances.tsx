import { useEffect, useMemo, useRef, useState } from 'react'
import { useParams, useSearchParams } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import { ChevronDown, FileSearch, X } from 'lucide-react'
import { api } from '../api/client'
import { keys } from '../api/queries'
import { DocumentPane } from '../components/run/DocumentPane'
import { QueueList } from '../components/run/QueueList'
import { TracePane } from '../components/run/TracePane'
import { ProcessScreen } from '../components/process/ProcessScreen'
import { ExportButton } from '../components/process/ExportButton'
import { Button, Input } from '../components/shell/Controls'
import { ErrorNotice } from '../components/shell/Notice'
import { cn } from '../lib/cn'
import { label } from '../lib/status'
import { paths } from '../lib/paths'

export function Instances() {
  const processId = Number(useParams().processId)
  const [params, setParams] = useSearchParams()
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState('TODAS')
  const [documentOpen, setDocumentOpen] = useState(false)

  const process = useQuery({
    queryKey: keys.process(processId),
    queryFn: () => api.getProcess(processId),
  })
  const instances = useQuery({
    queryKey: keys.instances(processId),
    queryFn: () => api.listInstances(processId),
  })
  // The engine stores rule ids, not their text: the list puts the words back.
  const rules = useQuery({
    queryKey: keys.rules(processId),
    queryFn: () => api.listRules(processId),
  })

  const all = useMemo(() => instances.data ?? [], [instances.data])

  const rows = useMemo(() => {
    const text = search.trim().toLowerCase()
    return all.filter((item) => {
      if (filter !== 'TODAS' && label(item) !== filter) return false
      return !text || item.nombre.toLowerCase().includes(text)
    })
  }, [all, search, filter])

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

  const outcomes = useMemo(() => {
    const count = new Map<string, number>()
    for (const item of all) {
      const key = label(item)
      count.set(key, (count.get(key) ?? 0) + 1)
    }
    return [...count.entries()].sort(([a], [b]) => a.localeCompare(b))
  }, [all])

  return (
    <ProcessScreen
      processId={processId}
      crumbs={[
        { label: 'Procesos', to: paths.processes },
        { label: process.data?.nombre ?? '…', to: paths.process(processId) },
        { label: 'Ejecuciones' },
      ]}
      actions={
        <>
          <Button tone="soft" onClick={() => setDocumentOpen((open) => !open)}>
            {documentOpen ? <X size={12} strokeWidth={2} /> : <FileSearch size={13} strokeWidth={1.7} />}
            {documentOpen ? 'Cerrar documento' : 'Abrir documento'}
          </Button>
          <ExportButton processId={processId} />
        </>
      }
    >

      {instances.isError ? (
        <div className="px-8 py-4">
          <ErrorNotice error={instances.error} />
        </div>
      ) : null}

      <div className="flex min-h-0 flex-1">
        <QueueList
          items={rows}
          total={all.length}
          selectedId={selectedId}
          onSelect={(item) => setParams({ i: String(item.id) })}
          header={
            <div className="space-y-1.5">
              <Input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Nombre del archivo…"
                className="bg-white"
              />
              <FilterMenu
                value={filter}
                onChange={setFilter}
                options={[
                  { value: 'TODAS', label: `Todas ${all.length}` },
                  ...outcomes.map(([key, count]) => ({
                    value: key,
                    label: `${key.replaceAll('_', ' ')} ${count}`,
                  })),
                ]}
              />
            </div>
          }
        />
        {documentOpen ? (
          <DocumentPane instanceId={detail.data?.id} name={detail.data?.nombre} />
        ) : null}
        <TracePane instance={detail.data} rules={rules.data ?? []} wide={!documentOpen} />
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
        className="flex w-full items-center justify-between gap-2 rounded-full bg-white px-3 py-1.5 text-left ring-1 ring-black/[0.06]"
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
          className="absolute z-20 mt-1 w-full origin-top rounded-[12px] bg-white p-1 shadow-[0_8px_24px_rgba(19,19,19,0.08)] ring-1 ring-black/[0.06]"
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
