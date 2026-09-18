import { useMemo, useState } from 'react'
import { useParams, useSearchParams } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import { keys } from '../api/queries'
import { DocumentPane } from '../components/run/DocumentPane'
import { QueueList } from '../components/run/QueueList'
import { TracePane } from '../components/run/TracePane'
import { ExportButton } from '../components/process/ExportButton'
import { Input } from '../components/shell/Controls'
import { ErrorNotice } from '../components/shell/Notice'
import { Topbar } from '../components/shell/Topbar'
import { label } from '../lib/status'
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
  const detail = useQuery({
    queryKey: keys.instance(selectedId ?? 0),
    queryFn: () => api.getInstance(selectedId!),
    enabled: Boolean(selectedId),
  })

  const chips = useMemo(() => {
    const count = new Map<string, number>()
    for (const item of all) {
      const key = label(item)
      count.set(key, (count.get(key) ?? 0) + 1)
    }
    return [...count.entries()].sort(([a], [b]) => a.localeCompare(b))
  }, [all])

  return (
    <>
      <Topbar
        crumbs={[
          { label: process.data?.nombre ?? '…', to: paths.process(processId) },
          { label: 'Instancias' },
        ]}
        actions={<ExportButton processId={processId} />}
      />

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
              <div className="flex flex-wrap gap-1">
                <Chip active={filter === 'TODAS'} onClick={() => setFilter('TODAS')}>
                  Todas
                </Chip>
                {chips.map(([key, count]) => (
                  <Chip key={key} active={filter === key} onClick={() => setFilter(key)}>
                    {`${key.replaceAll('_', ' ')} ${count}`}
                  </Chip>
                ))}
              </div>
            </div>
          }
        />
        <DocumentPane name={detail.data?.nombre} />
        <TracePane instance={detail.data} rules={rules.data ?? []} />
      </div>
    </>
  )
}

function Chip({
  active,
  onClick,
  children,
}: {
  active: boolean
  onClick: () => void
  children: string
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={
        active
          ? 'rounded-full bg-ink px-2 py-0.5 font-mono text-[10px] text-white'
          : 'rounded-full bg-white px-2 py-0.5 font-mono text-[10px] text-muted ring-1 ring-black/[0.05] hover:text-ink'
      }
    >
      {children}
    </button>
  )
}
