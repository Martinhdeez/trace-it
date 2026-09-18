import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router'
import { api } from '../api/client'
import { DataTable } from '../components/shell/DataTable'
import { StatusBadge } from '../components/shell/StatusBadge'
import { Topbar } from '../components/shell/Topbar'
import { NestedCard, PageIntro } from '../components/shell/Well'
import { formatEuro, formatRunDate } from '../lib/format'

export function RunsList() {
  const navigate = useNavigate()
  const runs = useQuery({
    queryKey: ['runs-all'],
    queryFn: () => api.listAllRuns(),
  })
  const processes = useQuery({
    queryKey: ['processes'],
    queryFn: () => api.listProcesses(),
  })

  return (
    <>
      <Topbar crumbs={[{ label: 'Operaciones', to: '/runs' }, { label: 'Runs' }]} />
      <div className="min-h-0 flex-1 overflow-y-auto px-8 pb-10 pt-4">
        <PageIntro
          kicker="Operaciones · 02"
          title="Runs"
          description="Historial de lotes. Cada run aplica una versión de la norma sobre un conjunto de archivos."
        />
        <NestedCard label={`${runs.data?.length ?? 0} lotes`}>
          <DataTable
            framed={false}
            rows={runs.data ?? []}
            onRowClick={(row) => navigate(`/processes/${row.processId}/runs/${row.id}`)}
            columns={[
              {
                key: 'label',
                header: 'Run',
                render: (row) => <span className="font-medium text-ink">{row.label}</span>,
              },
              {
                key: 'process',
                header: 'Proceso',
                render: (row) => (
                  <span className="text-[12px] text-muted">
                    {processes.data?.find((item) => item.id === row.processId)?.name ?? row.processId}
                  </span>
                ),
              },
              {
                key: 'status',
                header: 'Estado',
                render: (row) => (
                  <StatusBadge kind={row.status === 'en_curso' ? 'EN_CURSO' : 'COMPLETADO'}>
                    {row.status === 'en_curso' ? 'En curso' : 'Completado'}
                  </StatusBadge>
                ),
              },
              {
                key: 'norma',
                header: 'Norma',
                render: (row) => (
                  <span className="font-mono text-[12px]">v{row.normaVersion.replace('v', '')}</span>
                ),
              },
              {
                key: 'files',
                header: 'Archivos',
                render: (row) => <span className="font-mono text-[12px]">{row.fileCount}</span>,
              },
              {
                key: 'escalar',
                header: 'ESCALAR',
                render: (row) => (
                  <span className="font-mono text-[12px] text-escalar">{row.counts.escalar}</span>
                ),
              },
              {
                key: 'cost',
                header: '€ / archivo',
                render: (row) => (
                  <span className="font-mono text-[12px]">{formatEuro(row.costPerFile)}</span>
                ),
              },
              {
                key: 'when',
                header: 'Inicio',
                render: (row) => (
                  <span className="text-[12px] text-muted">{formatRunDate(row.startedAt)}</span>
                ),
              },
            ]}
          />
        </NestedCard>
      </div>
    </>
  )
}
