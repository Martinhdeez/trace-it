import { useEffect, useRef, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, Hammer, X } from 'lucide-react'
import { api } from '../api/client'
import { keys } from '../api/queries'
import type { AuditChange, CrossTest, Impact, RuleDetail, RuleReport } from '../api/contracts'
import { Button, Segmented } from '../components/shell/Controls'
import { ErrorNotice, Notice } from '../components/shell/Notice'
import { StatusBadge } from '../components/shell/StatusBadge'
import { Topbar } from '../components/shell/Topbar'
import { NestedCard, PageIntro } from '../components/shell/Well'
import { JsonHighlight } from '../lib/jsonHighlight'
import { cn } from '../lib/cn'
import { paths } from '../lib/paths'
import { useSession } from '../state/session'

export function Rule() {
  const processId = Number(useParams().processId)
  const ruleId = Number(useParams().ruleId)
  const [params, setParams] = useSearchParams()
  const queryClient = useQueryClient()
  const { isManager } = useSession()
  const [view, setView] = useState<'a' | 'b'>('a')

  const process = useQuery({
    queryKey: keys.process(processId),
    queryFn: () => api.getProcess(processId),
  })
  const rule = useQuery({ queryKey: keys.rule(ruleId), queryFn: () => api.getRule(ruleId) })

  const data = rule.data
  const report = data?.informe
  const compiled = Boolean(report)
  const valid = Boolean(report?.valida)
  const isActive = data?.estado === 'activa'

  // Activating and retiring are the same question asked of a different rule set,
  // so the impact is worth seeing before either.
  const impact = useQuery({
    queryKey: [...keys.rule(ruleId), 'impact'],
    queryFn: () => api.ruleImpact(ruleId),
    enabled: Boolean(data) && (valid || isActive),
  })

  const refresh = (updated: RuleDetail) => {
    queryClient.setQueryData(keys.rule(ruleId), updated)
    void queryClient.invalidateQueries({ queryKey: ['rules'] })
    void queryClient.invalidateQueries({ queryKey: ['rule', ruleId, 'impact'] })
    void queryClient.invalidateQueries({ queryKey: ['instances'] })
    void queryClient.invalidateQueries({ queryKey: ['findings'] })
  }

  const compile = useMutation({ mutationFn: () => api.compileRule(ruleId), onSuccess: refresh })
  const activate = useMutation({ mutationFn: () => api.activateRule(ruleId), onSuccess: refresh })
  const retire = useMutation({ mutationFn: () => api.retireRule(ruleId), onSuccess: refresh })

  // Coming from "crear y compilar": start the two agents without a second click.
  const launched = useRef(false)
  const autoCompile = params.get('compile') === '1'
  useEffect(() => {
    if (!autoCompile || launched.current || !data) return
    launched.current = true
    params.delete('compile')
    setParams(params, { replace: true })
    if (data.estado === 'borrador' && !data.informe) compile.mutate()
  }, [autoCompile, data, compile, params, setParams])

  const code = view === 'a' ? data?.codigo_a : data?.codigo_b
  const tests = view === 'a' ? data?.tests_a : data?.tests_b
  const conflicts = impact.data?.conflictos ?? []

  return (
    <>
      <Topbar
        crumbs={[
          { label: process.data?.nombre ?? '…', to: paths.process(processId) },
          { label: 'Reglas', to: paths.rules(processId) },
          { label: `Regla ${ruleId}` },
        ]}
        actions={
          <>
            <Button
              onClick={() => compile.mutate()}
              disabled={compile.isPending || data?.estado !== 'borrador'}
            >
              <Hammer size={12} strokeWidth={2} />
              {compile.isPending ? 'Compilando…' : compiled ? 'Recompilar' : 'Compilar'}
            </Button>
            {isActive ? (
              <Button
                tone="danger"
                onClick={() => retire.mutate()}
                disabled={!isManager || retire.isPending}
                title={isManager ? undefined : 'Solo un responsable puede retirar reglas'}
              >
                <X size={12} strokeWidth={2} />
                {retire.isPending ? 'Retirando…' : 'Retirar'}
              </Button>
            ) : (
              <Button
                tone="primary"
                onClick={() => activate.mutate()}
                disabled={!isManager || !valid || activate.isPending}
                title={isManager ? undefined : 'Solo un responsable puede activar reglas'}
              >
                <Check size={12} strokeWidth={2} />
                {activate.isPending ? 'Activando…' : 'Activar'}
              </Button>
            )}
          </>
        }
      />

      <div className="min-h-0 flex-1 overflow-y-auto px-8 pb-10 pt-4">
        {rule.isError ? <ErrorNotice error={rule.error} /> : null}

        <PageIntro kicker={`Regla ${ruleId} · ${data?.tipo ?? '…'}`} title={data?.texto ?? '…'} />

        <div className="-mt-4 mb-6 flex flex-wrap items-center gap-2">
          {data ? <StatusBadge value={data.estado} /> : null}
          {data ? (
            <span className="flex items-center gap-1.5 text-[12px] text-muted">
              Si salta: <StatusBadge value={data.decision} />
            </span>
          ) : null}
          {data?.hash ? (
            <span className="font-mono text-[11px] text-faint">hash {data.hash.slice(0, 16)}</span>
          ) : null}
        </div>

        <div className="space-y-3">
          {!isManager ? (
            <Notice title="Entras como operador">
              Activar y retirar reglas es cosa de un responsable. Cambia de usuario en{' '}
              <Link to={paths.settings} className="underline">
                Ajustes
              </Link>
              .
            </Notice>
          ) : null}

          {activate.isError ? <ErrorNotice error={activate.error} /> : null}
          {compile.isError ? <ErrorNotice error={compile.error} /> : null}
          {retire.isError ? <ErrorNotice error={retire.error} /> : null}

          {compile.isPending ? <Compiling /> : null}

          {conflicts.length > 0 ? (
            <Notice
              tone="warning"
              title={`${conflicts.length} decisiones que tomó una persona cambiarían`}
            >
              El cambio no entra hasta resolverlo. Ni la regla ni la persona ganan de oficio: abre
              cada instancia y decide cuál manda.
            </Notice>
          ) : null}

          {!compiled && !compile.isPending ? (
            <Notice title="Sin compilar">
              Pulsa <strong>Compilar</strong>: dos agentes escriben, cada uno por su lado, el código
              y los tests de esta regla. Hasta que pasen los tests cruzados no se puede activar.
            </Notice>
          ) : null}

          {compiled && !valid ? (
            <Notice tone="error" title="La validación no salió limpia">
              Los dos códigos no coinciden en algún test o en alguna instancia del histórico. La
              regla se queda en borrador. Normalmente se arregla aclarando el texto y recompilando.
            </Notice>
          ) : null}
        </div>

        {report ? <Report report={report} /> : null}

        {impact.data ? <ImpactSection impact={impact.data} retiring={isActive} /> : null}

        <section className="mt-8">
          <div className="mb-3 flex items-center justify-between">
            <p className="font-mono text-[11px] tracking-[0.12em] text-faint">CÓDIGO GENERADO</p>
            <Segmented
              value={view}
              onChange={setView}
              options={[
                { value: 'a', label: 'Agente A' },
                { value: 'b', label: 'Agente B' },
              ]}
            />
          </div>
          <div className="grid gap-3 lg:grid-cols-2">
            <NestedCard label={`codigo_${view}.py`}>
              {code ? (
                <pre className="max-h-[420px] overflow-auto bg-[#161615] px-3 py-3 font-mono text-[12px] leading-5 text-[#eceae4]">
                  {code}
                </pre>
              ) : (
                <p className="px-3.5 py-6 text-[13px] text-muted">Todavía no hay código.</p>
              )}
            </NestedCard>
            <NestedCard label={`tests_${view} · ${tests?.length ?? 0}`}>
              {tests?.length ? (
                <JsonHighlight value={tests} />
              ) : (
                <p className="px-3.5 py-6 text-[13px] text-muted">Todavía no hay tests.</p>
              )}
            </NestedCard>
          </div>
        </section>
      </div>
    </>
  )
}

/** Two agents, two LLM round trips. Showing the clock beats showing a spinner. */
function Compiling() {
  const [seconds, setSeconds] = useState(0)
  useEffect(() => {
    const id = window.setInterval(() => setSeconds((value) => value + 1), 1000)
    return () => window.clearInterval(id)
  }, [])

  return (
    <Notice title={`Compilando · ${seconds} s`}>
      Los agentes A y B escriben a la vez, sin verse. Después se pasan todos los tests por los dos
      códigos y los dos corren el histórico entero. Suele tardar entre 30 y 60 segundos.
      <div className="mt-2 h-[3px] w-full overflow-hidden rounded-full bg-black/[0.06]">
        <div
          className="h-full rounded-full bg-ink/70 transition-[width] duration-1000 ease-linear"
          style={{ width: `${Math.min(95, seconds * 2)}%` }}
        />
      </div>
    </Notice>
  )
}

function Report({ report }: { report: RuleReport }) {
  const tests = report.tests ?? []
  const failing = tests.filter((test) => !test.pasa)
  const history = report.historico

  return (
    <section className="mt-8">
      <p className="mb-3 font-mono text-[11px] tracking-[0.12em] text-faint">VALIDACIÓN</p>
      <div className="grid gap-3 sm:grid-cols-3">
        <Score
          title="Tests cruzados"
          value={`${tests.length - failing.length}/${tests.length}`}
          good={tests.length > 0 && failing.length === 0}
          foot="Cada test de A y de B, por los dos códigos."
        />
        <Score
          title="Histórico"
          value={history ? `${history.coinciden}/${history.instancias}` : '—'}
          good={Boolean(history) && history!.coinciden === history!.instancias}
          foot="Instancias en que A y B dicen lo mismo."
        />
        <Score
          title="Se puede activar"
          value={report.valida ? 'sí' : 'no'}
          good={Boolean(report.valida)}
          foot="Sin un solo desacuerdo entre los dos códigos."
        />
      </div>

      {tests.length > 0 ? (
        <div className="mt-3">
          <NestedCard label="caso · esperado · A y B">
            <ul className="divide-y divide-hairline">
              {[...failing, ...tests.filter((test) => test.pasa)].slice(0, 12).map((test, index) => (
                <Case key={`${test.autor}-${test.nombre}-${index}`} test={test} />
              ))}
            </ul>
          </NestedCard>
        </div>
      ) : null}

      {report.discrepancias?.length ? (
        <div className="mt-3">
          <Notice tone="error" title={`${report.discrepancias.length} discrepancias`}>
            <ul className="mt-1 space-y-1">
              {report.discrepancias.slice(0, 8).map((line) => (
                <li key={line} className="font-mono text-[11px] leading-5">
                  {line}
                </li>
              ))}
            </ul>
          </Notice>
        </div>
      ) : null}
    </section>
  )
}

function ImpactSection({ impact, retiring }: { impact: Impact; retiring: boolean }) {
  return (
    <section className="mt-8">
      <p className="mb-3 font-mono text-[11px] tracking-[0.12em] text-faint">
        {retiring ? 'QUÉ CAMBIARÍA AL RETIRARLA' : 'QUÉ CAMBIARÍA AL ACTIVARLA'}
      </p>
      <div className="grid gap-3 lg:grid-cols-3">
        <NestedCard label="sin cambio">
          <p className="px-3.5 py-3 font-mono text-[28px] leading-none tracking-[-0.04em]">
            {impact.sin_cambio}
          </p>
        </NestedCard>
        <Changes title="decisiones del motor que cambian" rows={impact.cambios} />
        <Changes title="contradicen a una persona" rows={impact.conflictos} danger />
      </div>
      <p className="mt-2 text-[12px] text-faint">
        La auditoría reejecuta las reglas sobre los símbolos ya guardados. No relee un PDF ni
        llama al ERP, y nunca cambia una decisión pasada: solo dice cuál sería hoy.
      </p>
    </section>
  )
}

function Case({ test }: { test: CrossTest }) {
  return (
    <li className="flex items-baseline gap-3 px-3.5 py-2">
      <span className="w-4 shrink-0 font-mono text-[11px] text-faint">{test.autor}</span>
      <span className="min-w-0 flex-1 truncate text-[12.5px]">{test.nombre}</span>
      <span className="shrink-0 font-mono text-[11px] text-muted">
        {test.esperado ? 'salta' : 'no salta'}
      </span>
      <span
        className={cn(
          'shrink-0 rounded-full px-1.5 py-0.5 font-mono text-[10px]',
          test.pasa ? 'bg-pagar-soft text-pagar' : 'bg-nopagar-soft text-nopagar',
        )}
        title={`A: ${test.a} · B: ${test.b}`}
      >
        {test.pasa ? 'A = B' : `A ${test.a} / B ${test.b}`}
      </span>
    </li>
  )
}

function Score({
  title,
  value,
  good,
  foot,
}: {
  title: string
  value: string
  good: boolean
  foot: string
}) {
  return (
    <div
      className={cn(
        'rounded-[14px] px-3.5 py-3 ring-1',
        good ? 'bg-pagar-soft ring-pagar/15' : 'bg-nopagar-soft ring-nopagar/15',
      )}
    >
      <p className="text-[12px] text-muted">{title}</p>
      <p
        className={cn(
          'mt-1 font-mono text-[20px] tracking-[-0.03em]',
          good ? 'text-pagar' : 'text-nopagar',
        )}
      >
        {value}
      </p>
      <p className="mt-1 text-[11px] text-faint">{foot}</p>
    </div>
  )
}

function Changes({
  title,
  rows,
  danger,
}: {
  title: string
  rows: AuditChange[]
  danger?: boolean
}) {
  return (
    <NestedCard label={title}>
      <p
        className={cn(
          'px-3.5 pt-3 font-mono text-[28px] leading-none tracking-[-0.04em]',
          danger && rows.length > 0 && 'text-nopagar',
        )}
      >
        {rows.length}
      </p>
      <ul className="max-h-40 overflow-y-auto px-3.5 py-2">
        {rows.slice(0, 20).map((row) => (
          <li
            key={row.instancia_id}
            className="flex items-baseline justify-between gap-2 py-0.5 font-mono text-[11px]"
          >
            <span className="truncate text-muted" title={row.motivo}>
              {row.nombre}
            </span>
            <span className="shrink-0 text-ink">
              {row.antes} → {row.despues}
            </span>
          </li>
        ))}
      </ul>
    </NestedCard>
  )
}
