import { useEffect, useMemo, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FileText, Sparkles } from 'lucide-react'
import { api } from '../api/client'
import { families, keys } from '../api/queries'
import type { ProcessDetail, RuleKind, Suggestion } from '../api/contracts'
import { ProcessScreen } from '../components/process/ProcessScreen'
import { Button, Field, Segmented, Select, Textarea } from '../components/shell/Controls'
import { Empty, ErrorNotice, Notice } from '../components/shell/Notice'
import { StatusBadge } from '../components/shell/StatusBadge'
import { PageIntro } from '../components/shell/Well'
import { cn } from '../lib/cn'
import { t } from '../i18n'
import { paths } from '../lib/paths'
import { byPriority, humanOutcomes } from '../lib/process'

const REVIEW_TAB = 'review'

/**
 * What is waiting on a person: every outcome the process marked
 * `requiere_persona`. Extraction gaps stay pending; they are not queue decisions.
 */
export function Queue() {
  const processId = Number(useParams().processId)
  const [params, setParams] = useSearchParams()

  const process = useQuery({
    queryKey: keys.process(processId),
    queryFn: () => api.getProcess(processId),
  })
  const escalated = useQuery({
    queryKey: keys.queue(processId, 'all'),
    queryFn: () => api.queue(processId),
  })
  const human = byPriority(humanOutcomes(process.data))
  const queued = useMemo(() => escalated.data ?? [], [escalated.data])
  // A case the reviewer disagreed with keeps its decision but still waits for a person,
  // so it gets its own tab instead of hiding under the outcome.
  const tabs = useMemo(() => {
    const outcomes = human.map((outcome) => ({
      value: outcome.nombre,
      label: outcome.nombre.replaceAll('_', ' '),
      count: queued.filter((item) => item.decision === outcome.nombre && !item.review_pending)
        .length,
    }))
    const review = queued.filter((item) => item.review_pending).length
    return review > 0
      ? [...outcomes, { value: REVIEW_TAB, label: t('queue.review'), count: review }]
      : outcomes
  }, [human, queued])

  const tab = params.get('tipo') ?? human[0]?.nombre ?? ''
  const items = queued.filter((item) =>
    tab === REVIEW_TAB ? item.review_pending : item.decision === tab && !item.review_pending,
  )
  const selectedId = params.get('i') ? Number(params.get('i')) : undefined
  const current = items.find((item) => item.id === selectedId) ?? items[0]

  return (
    <ProcessScreen
      processId={processId}
      crumbs={[
        { label: 'Procesos', to: paths.processes },
        { label: process.data?.nombre ?? '…', to: paths.process(processId) },
        { label: 'Revisión' },
      ]}
      actions={
        tabs.length > 1 ? (
          <Segmented value={tab} onChange={(next) => setParams({ tipo: next })} options={tabs} />
        ) : null
      }
    >
      <div className="min-h-0 flex-1 overflow-y-auto px-8 pb-10 pt-4">
        <PageIntro
          kicker="Revisión"
          title={tabs.find((item) => item.value === tab)?.label ?? (tab.replaceAll('_', ' ') || 'Cola')}
          description="Excepciones que el proceso no cierra. Tu decisión queda en el histórico y puede volverse una regla nueva, desde Definición."
        />

        {escalated.isError ? <ErrorNotice error={escalated.error} /> : null}

        <div className="grid gap-3 lg:grid-cols-[300px_minmax(0,1fr)]">
          <ul className="max-h-[560px] overflow-y-auto rounded-[16px] bg-surface p-1 ring-1 ring-line">
            {items.length === 0 ? (
              <li>
                <Empty>
                  Nada esperando. Las reglas cierran todos los casos.
                </Empty>
              </li>
            ) : (
              items.map((item) => (
                <li key={item.id}>
                  <button
                    type="button"
                    onClick={() => setParams({ tipo: tab, i: String(item.id) })}
                    className={cn(
                      'mb-0.5 flex w-full items-center gap-2 rounded-[12px] px-2.5 py-2 text-left',
                      item.id === current?.id
                        ? 'bg-canvas'
                        : 'hover:bg-canvas/70',
                    )}
                  >
                    <FileText size={13} strokeWidth={1.5} className="shrink-0 text-faint" />
                    <span className="min-w-0 flex-1 truncate font-mono text-[12px]">
                      {item.name}
                    </span>
                  </button>
                </li>
              ))
            )}
          </ul>

          {current && process.data ? (
            <Resolve
              key={current.id}
              process={process.data}
              instanceId={current.id}
              name={current.name}
              currentDecision={current.decision}
            />
          ) : null}
        </div>
      </div>
    </ProcessScreen>
  )
}

function Resolve({
  process,
  instanceId,
  name,
  currentDecision,
}: {
  process: ProcessDetail
  instanceId: number
  name: string
  currentDecision: string | null
}) {
  const queryClient = useQueryClient()
  const outcomes = process.tipos_decision.map((outcome) => outcome.nombre)
  const [decision, setDecision] = useState(currentDecision ?? outcomes[0] ?? '')
  const [note, setNote] = useState('')
  const [ruleText, setRuleText] = useState('')
  const [ruleKind, setRuleKind] = useState<RuleKind>('requisito')
  const [edited, setEdited] = useState(false)

  const suggestion = useQuery({
    queryKey: keys.suggestion(instanceId),
    queryFn: () => api.suggestion(instanceId),
  })

  // The assistant's proposal is the starting point; the person can overwrite it.
  useEffect(() => {
    const data = suggestion.data
    if (!data || edited) return
    setDecision(data.decision)
    setRuleText(data.regla_propuesta)
    setRuleKind(data.tipo_propuesto)
  }, [suggestion.data, edited])

  /**
   * Two calls, because the backend keeps them apart: resolving writes a decision
   * row, and the rule is a separate draft that still has to be compiled.
   */
  const resolve = useMutation({
    mutationFn: async ({ withRule }: { withRule: boolean }) => {
      await api.resolve(instanceId, {
        decision,
        motivo: note.trim() || 'Resuelta por una persona',
      })
      const text = ruleText.trim()
      if (!withRule || !text) return null
      return api.createRule(process.id, { texto: text, tipo: ruleKind, decision })
    },
    onSuccess: () => {
      for (const name of [...families.decisions, ...families.rules]) {
        void queryClient.invalidateQueries({ queryKey: [name] })
      }
    },
  })

  const newRule = resolve.data

  return (
    <div className="space-y-3">
      <div className="rounded-[16px] bg-surface px-4 py-3.5 ring-1 ring-line">
        <div className="flex items-baseline justify-between gap-3">
          <p className="font-mono text-[13px]">{name}</p>
          <Link
            to={paths.instance(process.id, instanceId)}
            className="shrink-0 text-[12px] text-muted hover:text-ink"
          >
            Ver traza →
          </Link>
        </div>
        {currentDecision ? (
          <p className="mt-1.5">
            <StatusBadge value={currentDecision} decisionTypes={process.tipos_decision} />
          </p>
        ) : null}
      </div>

      <Suggested suggestion={suggestion.data} loading={suggestion.isPending} />

      <div className="rounded-[16px] bg-surface px-4 py-3.5 ring-1 ring-line">
        <p className="text-[13px] font-medium">Tu decisión</p>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <Field label="Decisión">
            <Select
              value={decision}
              onChange={(event) => {
                setEdited(true)
                setDecision(event.target.value)
              }}
              className="mt-1"
            >
              {outcomes.map((outcome) => (
                <option key={outcome} value={outcome}>
                  {outcome}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Motivo" hint="Queda en el histórico junto a tu nombre.">
            <Textarea
              rows={1}
              value={note}
              onChange={(event) => setNote(event.target.value)}
              placeholder="Por qué decides esto"
              className="mt-1"
            />
          </Field>
        </div>

        <div className="mt-4">
          <Field
            label="Regla que entra con esta decisión"
            hint="Así el proceso resuelve solo los casos parecidos que vengan después."
          >
            <Textarea
              rows={2}
              value={ruleText}
              onChange={(event) => {
                setEdited(true)
                setRuleText(event.target.value)
              }}
              placeholder="Si el pedido de la factura no existe en el maestro, no se paga."
              className="mt-1"
            />
          </Field>
          <div className="mt-2">
            <Segmented
              value={ruleKind}
              onChange={(value) => {
                setEdited(true)
                setRuleKind(value)
              }}
              options={[
                { value: 'requisito', label: 'Requisito' },
                { value: 'prohibicion', label: 'Prohibición' },
              ]}
            />
          </div>
        </div>

        {resolve.isError ? (
          <div className="mt-3">
            <ErrorNotice error={resolve.error} />
          </div>
        ) : null}
        {resolve.isSuccess ? (
          <div className="mt-3">
            <Notice title="Resuelta">
              La decisión queda en el histórico.
              {newRule ? (
                <>
                  {' '}
                  La regla nueva entra como borrador:{' '}
                  <Link to={paths.rule(process.id, newRule.id)} className="underline">
                    compílala y actívala
                  </Link>
                  .
                </>
              ) : null}
            </Notice>
          </div>
        ) : null}

        <div className="mt-4 flex flex-wrap gap-2">
          <Button
            tone="primary"
            onClick={() => resolve.mutate({ withRule: true })}
            disabled={resolve.isPending || !decision || !ruleText.trim()}
          >
            {resolve.isPending ? 'Guardando…' : 'Resolver y crear la regla'}
          </Button>
          <Button
            tone="soft"
            onClick={() => resolve.mutate({ withRule: false })}
            disabled={resolve.isPending || !decision}
          >
            Resolver sin regla
          </Button>
        </div>
      </div>
    </div>
  )
}

function Suggested({
  suggestion,
  loading,
}: {
  suggestion: Suggestion | undefined
  loading: boolean
}) {
  return (
    <div className="rounded-[16px] bg-surface px-4 py-3.5 ring-1 ring-line">
      <p className="flex items-center gap-1.5 text-[13px] font-medium">
        <Sparkles size={13} strokeWidth={1.75} className="text-faint" />
        El asistente propone
      </p>
      {loading ? (
        <p className="mt-2 text-[13px] text-muted">Pensando…</p>
      ) : suggestion ? (
        <>
          <p className="mt-2 flex items-start gap-2 text-[13px]">
            <StatusBadge value={suggestion.decision} className="mt-0.5 shrink-0" />
            <span className="text-muted">{suggestion.razonamiento}</span>
          </p>
          <p className="mt-2 rounded-[10px] bg-canvas px-3 py-2 text-[13px] ring-1 ring-line">
            {suggestion.regla_propuesta}
          </p>
        </>
      ) : (
        <p className="mt-2 text-[13px] text-muted">
          Sin sugerencia. Decide tú y escribe la regla que lo resuelva.
        </p>
      )}
    </div>
  )
}
