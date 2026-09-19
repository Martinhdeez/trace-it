import { useState } from 'react'
import { useParams } from 'react-router'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { RefreshCw } from 'lucide-react'
import { api } from '../api/client'
import { keys } from '../api/queries'
import type { IngestedFile, SourceLoad } from '../api/contracts'
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
  const [ingest, setIngest] = useState<{ done: number; total: number } | null>(null)

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

  const refreshLoads = () => {
    void queryClient.invalidateQueries({ queryKey: keys.files(processId) })
    void queryClient.invalidateQueries({ queryKey: ['instances'] })
    void queryClient.invalidateQueries({ queryKey: keys.sources(processId) })
  }

  const upload = useMutation({
    mutationFn: async (incoming: File[]) => {
      const pdfs = incoming.filter((file) => file.name.toLowerCase().endsWith('.pdf'))
      const added: IngestedFile[] = []
      setIngest({ done: 0, total: pdfs.length })
      try {
        for (const file of pdfs) {
          added.push(...(await api.uploadFiles(processId, [file])))
          setIngest({ done: added.length, total: pdfs.length })
        }
      } finally {
        setIngest(null)
      }
      return added
    },
    onSuccess: refreshLoads,
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
    <>
      <Topbar
        crumbs={[
          { label: process.data?.nombre ?? '…', to: paths.process(processId) },
          { label: 'Inicializar' },
        ]}
      />

      <div className="min-h-0 flex-1 overflow-y-auto px-8 pb-10 pt-4">
        <PageIntro
          kicker="Configuración"
          title="Inicializar proceso"
          description="Carga los documentos del lote y conecta sus fuentes de referencia. Los archivos repetidos se detectan por hash."
        />

        <div className="grid gap-3 lg:grid-cols-2">
          <NestedCard label="instancias">
            <div className="space-y-2 px-3.5 py-3">
              <DropZone
                multiple
                accept="application/pdf"
                disabled={upload.isPending}
                label={
                  ingest
                    ? `Subiendo ${ingest.done} / ${ingest.total}`
                    : 'Facturas en PDF'
                }
                hint="Uno a uno por la API, como en la prueba en vivo. Arrastra el lote o elige."
                onFiles={(incoming) => upload.mutate(incoming)}
              />
              {upload.isError ? <ErrorNotice error={upload.error} /> : null}
            </div>
          </NestedCard>

          <NestedCard label="fuentes de verdad">
            <div className="space-y-2 px-3.5 py-3">
              <DropZone
                accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                disabled={workbook.isPending}
                label={workbook.isPending ? 'Cargando el Excel…' : 'Excel de proveedores y pedidos'}
                hint="FINAL_v7…xlsx · hojas de proveedores, pedidos y parámetros"
                onFiles={(incoming) => {
                  const file = incoming[0]
                  if (file) workbook.mutate(file)
                }}
              />
              {workbook.isError ? <ErrorNotice error={workbook.error} /> : null}
              <div className="flex items-center justify-between gap-3 rounded-[12px] bg-well px-3 py-3 ring-1 ring-line">
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
                rows={files.data.slice(0, 50).map((file, index) => ({
                  ...file,
                  id: file.hash || `${file.nombre}-${index}`,
                }))}
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
                        {row.tiene_texto ? 'extraído' : 'sin símbolos'}
                      </span>
                    ),
                  },
                  {
                    key: 'hash',
                    header: 'Hash',
                    width: '10rem',
                    render: (row) => (
                      <span className="font-mono text-[11px] text-faint">
                        {row.hash ? row.hash.slice(0, 16) : '—'}
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
