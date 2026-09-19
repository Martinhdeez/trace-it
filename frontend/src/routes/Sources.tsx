import { useParams } from 'react-router'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { RefreshCw } from 'lucide-react'
import { api } from '../api/client'
import { keys } from '../api/queries'
import { DropZone } from '../components/process/DropZone'
import { Button } from '../components/shell/Controls'
import { DataTable } from '../components/shell/DataTable'
import { Empty, ErrorNotice } from '../components/shell/Notice'
import { Topbar } from '../components/shell/Topbar'
import { NestedCard, PageIntro } from '../components/shell/Well'
import { formatRunDate } from '../lib/format'
import { paths } from '../lib/paths'

/** F2 and F3: what goes in. Files are identified by hash, so re-uploading is free. */
export function Sources() {
  const processId = Number(useParams().processId)
  const queryClient = useQueryClient()

  const process = useQuery({
    queryKey: keys.process(processId),
    queryFn: () => api.getProcess(processId),
  })
  const files = useQuery({
    queryKey: keys.files(processId),
    queryFn: () => api.listFiles(processId),
  })
  const sources = useQuery({
    queryKey: keys.sources(processId),
    queryFn: () => api.listSources(processId),
  })

  const upload = useMutation({
    mutationFn: (incoming: File[]) => api.uploadFiles(processId, incoming),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['files'] })
      void queryClient.invalidateQueries({ queryKey: ['instances'] })
    },
  })
  const loadSheet = useMutation({
    mutationFn: ({ name, file }: { name: string; file: File }) =>
      api.uploadSource(processId, name, file),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['sources'] }),
  })
  const sync = useMutation({
    mutationFn: () => api.syncErp(processId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['sources'] }),
  })

  return (
    <>
      <Topbar
        crumbs={[
          { label: process.data?.nombre ?? '…', to: paths.process(processId) },
          { label: 'Fuentes' },
        ]}
      />

      <div className="min-h-0 flex-1 overflow-y-auto px-8 pb-10 pt-4">
        <PageIntro
          kicker="Fuentes"
          title="Lo que entra"
          description="Los ficheros se guardan tal cual, identificados por el hash de su contenido, junto al texto completo que se les extrae. Las fuentes de verdad se cargan aparte, y de cada una vale la última carga: el mismo fichero dos veces no se procesa dos veces."
        />

        <div className="grid gap-3 lg:grid-cols-2">
          <NestedCard label="instancias">
            <div className="space-y-2 px-3.5 py-3">
              <DropZone
                multiple
                accept="application/pdf"
                disabled={upload.isPending}
                label={upload.isPending ? 'Subiendo…' : 'Facturas en PDF'}
                hint="Arrastra la carpeta del lote o pulsa para elegir"
                onFiles={(incoming) => upload.mutate(incoming)}
              />
              {upload.isError ? <ErrorNotice error={upload.error} /> : null}
            </div>
          </NestedCard>

          <NestedCard label="fuentes de verdad">
            <div className="space-y-2 px-3.5 py-3">
              <DropZone
                accept=".xlsx,.xls,.csv"
                disabled={loadSheet.isPending}
                label={loadSheet.isPending ? 'Cargando…' : 'Excel de proveedores y pedidos'}
                hint="FINAL_v7_DEFINITIVO_ahorasi.xlsx"
                onFiles={([file]) => loadSheet.mutate({ name: 'proveedores', file })}
              />
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
              {loadSheet.isError ? <ErrorNotice error={loadSheet.error} /> : null}
              {sync.isError ? <ErrorNotice error={sync.error} /> : null}
            </div>
          </NestedCard>
        </div>

        <section className="mt-8">
          <p className="mb-3 font-mono text-[11px] tracking-[0.12em] text-faint">FUENTES CARGADAS</p>
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

        <section className="mt-8">
          <p className="mb-3 font-mono text-[11px] tracking-[0.12em] text-faint">
            FICHEROS INGERIDOS
          </p>
          {files.isError ? <ErrorNotice error={files.error} /> : null}
          <NestedCard label={`${files.data?.length ?? 0} ficheros`}>
            {files.data?.length ? (
              <DataTable
                framed={false}
                rows={files.data.slice(0, 50).map((file) => ({ ...file, id: file.hash }))}
                columns={[
                  {
                    key: 'nombre',
                    header: 'Archivo',
                    render: (row) => <span className="font-mono text-[12px]">{row.nombre}</span>,
                  },
                  {
                    key: 'texto',
                    header: 'Texto',
                    width: '9rem',
                    render: (row) => (
                      <span className="text-[12px] text-muted">
                        {row.tiene_texto ? 'extraído' : 'escaneada · visión'}
                      </span>
                    ),
                  },
                  {
                    key: 'hash',
                    header: 'Hash',
                    width: '10rem',
                    render: (row) => (
                      <span className="font-mono text-[11px] text-faint">
                        {row.hash.slice(0, 16)}
                      </span>
                    ),
                  },
                ]}
              />
            ) : (
              <Empty>Todavía no hay ficheros en este proceso.</Empty>
            )}
          </NestedCard>
        </section>
      </div>
    </>
  )
}
