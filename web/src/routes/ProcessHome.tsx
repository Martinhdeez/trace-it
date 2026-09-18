import { useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import type { QueueItem } from '../api/types'
import { RecentCards, RunPreview } from '../components/shell/RecentCards'
import { DataTable } from '../components/shell/DataTable'
import { StatusBadge } from '../components/shell/StatusBadge'
import { NestedCard, PageIntro } from '../components/shell/Well'
import { NewRunDialog } from '../components/process/NewRunDialog'
import { decisionFromState } from '../lib/status'
import { Topbar } from '../components/shell/Topbar'
import { formatMs } from '../lib/format'
import { applyQueueVersion } from '../lib/norma'
import { useAppState } from '../state/app'
import { cn } from '../lib/cn'
import { t } from '../i18n'
import { paths } from '../lib/paths'

const filters = ['TODAS', 'PAGAR', 'ESCALAR', 'NO_PAGAR', 'OCR'] as const
type Filter = (typeof filters)[number]

const processIndex: Record<string, string> = {
  'reconcile-payments': '01',
  'land-registry': '02',
  'vendor-onboarding': '03',
}

export function ProcessHome() {
  const { processId = 'reconcile-payments' } = useParams()
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [filter, setFilter] = useState<Filter>('TODAS')
  const [runOpen, setRunOpen] = useState(false)
  const { versionFor, setVersionsOpen } = useAppState()
  const versionId = versionFor(processId)

  const process = useQuery({
    queryKey: ['process', processId],
    queryFn: () => api.getProcess(processId),
  })
  const runs = useQuery({
    queryKey: ['runs', processId],
    queryFn: () => api.listRuns(processId),
  })

  const activeRun = runs.data?.[0]
  const instances = useQuery({
    queryKey: ['instances', activeRun?.id],
    queryFn: () => api.listInstances(activeRun!.id),
    enabled: Boolean(activeRun),
  })

  const rows = useMemo(() => {
    let list = applyQueueVersion(instances.data ?? [], processId, versionId)
    if (filter !== 'TODAS') {
      list = list.filter((row) => decisionFromState(row.result, row.state) === filter)
    }
    if (!query.trim()) return list
    const q = query.toLowerCase()
    return list.filter(
      (row) =>
        row.fileId.toLowerCase().includes(q) ||
        row.reason.toLowerCase().includes(q) ||
        (row.result ?? '').toLowerCase().includes(q),
    )
  }, [instances.data, query, filter, versionId, processId])

  if (process.isError) {
    return (
      <>
        <Topbar crumbs={[{ label: t('nav.processes'), to: paths.home }, { label: processId }]} />
        <div className="px-8 py-10 text-[13px] text-muted">{t('process.missing')}</div>
      </>
    )
  }

  const loading = process.isPending || runs.isPending
  const empty = !loading && !activeRun

  return (
    <>
      <Topbar
        crumbs={[{ label: t('nav.processes'), to: paths.home }, { label: process.data?.name ?? '…' }]}
        actions={
          <>
            <button
              type="button"
              onClick={() => setVersionsOpen(true)}
              className="rounded-full bg-canvas px-3 py-1 text-[12px] ring-1 ring-black/[0.06]"
            >
              {t('process.version')} {versionId}
            </button>
            <Link
              to={paths.processRules(processId)}
              className="rounded-full px-3 py-1 text-[12px] text-muted hover:text-ink"
            >
              {t('process.rules')}
            </Link>
            <button
              type="button"
              onClick={() => setRunOpen(true)}
              className="rounded-full bg-ink px-3.5 py-1.5 text-[12px] font-medium text-white"
            >
              {t('process.newRun')}
            </button>
          </>
        }
      />

      <div className="min-h-0 flex-1 overflow-y-auto px-8 pb-10 pt-4">
        <PageIntro
          kicker={`${t('process.kicker')} · ${processIndex[processId] ?? '00'}`}
          title={process.data?.name ?? '…'}
          description={process.data?.summary ?? process.data?.description}
        />

        {empty ? (
          <p className="text-[14px] text-muted">{t('process.empty')}</p>
        ) : (
          <>
            {activeRun ? <RunPreview processId={processId} run={activeRun} /> : null}

            <section className="mt-10">
              <p className="mb-3 font-mono text-[11px] tracking-[0.12em] text-faint">
                {t('process.instances').toUpperCase()}
              </p>
              <NestedCard
                label={
                  activeRun
                    ? `${activeRun.label} · ${rows.length} de ${instances.data?.length ?? 0}`
                    : 'instancias'
                }
                action={
                  <input
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                    placeholder={t('process.searchFile')}
                    className="w-44 rounded-full bg-canvas px-3 py-1 text-[12px] outline-none ring-1 ring-black/[0.06] placeholder:text-faint"
                  />
                }
              >
                <div className="flex gap-1 px-3 pb-2">
                  {filters.map((item) => (
                    <button
                      key={item}
                      type="button"
                      onClick={() => setFilter(item)}
                      className={cn(
                        'rounded-full px-2.5 py-1 text-[12px]',
                        item === filter
                          ? 'bg-canvas text-ink ring-1 ring-black/[0.06]'
                          : 'text-muted hover:text-ink',
                      )}
                    >
                      {item === 'TODAS' ? t('filter.all') : item.replaceAll('_', ' ')}
                    </button>
                  ))}
                </div>
                <DataTable
                  framed={false}
                  rows={rows}
                  onRowClick={(row) =>
                    activeRun && navigate(paths.runInstance(processId, activeRun.id, row.id))
                  }
                  columns={[
                    {
                      key: 'name',
                      header: 'Archivo',
                      render: (row) => <span className="font-mono text-[12px]">{row.fileId}</span>,
                    },
                    {
                      key: 'decision',
                      header: t('run.decision'),
                      render: (row) => (
                        <StatusBadge kind={decisionFromState(row.result, row.state)} />
                      ),
                    },
                    {
                      key: 'step',
                      header: 'Motivo',
                      render: (row) => <span className="text-[13px] text-muted">{row.reason}</span>,
                    },
                    {
                      key: 'owner',
                      header: 'Responsable',
                      render: (row) => <Owner row={row} />,
                    },
                    {
                      key: 'status',
                      header: 'Estado',
                      render: (row) => (
                        <span className="text-[13px] text-muted">{labelState(row)}</span>
                      ),
                    },
                    {
                      key: 'latency',
                      header: 'Latencia',
                      render: (row) => (
                        <span className="font-mono text-[12px]">{formatMs(row.latencyMs)}</span>
                      ),
                    },
                  ]}
                />
              </NestedCard>
            </section>

            {runs.data && runs.data.length > 1 ? (
              <section className="mt-10">
                <p className="mb-3 font-mono text-[11px] tracking-[0.12em] text-faint">
                  {t('process.runs').toUpperCase()}
                </p>
                <NestedCard label={t('process.history')}>
                  <RecentCards processId={processId} runs={runs.data.slice(1)} />
                </NestedCard>
              </section>
            ) : null}
          </>
        )}
      </div>
      <NewRunDialog processId={processId} open={runOpen} onClose={() => setRunOpen(false)} />
    </>
  )
}

function Owner({ row }: { row: QueueItem }) {
  if (row.state === 'PENDIENTE_HUMANO') {
    return <span className="text-[13px]">{t('owner.human')}</span>
  }
  return <span className="text-[13px] text-faint">{t('owner.system')}</span>
}

function labelState(row: QueueItem) {
  if (row.state === 'OCR') return t('state.reading')
  if (row.state === 'PENDIENTE_HUMANO') return t('state.review')
  if (row.result) return t('state.decided')
  return row.state
}
