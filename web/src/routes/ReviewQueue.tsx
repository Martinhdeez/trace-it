import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router'
import { api } from '../api/client'
import { DataTable } from '../components/shell/DataTable'
import { StatusBadge } from '../components/shell/StatusBadge'
import { Topbar } from '../components/shell/Topbar'
import { NestedCard, PageIntro } from '../components/shell/Well'
import { t } from '../i18n'
import { paths } from '../lib/paths'

export function ReviewQueue() {
  const navigate = useNavigate()
  const escalations = useQuery({
    queryKey: ['escalations'],
    queryFn: () => api.listEscalations(),
  })

  return (
    <>
      <Topbar crumbs={[{ label: t('nav.runs'), to: paths.runs }, { label: t('review.title') }]} />
      <div className="min-h-0 flex-1 overflow-y-auto px-8 pb-10 pt-4">
        <PageIntro
          kicker={`${t('review.kicker')} · 01`}
          title={t('review.title')}
          description={t('review.description')}
        />
        <NestedCard label={`${escalations.data?.length ?? 0} ${t('review.pending')}`}>
          <DataTable
            framed={false}
            rows={escalations.data ?? []}
            onRowClick={(row) =>
              navigate(paths.runInstance(row.processId, row.runId, row.instanceId))
            }
            columns={[
              {
                key: 'file',
                header: 'Archivo',
                render: (row) => <span className="font-mono text-[12px] text-ink">{row.fileId}</span>,
              },
              {
                key: 'process',
                header: t('nav.processes'),
                render: (row) => (
                  <span className="text-[12px] text-muted">
                    {row.processName} · {row.runLabel}
                  </span>
                ),
              },
              {
                key: 'reason',
                header: 'Motivo',
                render: (row) => <span className="text-[12px] text-ink">{row.reason}</span>,
              },
              {
                key: 'proposed',
                header: 'Agente propone',
                render: (row) => <StatusBadge kind={row.proposedDecision} />,
              },
              {
                key: 'since',
                header: 'Desde',
                render: (row) => (
                  <span className="font-mono text-[12px] text-ink">{row.waitingSince}</span>
                ),
              },
            ]}
          />
        </NestedCard>
      </div>
    </>
  )
}
