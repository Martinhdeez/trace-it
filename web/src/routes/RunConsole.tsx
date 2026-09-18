import { useMemo } from 'react'
import { Link, useParams, useSearchParams } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import { DecisionNote } from '../components/run/DecisionNote'
import { DocumentPane } from '../components/run/DocumentPane'
import { QueueList } from '../components/run/QueueList'
import { Topbar } from '../components/shell/Topbar'
import { applyDetailVersion, applyQueueVersion } from '../lib/norma'
import { useAppState } from '../state/app'
import { t } from '../i18n'
import { paths } from '../lib/paths'

export function RunConsole() {
  const { processId = 'reconcile-payments', runId = 'run-014' } = useParams()
  const [params, setParams] = useSearchParams()
  const { versionFor, setVersionsOpen } = useAppState()
  const versionId = versionFor(processId)

  const process = useQuery({
    queryKey: ['process', processId],
    queryFn: () => api.getProcess(processId),
  })
  const run = useQuery({
    queryKey: ['run', runId],
    queryFn: () => api.getRun(runId),
  })
  const instances = useQuery({
    queryKey: ['instances', runId],
    queryFn: () => api.listInstances(runId),
  })

  const items = useMemo(
    () => applyQueueVersion(instances.data ?? [], processId, versionId),
    [instances.data, processId, versionId],
  )

  const selectedId = params.get('i') ?? items[0]?.id
  const selected = useQuery({
    queryKey: ['instance', selectedId],
    queryFn: () => api.getInstance(selectedId!),
    enabled: Boolean(selectedId),
  })
  const detail = applyDetailVersion(selected.data, processId, versionId)

  const jsonl = useMemo(() => {
    if (!detail) return ''
    return JSON.stringify({
      file_id: detail.fileId,
      result: detail.result ?? 'ESCALAR',
      motivo: detail.reason,
      reglas: versionId,
      estado: detail.state,
    })
  }, [detail, versionId])

  const escalarCount = items.filter((item) => item.result === 'ESCALAR').length

  return (
    <>
      <Topbar
        crumbs={[
          { label: t('nav.processes'), to: paths.home },
          { label: process.data?.name ?? '…', to: paths.process(processId) },
          { label: run.data?.label ?? '…' },
        ]}
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
            <span className="rounded-full bg-pagar-soft px-2.5 py-1 font-mono text-[12px] text-pagar">
              {run.data?.status === 'en_curso' ? t('run.inProgress') : run.data ? t('run.done') : '…'}
            </span>
          </>
        }
      />

      <div className="flex min-h-0 flex-1">
        <QueueList
          items={items}
          selectedId={selectedId ?? undefined}
          fileCount={run.data?.fileCount ?? items.length}
          onSelect={(item) => setParams({ i: item.id })}
        />
        <DocumentPane instance={detail} />
        <DecisionNote instance={detail} jsonl={jsonl} />
      </div>

      {escalarCount > 0 ? (
        <div className="flex items-center gap-2 px-4 py-3">
          <p className="rounded-full bg-escalar-soft px-3 py-1 text-[13px] text-escalar">
            {escalarCount} ESCALAR · {t('run.needsReview')}
          </p>
          <Link
            to={paths.review}
            className="rounded-full bg-canvas px-3 py-1 text-[13px] text-ink ring-1 ring-black/[0.06]"
          >
            {t('run.seeAll')}
          </Link>
        </div>
      ) : null}
    </>
  )
}
