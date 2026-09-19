import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { RefreshCw } from 'lucide-react'
import { api } from '../../api/client'
import { keys } from '../../api/queries'
import type { SourceLoad } from '../../api/contracts'
import { DropZone } from './DropZone'
import { Button } from '../shell/Controls'
import { DataTable } from '../shell/DataTable'
import { Empty, ErrorNotice } from '../shell/Notice'
import { NestedCard } from '../shell/Well'
import { formatRunDate } from '../../lib/format'

/** Maestros and ERP. Not the invoice lote. */
export function TruthSources({ processId }: { processId: number }) {
  const queryClient = useQueryClient()
  const sources = useQuery({
    queryKey: keys.sources(processId),
    queryFn: () => api.listSources(processId),
  })

  const workbook = useMutation({
    mutationFn: (file: File) => api.uploadWorkbook(processId, file),
    onSuccess: (loads: SourceLoad[]) => {
      queryClient.setQueryData(keys.sources(processId), (current: typeof sources.data) => {
        const next = [...(current ?? [])]
        for (const load of loads) {
          const index = next.findIndex((item) => item.nombre === load.nombre)
          if (index >= 0) next[index] = load
          else next.push(load)
        }
        return next
      })
    },
  })
  const sync = useMutation({
    mutationFn: () => api.syncErp(processId),
    onSuccess: (source) =>
      queryClient.setQueryData(keys.sources(processId), (current: typeof sources.data) => [
        ...(current ?? []).filter((item) => item.nombre !== source.nombre),
        source,
      ]),
  })

  return (
    <div className="space-y-8">
      <div className="grid gap-3">
        <NestedCard label="excel de referencia">
          <div className="space-y-2 px-3.5 py-3">
            <DropZone
              accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
              disabled={workbook.isPending}
              label={workbook.isPending ? 'Cargando el Excel…' : 'Proveedores, pedidos, parámetros'}
              hint="Un workbook. Cada hoja entra como una fuente."
              onFiles={(incoming) => {
                const file = incoming[0]
                if (file) workbook.mutate(file)
              }}
            />
            {workbook.isError ? <ErrorNotice error={workbook.error} /> : null}
          </div>
        </NestedCard>

        <NestedCard label="erp">
          <div className="space-y-2 px-3.5 py-3">
            <div className="flex items-center justify-between gap-3 rounded-[12px] bg-well px-3 py-3 ring-1 ring-black/[0.04]">
              <div className="min-w-0">
                <p className="text-[13px] text-ink">Conector del ERP</p>
                <p className="truncate text-[11px] text-muted">
                  http://127.0.0.1:8009 · cada descarga se guarda como una carga más
                </p>
              </div>
              <Button onClick={() => sync.mutate()} disabled={sync.isPending} className="shrink-0">
                <RefreshCw size={12} strokeWidth={2} />
                {sync.isPending ? 'Descargando…' : 'Sincronizar'}
              </Button>
            </div>
            {sync.isError ? <ErrorNotice error={sync.error} /> : null}
          </div>
        </NestedCard>
      </div>

      <section>
        <p className="mb-3 font-mono text-[11px] tracking-[0.12em] text-faint">CARGAS</p>
        <NestedCard label={`${sources.data?.length ?? 0} fuentes`}>
          {sources.data?.length ? (
            <DataTable
              framed={false}
              rows={sources.data.map((source) => ({ ...source, id: source.nombre }))}
              columns={[
                {
                  key: 'nombre',
                  header: 'Nombre',
                  width: '10rem',
                  render: (row) => <span className="font-mono text-[12px]">{row.nombre}</span>,
                },
                {
                  key: 'origen',
                  header: 'Origen',
                  render: (row) => <span className="text-[12px] text-muted">{row.origen}</span>,
                },
                {
                  key: 'filas',
                  header: 'Filas',
                  width: '6rem',
                  render: (row) => <span className="font-mono text-[12px]">{row.filas}</span>,
                },
                {
                  key: 'cargada',
                  header: 'Cargada',
                  width: '10rem',
                  render: (row) => (
                    <span className="text-[12px] text-muted">{formatRunDate(row.cargada)}</span>
                  ),
                },
              ]}
            />
          ) : (
            <Empty>Sin fuentes. Sin ellas, ninguna regla que cruce datos puede decidir.</Empty>
          )}
        </NestedCard>
      </section>
    </div>
  )
}
