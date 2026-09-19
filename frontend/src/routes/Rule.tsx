import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, Hammer, X } from 'lucide-react'
import { api } from '../api/client'
import { keys } from '../api/queries'
import type { Impact, ImpactChange, RuleDetail, RuleReport } from '../api/contracts'
import { ProcessScreen } from '../components/process/ProcessScreen'
import { Button } from '../components/shell/Controls'
import { ErrorNotice, Notice } from '../components/shell/Notice'
import { StatusBadge } from '../components/shell/StatusBadge'
import { NestedCard, PageIntro } from '../components/shell/Well'
import { t } from '../i18n'
import { JsonHighlight, PythonHighlight } from '../lib/jsonHighlight'
import { cn } from '../lib/cn'
import { paths } from '../lib/paths'
import { ruleLabel } from '../lib/process'
import { useSession } from '../state/session'

export function Rule() {
  const processId = Number(useParams().processId)
  const ruleId = Number(useParams().ruleId)
  const queryClient = useQueryClient()
  const { isManager } = useSession()

  const process = useQuery({
    queryKey: keys.process(processId),
    queryFn: () => api.getProcess(processId),
  })
  const rule = useQuery({
    queryKey: keys.rule(ruleId),
    queryFn: () => api.getRule(ruleId),
    refetchInterval: (query) =>
      query.state.data?.status === 'compiling' ? 1_500 : false,
  })

  const data = rule.data
  const report = data?.report as RuleReport | null | undefined
  const compiled = Boolean(report || data?.code)
  const valid = Boolean(report?.valid)
  const isActive = data?.status === 'active'
  const isCompiling = data?.status === 'compiling'

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

  const code = data?.code
  const tests = data?.tests
  const conflicts = impact.data?.conflicts ?? []
  const staged = activate.isSuccess || retire.isSuccess

  return (
    <ProcessScreen
      processId={processId}
      crumbs={[
        { label: 'Procesos', to: paths.processes },
        { label: process.data?.name ?? '…', to: paths.process(processId) },
        { label: 'Definición', to: paths.definition(processId) },
        { label: `Regla ${ruleId}` },
      ]}
      actions={
        <>
          <Button
            onClick={() => compile.mutate()}
            disabled={
              compile.isPending ||
              isCompiling ||
              !data ||
              !['draft', 'blocked'].includes(data.status)
            }
          >
            <Hammer size={12} strokeWidth={2} />
            {compile.isPending || isCompiling
              ? 'Compilando…'
              : compiled
                ? 'Recompilar'
                : 'Compilar'}
          </Button>
          {isActive ? (
            <Button
              tone="danger"
              onClick={() => retire.mutate()}
              disabled={!isManager || retire.isPending}
              title={isManager ? undefined : 'Solo un responsable puede quitar reglas de la versión'}
            >
              <X size={12} strokeWidth={2} />
              {retire.isPending ? 'Quitando…' : 'Quitar de la versión'}
            </Button>
          ) : (
            <Button
              tone="primary"
              onClick={() => activate.mutate()}
              disabled={!isManager || !valid || activate.isPending}
              title={isManager ? undefined : 'Solo un responsable puede añadir reglas a la versión'}
            >
              <Check size={12} strokeWidth={2} />
              {activate.isPending ? 'Añadiendo…' : 'Añadir a la versión'}
            </Button>
          )}
        </>
      }
    >

      <div className="min-h-0 flex-1 overflow-y-auto px-6 pb-10 pt-4">
        {rule.isError ? <ErrorNotice error={rule.error} /> : null}

        <PageIntro
          kicker={`Regla ${ruleId} · ${data ? t(`ruleType.${data.type}`) : '…'}`}
          title={data ? ruleLabel(data) : '…'}
        />
        {data?.summary?.trim() ? (
          <p className="-mt-6 mb-8 max-w-2xl text-[14px] leading-6 text-muted">{data.text}</p>
        ) : null}

        <div className="-mt-4 mb-6 flex flex-wrap items-center gap-2">
          {data ? <StatusBadge value={data.status}>{t(`ruleStatus.${data.status}`)}</StatusBadge> : null}
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
              Añadir y quitar reglas de la versión es cosa de un responsable. Cambia de usuario en{' '}
              <Link to={paths.settings} className="underline">
                Ajustes
              </Link>
              .
            </Notice>
          ) : null}

          {activate.isError ? <ErrorNotice error={activate.error} /> : null}
          {compile.isError ? <ErrorNotice error={compile.error} /> : null}
          {retire.isError ? <ErrorNotice error={retire.error} /> : null}
          {staged ? (
            <Notice
              title="Queda en el borrador. Publica una versión para que se aplique"
              action={
                <Link
                  to={`${paths.panel(processId)}?publicar=1`}
                  className="text-[12px] text-muted hover:text-ink"
                >
                  Publicar
                </Link>
              }
            />
          ) : null}

          {compile.isPending || isCompiling ? <Compiling /> : null}

          {conflicts.length > 0 ? (
            <Notice
              tone="warning"
              title={`${conflicts.length} decisiones que tomó una persona cambiarían`}
            >
              El cambio no entra hasta resolverlo. Ni la regla ni la persona ganan de oficio: abre
              cada instancia y decide cuál manda.
            </Notice>
          ) : null}

          {!compiled && !compile.isPending && !isCompiling ? (
            <Notice title="Sin compilar">
              Al guardar, un tester ciego escribe los casos y un compilador autónomo escribe el
              código contra ellos. También puedes pulsar <strong>Compilar</strong> para reintentarlo.
            </Notice>
          ) : null}

          {compiled && !valid ? (
            <Notice tone="error" title="La validación no salió limpia">
              El código no pasa algún caso del tester, o la regla pide datos que el proceso no
              tiene. La versión activa anterior sigue funcionando.
            </Notice>
          ) : null}
        </div>

        {report ? <Report report={report} /> : null}

        {impact.data ? <ImpactSection impact={impact.data} retiring={isActive} /> : null}

        <section className="mt-8">
          <p className="mb-3 font-mono text-[11px] tracking-[0.12em] text-faint">
            CÓDIGO Y CASOS DEL TESTER
          </p>
          <div className="grid gap-3 lg:grid-cols-2">
            <NestedCard label="evaluate.py · compilador">
              {code ? (
                <PythonHighlight code={code} className="h-[420px]" />
              ) : (
                <p className="px-3.5 py-6 text-[13px] text-muted">Todavía no hay código.</p>
              )}
            </NestedCard>
            <NestedCard label={`tester ciego · ${tests?.length ?? 0} casos`}>
              {tests?.length ? (
                <JsonHighlight value={tests} className="h-[420px]" />
              ) : (
                <p className="px-3.5 py-6 text-[13px] text-muted">Todavía no hay tests.</p>
              )}
            </NestedCard>
          </div>
        </section>
      </div>
    </ProcessScreen>
  )
}

/** Background compiler progress. Showing the clock beats showing a spinner. */
function Compiling() {
  const [seconds, setSeconds] = useState(0)
  useEffect(() => {
    const id = window.setInterval(() => setSeconds((value) => value + 1), 1000)
    return () => window.clearInterval(id)
  }, [])

  return (
    <Notice title={`Compilando · ${seconds} s`}>
      El tester ciego escribe los casos sin ver el código. El compilador escribe y corrige la
      función hasta pasarlos; si discuten un caso, el tester lo revisa sin adoptar la respuesta del
      compilador.
      <div className="mt-2 h-[3px] w-full overflow-hidden rounded-full bg-rule">
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
  const failing = tests.filter((test) => !test.passed)
  const needsData = report.needs_data

  return (
    <section className="mt-8">
      <p className="mb-3 font-mono text-[11px] tracking-[0.12em] text-faint">VALIDACIÓN</p>
      <div className="grid gap-3 sm:grid-cols-3">
        <Score
          title="Casos del tester"
          value={`${tests.length - failing.length}/${tests.length}`}
          good={tests.length > 0 && failing.length === 0}
          foot="Casos que pasa el código generado."
        />
        <Score
          title="Intentos"
          value={String(report.attempts ?? '—')}
          good={Boolean(report.valid)}
          foot={`${report.reviews?.length ?? 0} revisiones del tester.`}
        />
        <Score
          title="Se puede añadir"
          value={report.valid ? 'sí' : 'no'}
          good={Boolean(report.valid)}
          foot="Todos los casos pasan y no faltan datos."
        />
      </div>

      {needsData ? (
        <div className="mt-3">
          <Notice tone="warning" title="Esta regla pide datos que el proceso no tiene">
            {needsData.missing?.length ? (
              <span className="font-mono">{needsData.missing.join(' · ')}</span>
            ) : null}{' '}
            {needsData.explanation}
          </Notice>
        </div>
      ) : null}

      {tests.length > 0 ? (
        <div className="mt-3">
          <NestedCard label="caso · esperado · resultado">
            <ul className="divide-y divide-hairline">
              {[...failing, ...tests.filter((test) => test.passed)].slice(0, 12).map((test, index) => (
                <Case key={`${test.name}-${index}`} test={test} />
              ))}
            </ul>
          </NestedCard>
        </div>
      ) : null}

      {report.discrepancies?.length ? (
        <div className="mt-3">
          <Notice tone="error" title={`${report.discrepancies.length} discrepancias`}>
            <ul className="mt-1 space-y-1">
              {report.discrepancies.slice(0, 8).map((line) => (
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
        {retiring ? 'QUÉ CAMBIARÍA AL QUITARLA' : 'QUÉ CAMBIARÍA AL AÑADIRLA'}
      </p>
      <div className="grid gap-3 lg:grid-cols-3">
        <NestedCard label="sin cambio">
          <p className="px-3.5 py-3 font-mono text-[28px] leading-none tracking-[-0.04em]">
            {impact.unchanged}
          </p>
        </NestedCard>
        <Changes title="decisiones del motor que cambian" rows={impact.changes} />
        <Changes title="contradicen a una persona" rows={impact.conflicts} danger />
      </div>
      <p className="mt-2 text-[12px] text-faint">
        La auditoría reejecuta las reglas sobre los símbolos ya guardados. No relee un PDF ni
        llama al ERP, y nunca cambia una decisión pasada: solo dice cuál sería hoy.
      </p>
    </section>
  )
}

type ReportTest = NonNullable<RuleReport['tests']>[number]

function Case({ test }: { test: ReportTest }) {
  return (
    <li className="flex items-baseline gap-3 px-3.5 py-2">
      <span className="min-w-0 flex-1 truncate text-[12.5px]">{test.name}</span>
      <span className="shrink-0 font-mono text-[11px] text-muted">
        {test.expected ? 'salta' : 'no salta'}
      </span>
      <span
        className={cn(
          'shrink-0 rounded-full px-1.5 py-0.5 font-mono text-[10px]',
          test.passed ? 'bg-pagar-soft text-pagar' : 'bg-nopagar-soft text-nopagar',
        )}
        title={`Resultado: ${test.got}`}
      >
        {test.passed ? 'pasa' : test.got}
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
  rows: ImpactChange[]
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
            key={row.instance_id}
            className="flex items-baseline justify-between gap-2 py-0.5 font-mono text-[11px]"
          >
            <span className="truncate text-muted" title={row.reason}>
              {row.name}
            </span>
            <span className="shrink-0 text-ink">
              {row.before} → {row.after}
            </span>
          </li>
        ))}
      </ul>
    </NestedCard>
  )
}
