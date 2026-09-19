import { useMemo, useState } from 'react'
import { Link, useParams } from 'react-router'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { BookOpenText, Cpu, Download, FileText, Play } from 'lucide-react'
import { api } from '../api/client'
import { keys } from '../api/queries'
import { ExportButton } from '../components/process/ExportButton'
import { Button } from '../components/shell/Controls'
import { ErrorNotice } from '../components/shell/Notice'
import { Topbar } from '../components/shell/Topbar'
import { NestedCard, PageIntro, PreviewWell } from '../components/shell/Well'
import { cn } from '../lib/cn'
import { tone } from '../lib/status'
import { paths } from '../lib/paths'
import type { Instance, NormRule, Rule } from '../api/contracts'
import { byPriority, countsOf, waitingOnPerson, type Counts } from '../lib/process'

export function Process() {
  const processId = Number(useParams().processId)
  const queryClient = useQueryClient()
  const [summary, setSummary] = useState<string | null>(null)

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
  })
  const norm = useQuery({
    queryKey: keys.norm(processId),
    queryFn: () => api.listNormRules(processId),
  })

  const run = useMutation({
    mutationFn: () => api.run(processId),
    onSuccess: (data) => {
      const split = Object.entries(data.por_decision)
        .map(([name, value]) => `${value} ${name}`)
        .join(' · ')
      setSummary(`${data.decididas} decididas${split ? ` · ${split}` : ''}`)
      void queryClient.invalidateQueries()
    },
  })

  const active = rules.data?.filter((rule) => rule.estado === 'activa').length ?? 0
  const drafts = rules.data?.filter((rule) => rule.estado === 'borrador').length ?? 0
  const waiting = waitingOnPerson(process.data, counts.data)

  if (process.isError) {
    return (
      <>
        <Topbar crumbs={[{ label: 'Procesos', to: paths.processes }, { label: String(processId) }]} />
        <div className="px-8 py-6">
          <ErrorNotice error={process.error} />
        </div>
      </>
    )
  }

  return (
    <>
      <Topbar
        crumbs={[{ label: 'Procesos', to: paths.processes }, { label: process.data?.nombre ?? '…' }]}
        actions={
          <>
            <Button
              tone="soft"
              onClick={() => run.mutate()}
              disabled={run.isPending}
              title="Ejecuta todas las reglas activas sobre las instancias pendientes"
            >
              <Play size={12} strokeWidth={2} />
              {run.isPending ? 'Ejecutando…' : 'Ejecutar'}
            </Button>
            <ExportButton processId={processId} />
          </>
        }
      />

      <div className="min-h-0 flex-1 overflow-y-auto px-8 pb-10 pt-4">
        <PageIntro
          kicker="Proceso"
          title={process.data?.nombre ?? '…'}
          description={process.data?.descripcion}
        />

        {run.isError ? (
          <div className="mb-4 max-w-2xl">
            <ErrorNotice error={run.error} />
          </div>
        ) : null}
        {summary ? <p className="mb-4 text-[13px] text-muted">{summary}</p> : null}

        <Pipeline
          total={counts.data?.total ?? 0}
          norm={norm.data ?? []}
          rules={rules.data ?? []}
          decided={counts.data?.decided ?? 0}
          pending={(counts.data?.pending ?? 0) + (counts.data?.review ?? 0)}
        />

        <Split counts={counts.data} instances={instances.data ?? []} />

        <section className="mt-10 grid gap-3 lg:grid-cols-2">
          <Shortcut
            to={paths.rules(processId)}
            title="Reglas"
            detail={`${active} activas${drafts ? ` · ${drafts} en borrador` : ''}`}
            foot="Norma → comprobaciones → tester ciego → código validado."
          />
          <Shortcut
            to={paths.queue(processId)}
            title="Cola"
            detail={`${waiting} esperando a una persona`}
            foot="Lo que las reglas no cierran. El asistente propone decisión y regla."
          />
          <Shortcut
            to={paths.instances(processId)}
            title="Instancias"
            detail={`${counts.data?.total ?? 0} en el proceso`}
            foot="Consola: documento, símbolos con origen y traza paso a paso."
          />
          <Shortcut
            to={paths.audit(processId)}
            title="Auditoría"
            detail="Hallazgos"
            foot="Qué decisiones pasadas contradice la norma de hoy."
          />
        </section>

        <section className="mt-10 grid gap-3 lg:grid-cols-2">
          <div>
            <p className="mb-3 font-mono text-[11px] tracking-[0.12em] text-faint">
              TIPOS DE DECISIÓN
            </p>
            <NestedCard label="gana la mayor prioridad si saltan varias reglas">
              <ul className="divide-y divide-hairline">
                {byPriority(process.data?.tipos_decision ?? []).map((outcome) => (
                  <li
                    key={outcome.nombre}
                    className="flex items-center gap-2 px-3.5 py-2 text-[12.5px]"
                  >
                    <span className="w-4 shrink-0 font-mono text-[11px] text-faint">
                      {outcome.prioridad}
                    </span>
                    <span
                      className={cn(
                        'rounded-full px-2 py-0.5 font-mono text-[10px]',
                        tone(outcome.nombre),
                      )}
                    >
                      {outcome.nombre.replaceAll('_', ' ')}
                    </span>
                    <span className="text-muted">
                      {[
                        outcome.por_defecto ? 'por defecto' : null,
                        outcome.requiere_persona ? 'requiere persona' : null,
                      ]
                        .filter(Boolean)
                        .join(' · ')}
                    </span>
                  </li>
                ))}
              </ul>
            </NestedCard>
          </div>

          <div>
            <p className="mb-3 font-mono text-[11px] tracking-[0.12em] text-faint">SÍMBOLOS</p>
            <NestedCard label={`${process.data?.simbolos.length ?? 0} símbolos del proceso`}>
              <ul className="flex flex-wrap gap-1.5 px-3.5 py-3">
                {process.data?.simbolos.map((symbol) => (
                  <li
                    key={symbol.nombre}
                    title={symbol.descripcion}
                    className="rounded-full bg-well px-2.5 py-1 font-mono text-[11px] text-ink"
                  >
                    {symbol.nombre}
                    <span className="ml-1.5 text-faint">{symbol.tipo}</span>
                  </li>
                ))}
              </ul>
            </NestedCard>
          </div>
        </section>
      </div>
    </>
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
              <span>{index + 1} · {stage.label}</span>
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
    <PreviewWell name={`${counts?.total ?? 0} instancias · cada punto es una decisión`}>
      {cells.length === 0 ? (
        <p className="text-[13px] text-muted">
          Aún no hay instancias. Sube ficheros desde Fuentes y pulsa Ejecutar.
        </p>
      ) : (
        <div className="w-full">
          <div className="mb-5 flex flex-wrap items-end justify-center gap-6">
            {cells.map((cell) => (
              <div key={cell.label} className="flex flex-col items-center">
                <span className="font-mono text-[30px] leading-none tracking-[-0.04em] tabular-nums">
                  {cell.value}
                </span>
                <span
                  className={cn(
                    'mt-2 rounded-full px-2 py-0.5 font-mono text-[10px] tracking-[0.04em]',
                    tone(cell.label),
                  )}
                >
                  {cell.label.replaceAll('_', ' ')}
                </span>
              </div>
            ))}
          </div>
          <div className="mx-auto flex max-w-[620px] flex-wrap justify-center gap-[3px]">
            {instances.map((item) => (
              <span
                key={item.id}
                title={`${item.nombre} · ${item.decision ?? item.estado}`}
                className={cn(
                  'h-[7px] w-[7px] rounded-[2px]',
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
      )}
    </PreviewWell>
  )
}

function Shortcut({
  to,
  title,
  detail,
  foot,
}: {
  to: string
  title: string
  detail: string
  foot: string
}) {
  return (
    <Link
      to={to}
      className="block rounded-[16px] bg-white px-4 py-3.5 ring-1 ring-black/[0.06] hover:bg-canvas"
    >
      <div className="flex items-baseline justify-between gap-3">
        <span className="text-[15px] font-medium">{title}</span>
        <span className="font-mono text-[11px] text-muted">{detail}</span>
      </div>
      <p className="mt-1 text-[12.5px] text-muted">{foot}</p>
    </Link>
  )
}
