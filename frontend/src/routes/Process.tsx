import { useMemo, useState } from 'react'
import { Link, useParams } from 'react-router'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  AlertTriangle,
  BookOpenText,
  Cpu,
  Download,
  FileText,
  Play,
} from 'lucide-react'
import { api } from '../api/client'
import { keys } from '../api/queries'
import { ProcessExecutionSettings } from '../components/process/ExecutionSettings'
import { ExportButton } from '../components/process/ExportButton'
import {
  revokePreview,
  toPreview,
  type FilePreview,
} from '../components/process/FileChip'
import { ProcessScreen } from '../components/process/ProcessScreen'
import { BatchRunPanel } from '../components/run/BatchRunPanel'
import { Button } from '../components/shell/Controls'
import { Overlay } from '../components/shell/Overlay'
import { ErrorNotice } from '../components/shell/Notice'
import { cn } from '../lib/cn'
import { paths } from '../lib/paths'
import type { Instance, NormRule, Rule } from '../api/contracts'
import { countsOf, waitingOnPerson, type Counts } from '../lib/process'

type QueuedFile = FilePreview & { file: File }

type SessionRun = {
  finishedAt: Date
  decided: number
  split: string
}

export function Process() {
  const processId = Number(useParams().processId)
  const queryClient = useQueryClient()
  const [runPanelOpen, setRunPanelOpen] = useState(false)
  const [queue, setQueue] = useState<QueuedFile[]>([])
  const [runs, setRuns] = useState<SessionRun[]>([])

  const process = useQuery({
    queryKey: keys.process(processId),
    queryFn: () => api.getProcess(processId),
  })
  const counts = useQuery({
    queryKey: keys.instances(processId),
    queryFn: () => api.listInstances(processId),
    select: countsOf,
  })
  const instances = useQuery({
    queryKey: keys.instances(processId),
    queryFn: () => api.listInstances(processId),
  })
  const rules = useQuery({
    queryKey: keys.rules(processId),
    queryFn: () => api.listRules(processId),
    refetchInterval: (query) =>
      query.state.data?.some((rule) => rule.estado === 'compilando') ? 2_000 : false,
  })
  const norm = useQuery({
    queryKey: keys.norm(processId),
    queryFn: () => api.listNormRules(processId),
  })
  const findings = useQuery({
    queryKey: keys.findings(processId),
    queryFn: () => api.listFindings(processId),
  })

  const run = useMutation({
    mutationFn: () => api.run(processId),
    onSuccess: (data) => {
      const split = Object.entries(data.por_decision)
        .map(([name, value]) => `${value} ${name.replaceAll('_', ' ')}`)
        .join(', ')
      setRuns((current) => [
        { finishedAt: new Date(), decided: data.decididas, split },
        ...current,
      ])
      void queryClient.invalidateQueries()
    },
  })

  const upload = useMutation({
    mutationFn: (incoming: File[]) => api.uploadFiles(processId, incoming),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: keys.instances(processId) })
      void queryClient.invalidateQueries({ queryKey: keys.files(processId) })
    },
  })

  const active = rules.data?.filter((rule) => rule.estado === 'activa').length ?? 0
  const compiling = rules.data?.filter((rule) => rule.estado === 'compilando').length ?? 0
  const waiting = waitingOnPerson(process.data, counts.data)
  const busy = run.isPending || upload.isPending
  const startBlocked =
    compiling > 0
      ? 'El motor no arranca mientras hay reglas compilando'
      : active === 0
        ? 'Hace falta al menos una regla activa'
        : undefined
  const latestRun = runs[0]

  const addToQueue = (incoming: File[]) => {
    setQueue((current) => [...current, ...incoming.map(toPreview)])
  }

  const removeFromQueue = (id: string) => {
    setQueue((current) => {
      const gone = current.find((item) => item.id === id)
      if (gone) revokePreview(gone)
      return current.filter((item) => item.id !== id)
    })
  }

  const clearQueue = () => {
    queue.forEach(revokePreview)
    setQueue([])
  }

  const openRun = () => {
    if (busy) {
      setRunPanelOpen(true)
      return
    }
    if (run.isSuccess || !runPanelOpen) {
      run.reset()
      upload.reset()
      clearQueue()
    }
    setRunPanelOpen(true)
  }

  const closeRun = () => {
    if (busy) return
    if (!run.isSuccess) clearQueue()
    else {
      queue.forEach(revokePreview)
      setQueue([])
    }
    setRunPanelOpen(false)
  }

  const startRun = async () => {
    if (!queue.length || startBlocked) return
    try {
      await upload.mutateAsync(queue.map((item) => item.file))
      await run.mutateAsync()
    } catch {
      // el panel muestra el error
    }
  }

  if (process.isError) {
    return (
      <ProcessScreen
        processId={processId}
        crumbs={[{ label: 'Procesos', to: paths.processes }, { label: String(processId) }]}
      >
        <div className="px-8 py-6">
          <ErrorNotice error={process.error} />
        </div>
      </ProcessScreen>
    )
  }

  return (
    <ProcessScreen
      processId={processId}
      crumbs={[{ label: 'Procesos', to: paths.processes }, { label: process.data?.nombre ?? '…' }]}
      actions={
        <>
          <Button
            tone="soft"
            onClick={openRun}
            disabled={busy}
            title="Elige el lote y lo encolas. El motor arranca después."
          >
            <Play size={12} strokeWidth={2} />
            {busy ? 'Ejecutando…' : 'Ejecutar'}
          </Button>
          <ExportButton processId={processId} />
        </>
      }
    >
      {runPanelOpen ? (
        <Overlay onClose={closeRun} size="lg">
          <BatchRunPanel
            queue={queue}
            running={run.isPending}
            uploading={upload.isPending}
            finished={run.isSuccess}
            rulesCount={active}
            startBlocked={startBlocked}
            error={upload.error ?? run.error}
            onFiles={addToQueue}
            onRemove={removeFromQueue}
            onStart={() => void startRun()}
            onClose={closeRun}
          />
        </Overlay>
      ) : null}

      <div className="min-h-0 flex-1 overflow-y-auto px-8 pb-10 pt-4">
        <header className="mb-6">
          <p className="text-[13px] text-muted">Panel</p>
          <h1 className="mt-1 text-[32px] font-medium leading-[1.1] tracking-[-0.045em]">
            {process.data?.nombre ?? '…'}
          </h1>
          <p className="mt-2 max-w-2xl text-[14.5px] leading-6 text-muted">
            {process.data?.descripcion}
          </p>
        </header>

        <Alerts
          processId={processId}
          waiting={waiting}
          compiling={compiling}
          findings={findings.data?.length ?? 0}
        />

        <Metrics
          counts={counts.data}
          waiting={waiting}
          latestRun={latestRun}
        />

        <Pipeline
          total={counts.data?.total ?? 0}
          norm={norm.data ?? []}
          rules={rules.data ?? []}
          decided={counts.data?.decided ?? 0}
          pending={(counts.data?.pending ?? 0) + (counts.data?.review ?? 0)}
        />

        <Runs processId={processId} runs={runs} documentCount={counts.data?.total ?? 0} />

        <Split counts={counts.data} instances={instances.data ?? []} />
        <ProcessExecutionSettings processId={processId} />
      </div>
    </ProcessScreen>
  )
}

function Alerts({
  processId,
  waiting,
  compiling,
  findings,
}: {
  processId: number
  waiting: number
  compiling: number
  findings: number
}) {
  const items = [
    waiting > 0
      ? {
          to: paths.review(processId),
          text: `${waiting} documento${waiting === 1 ? '' : 's'} esperan a una persona`,
        }
      : null,
    compiling > 0
      ? {
          to: paths.definition(processId),
          text: `${compiling} regla${compiling === 1 ? '' : 's'} compilando. El motor no arranca hasta que terminen.`,
        }
      : null,
    findings > 0
      ? {
          to: paths.versions(processId),
          text: `${findings} decisión${findings === 1 ? '' : 'es'} del pasado contradicen la norma de hoy`,
        }
      : null,
  ].filter((item): item is { to: string; text: string } => item != null)

  if (items.length === 0) return null

  return (
    <section className="mb-6 overflow-hidden rounded-[16px] bg-white ring-1 ring-black/[0.06]">
      <div className="flex items-center gap-2 px-4 py-2.5">
        <AlertTriangle size={14} strokeWidth={1.6} className="text-escalar" />
        <p className="font-mono text-[11px] tracking-[0.12em] text-faint">ATENCIÓN</p>
      </div>
      <ul className="divide-y divide-hairline border-t border-hairline">
        {items.map((item) => (
          <li key={item.to}>
            <Link to={item.to} className="block px-4 py-2.5 text-[13px] text-ink hover:bg-canvas">
              {item.text}
            </Link>
          </li>
        ))}
      </ul>
    </section>
  )
}

function Metrics({
  counts,
  waiting,
  latestRun,
}: {
  counts: Counts | undefined
  waiting: number
  latestRun: SessionRun | undefined
}) {
  const cells = [
    { label: 'Documentos', value: String(counts?.total ?? 0), note: 'en el proceso' },
    { label: 'Decididos', value: String(counts?.decided ?? 0), note: 'cierre del motor' },
    { label: 'En revisión', value: String(waiting), note: 'cola humana' },
    {
      label: 'Latencia',
      value: '—',
      note: latestRun ? 'sale con el historial de ejecuciones' : 'aún no hay series',
    },
    {
      label: 'Coste',
      value: '—',
      note: 'OCR y LLM por ejecución, cuando el API lo publique',
    },
  ]

  return (
    <section className="mb-6 grid overflow-hidden rounded-[16px] bg-white ring-1 ring-black/[0.06] sm:grid-cols-5">
      {cells.map((cell) => (
        <div
          key={cell.label}
          className="border-b border-hairline px-3.5 py-3 last:border-0 sm:border-b-0 sm:border-r sm:last:border-r-0"
        >
          <p className="text-[11px] text-muted">{cell.label}</p>
          <p className="mt-2 font-mono text-[22px] tracking-[-0.04em] tabular-nums">{cell.value}</p>
          <p className="mt-0.5 font-mono text-[10px] text-faint">{cell.note}</p>
        </div>
      ))}
    </section>
  )
}

function Runs({
  processId,
  runs,
  documentCount,
}: {
  processId: number
  runs: SessionRun[]
  documentCount: number
}) {
  return (
    <section className="mt-8">
      <div className="mb-3 flex items-end justify-between gap-4">
        <div>
          <h2 className="text-[18px] font-medium tracking-[-0.03em]">Ejecuciones</h2>
          <p className="mt-1 text-[12.5px] text-muted">
            Las de esta sesión. El historial durable llega cuando el backend publique runs.
          </p>
        </div>
        <Link to={paths.instances(processId)} className="text-[12px] text-muted hover:text-ink">
          Historial
        </Link>
      </div>
      <div className="overflow-hidden rounded-[16px] bg-white ring-1 ring-black/[0.06]">
        {runs.length === 0 ? (
          <p className="px-4 py-5 text-[13px] text-muted">
            {documentCount
              ? `${documentCount} documentos en el proceso. Ejecutar abre la cola del lote.`
              : 'Aún no has ejecutado este proceso en esta sesión.'}
          </p>
        ) : (
          <ul className="divide-y divide-hairline">
            {runs.map((item, index) => (
              <li key={`${item.finishedAt.toISOString()}-${index}`}>
                <Link
                  to={paths.instances(processId)}
                  className="flex items-center justify-between gap-4 px-4 py-3 hover:bg-canvas"
                >
                  <div className="min-w-0">
                    <p className="text-[13px] text-ink">
                      {item.decided} decisiones
                    </p>
                    <p className="truncate text-[12px] text-muted">
                      {item.split || 'Sin salidas'}
                    </p>
                  </div>
                  <span className="shrink-0 font-mono text-[11px] text-faint">
                    {item.finishedAt.toLocaleTimeString('es-ES', {
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  )
}

function Pipeline({
  total,
  norm,
  rules,
  decided,
  pending,
}: {
  total: number
  norm: NormRule[]
  rules: Rule[]
  decided: number
  pending: number
}) {
  const checks = norm.reduce((sum, item) => sum + item.reglas.length, 0)
  const compiling = rules.filter((rule) => rule.estado === 'compilando').length
  const active = rules.filter((rule) => rule.estado === 'activa').length

  const stages = [
    { icon: FileText, label: 'Documentos', value: total, note: 'instancias' },
    { icon: BookOpenText, label: 'Norma', value: norm.length, note: `${checks} comprobaciones` },
    {
      icon: Cpu,
      label: 'Compilador',
      value: active,
      note: compiling ? `${compiling} compilando` : 'activas',
    },
    { icon: Play, label: 'Motor', value: decided, note: pending ? `${pending} pendientes` : 'cerrado' },
    { icon: Download, label: 'Exportación', value: decided, note: 'líneas listas' },
  ]

  return (
    <section className="mb-3">
      <p className="mb-3 font-mono text-[11px] tracking-[0.12em] text-faint">
        ESTADO DEL PROCESO
      </p>
      <div className="grid overflow-hidden rounded-[16px] bg-white ring-1 ring-black/[0.06] sm:grid-cols-5">
        {stages.map((stage, index) => (
          <div
            key={stage.label}
            className="relative border-b border-hairline px-3.5 py-3 last:border-0 sm:border-b-0 sm:border-r sm:last:border-r-0"
          >
            <div className="flex items-center gap-1.5 text-[11px] text-muted">
              <stage.icon size={12} strokeWidth={1.6} />
              <span>
                {index + 1} · {stage.label}
              </span>
            </div>
            <p className="mt-2 font-mono text-[22px] tracking-[-0.04em] tabular-nums">
              {stage.value}
            </p>
            <p className="mt-0.5 font-mono text-[10px] text-faint">{stage.note}</p>
          </div>
        ))}
      </div>
    </section>
  )
}

function Split({ counts, instances }: { counts: Counts | undefined; instances: Instance[] }) {
  const cells = useMemo(() => {
    if (!counts) return []
    const outcomes = Object.entries(counts.byOutcome).sort(([a], [b]) => a.localeCompare(b))
    const blocking = [
      { label: 'REVISION', value: counts.review },
      { label: 'PENDIENTE', value: counts.pending },
    ].filter((cell) => cell.value > 0)
    return [...outcomes.map(([label, value]) => ({ label, value })), ...blocking]
  }, [counts])

  return (
    <section className="mt-8 overflow-hidden rounded-[16px] bg-white ring-1 ring-black/[0.06]">
      <div className="flex items-start justify-between gap-4 px-5 py-4">
        <div>
          <h2 className="text-[18px] font-medium tracking-[-0.03em]">Salida de decisiones</h2>
          <p className="mt-1 text-[12.5px] text-muted">
            Distribución actual del lote. Cada marca representa un documento.
          </p>
        </div>
        <span className="font-mono text-[12px] text-muted">{counts?.total ?? 0} total</span>
      </div>
      {cells.length === 0 ? (
        <p className="px-5 pb-5 text-[13px] text-muted">
          Aún no hay documentos. Ejecutar y suelta el lote.
        </p>
      ) : (
        <div className="grid gap-px bg-black/[0.05] md:grid-cols-[minmax(0,1fr)_1.4fr]">
          <div className="bg-white px-5 py-4">
            <div className="space-y-4">
              {cells.map((cell) => (
                <div key={cell.label} className="flex items-center gap-3">
                  <span
                    className={cn(
                      'h-2.5 w-2.5 shrink-0 rounded-[3px]',
                      cell.label === 'PAGAR' || cell.label === 'APROBAR'
                        ? 'bg-pagar'
                        : cell.label === 'NO_PAGAR' || cell.label === 'RECHAZAR'
                          ? 'bg-nopagar'
                          : cell.label === 'PENDIENTE'
                            ? 'bg-faint/50'
                            : 'bg-escalar',
                    )}
                  />
                  <span className="min-w-0 flex-1 text-[12.5px] text-muted">
                    {cell.label.replaceAll('_', ' ')}
                  </span>
                  <span className="font-mono text-[18px] tracking-[-0.04em] tabular-nums">
                    {cell.value}
                  </span>
                </div>
              ))}
            </div>
          </div>
          <div className="flex min-h-[150px] items-center bg-white px-5 py-5">
            <div className="flex w-full flex-wrap content-center gap-1">
              {instances.map((item) => (
                <span
                  key={item.id}
                  title={`${item.nombre}: ${item.decision ?? item.estado}`}
                  className={cn(
                    'h-3 w-3 rounded-[3px] transition-transform hover:scale-125',
                    item.decision === 'PAGAR' || item.decision === 'APROBAR'
                      ? 'bg-pagar'
                      : item.decision === 'NO_PAGAR' || item.decision === 'RECHAZAR'
                        ? 'bg-nopagar'
                        : item.decision
                          ? 'bg-escalar'
                          : 'bg-faint/40',
                  )}
                />
              ))}
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
