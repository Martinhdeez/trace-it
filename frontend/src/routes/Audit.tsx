import { useParams } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import { keys } from '../api/queries'
import { RuleSteps } from '../components/process/RuleSteps'
import { DataTable } from '../components/shell/DataTable'
import { Empty, ErrorNotice } from '../components/shell/Notice'
import { Topbar } from '../components/shell/Topbar'
import { NestedCard, PageIntro } from '../components/shell/Well'
import { formatRunDate } from '../lib/format'
import { paths } from '../lib/paths'

/**
 * F7. The past is never rewritten: activating a rule only tells you which old
 * decisions would come out different, so someone can go and act on it.
 */
export function Audit() {
  const processId = Number(useParams().processId)

  const process = useQuery({
    queryKey: keys.process(processId),
    queryFn: () => api.getProcess(processId),
  })
  const findings = useQuery({
    queryKey: keys.findings(processId),
    queryFn: () => api.listFindings(processId),
  })
  const rules = useQuery({
    queryKey: keys.rules(processId, 'activa'),
    queryFn: () => api.listRules(processId, 'activa'),
  })

  const active = rules.data ?? []
  const ruleText = (id: number | null) =>
    (id && rules.data?.find((rule) => rule.id === id)?.texto) || '—'

  return (
    <>
      <Topbar
        crumbs={[
          { label: process.data?.nombre ?? '…', to: paths.process(processId) },
          { label: 'Auditoría' },
        ]}
      />

      <div className="min-h-0 flex-1 overflow-y-auto px-8 pb-10 pt-4">
        <PageIntro
          kicker="Auditoría"
          title="Qué contradice la norma de hoy"
          description="Cada vez que entra o se retira una regla, se reejecuta sobre los símbolos ya guardados de cada decisión. Nunca cambia el pasado: deja constancia de lo que se decidió mal para que alguien lo reclame fuera del sistema."
        />

        {findings.isError ? <ErrorNotice error={findings.error} /> : null}

        <section className="mb-8">
          <p className="mb-3 font-mono text-[11px] tracking-[0.12em] text-faint">
            HALLAZGOS · {findings.data?.length ?? 0}
          </p>
          <NestedCard label="decisiones pasadas que la norma de hoy contradice">
            {findings.data?.length ? (
              <DataTable
                framed={false}
                rows={findings.data.map((finding) => ({ ...finding, id: String(finding.id) }))}
                columns={[
                  {
                    key: 'tipo',
                    header: 'Tipo',
                    width: '12rem',
                    render: (row) => (
                      <span className="text-[12px] text-escalar">
                        {row.tipo.replaceAll('_', ' ')}
                      </span>
                    ),
                  },
                  {
                    key: 'detalle',
                    header: 'Detalle',
                    render: (row) => <span className="text-[12px] text-muted">{row.detalle}</span>,
                  },
                  {
                    key: 'regla',
                    header: 'Regla que lo detecta',
                    render: (row) => (
                      <span className="text-[12px] text-muted">{ruleText(row.regla_id)}</span>
                    ),
                  },
                  {
                    key: 'creado',
                    header: 'Cuándo',
                    width: '9rem',
                    render: (row) => (
                      <span className="text-[12px] text-faint">{formatRunDate(row.creado)}</span>
                    ),
                  },
                ]}
              />
            ) : (
              <Empty>
                Ningún hallazgo. Aparecen al activar o retirar una regla que cambia decisiones ya
                tomadas.
              </Empty>
            )}
          </NestedCard>
        </section>

        <section>
          <p className="mb-3 font-mono text-[11px] tracking-[0.12em] text-faint">
            NORMA EN VIGOR · {active.length} REGLAS
          </p>
          <NestedCard label="con lo que se está decidiendo ahora mismo">
            {active.length === 0 ? (
              <Empty>No hay reglas activas: todo se decide con el tipo por defecto.</Empty>
            ) : (
              <RuleSteps rules={active} />
            )}
          </NestedCard>
        </section>
      </div>
    </>
  )
}
