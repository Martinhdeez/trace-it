import { useEffect, useMemo, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CheckCircle2, ChevronDown, FileSearch, FileText } from 'lucide-react'
import { api, ApiError } from '../api/client'
import { families, keys } from '../api/queries'
import type {
  AlertOut,
  DecisionProposalPayload,
  InstanceDetail,
  ProcessDetail,
  Proposal,
  ProposalOutcome,
  RuleProposalPayload,
  RuleResult,
} from '../api/contracts'
import { ProcessScreen } from '../components/process/ProcessScreen'
import { Button, Field, Segmented, Select, Textarea } from '../components/shell/Controls'
import { Empty, EmptyState, ErrorNotice, Notice } from '../components/shell/Notice'
import { StatusBadge } from '../components/shell/StatusBadge'
import { TerminalLoader } from '../components/shell/TerminalLoader'
import { SenderContact } from '../components/run/SenderContact'
import { cn } from '../lib/cn'
import { t } from '../i18n'
import { ALERTS_TAB, paths } from '../lib/paths'
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
  const alerts = useQuery({
    queryKey: keys.alerts(processId, 'open'),
    queryFn: () => api.listAlerts(processId, 'open'),
  })
  const openAlerts = useMemo(() => alerts.data ?? [], [alerts.data])
  const human = byPriority(humanOutcomes(process.data))
  const queued = useMemo(() => escalated.data ?? [], [escalated.data])
  // A case the reviewer disagreed with keeps its decision but still waits for a person,
  // so it gets its own tab instead of hiding under the outcome.
  const tabs = useMemo(() => {
    const outcomes = human.map((outcome) => ({
      value: outcome.name,
      label: outcome.name.replaceAll('_', ' '),
      count: queued.filter((item) => item.decision === outcome.name && !item.review_pending)
        .length,
    }))
    const review = queued.filter((item) => item.review_pending).length
    return [
      ...outcomes,
      ...(review > 0 ? [{ value: REVIEW_TAB, label: t('queue.review'), count: review }] : []),
      { value: ALERTS_TAB, label: 'Alertas', count: openAlerts.length },
    ]
  }, [human, queued, openAlerts])

  const tab = params.get('tipo') ?? human[0]?.name ?? ''
  const items = queued.filter((item) =>
    tab === REVIEW_TAB ? item.review_pending : item.decision === tab && !item.review_pending,
  )
  const selectedId = params.get('i') ? Number(params.get('i')) : undefined
  const showAlerts = tab === ALERTS_TAB
  // reviewer-agent FE-3 (docs/reviewer-agent.md): a resolved case leaves the list but stays
  // open through `?i=` (after resolving, or from the Panel), so "Sugerir regla" can follow.
  // If you are merging a newer version from Carlos, keep his UI and make sure a selected
  // case outside the list still opens.
  const current = items.find((item) => item.id === selectedId) ?? (selectedId ? undefined : items[0])
  const caseId = showAlerts ? undefined : (current?.id ?? selectedId)
  const alert = openAlerts.find((item) => item.id === selectedId) ?? openAlerts[0]
  const nothing = showAlerts
    ? alerts.isSuccess && openAlerts.length === 0
    : escalated.isSuccess && caseId === undefined

  return (
    <ProcessScreen
      processId={processId}
      crumbs={[
        { label: 'Procesos', to: paths.processes },
        { label: process.data?.name ?? '…', to: paths.process(processId) },
        { label: 'Revisión' },
      ]}
      actions={
        tabs.length > 1 ? (
          <Segmented value={tab} onChange={(next) => setParams({ tipo: next })} options={tabs} />
        ) : null
      }
    >
      <div className="min-h-0 flex-1 overflow-y-auto px-4 pb-10 pt-4 sm:px-6">
        {escalated.isError ? <ErrorNotice error={escalated.error} /> : null}
        {alerts.isError ? <ErrorNotice error={alerts.error} /> : null}

        {nothing ? (
          <section className="rounded-[16px] bg-surface ring-1 ring-line">
            {showAlerts ? (
              <EmptyState icon={CheckCircle2} title="Sin alertas">
                Ninguna decisión pasada cambiaría con los datos y las reglas de hoy.
              </EmptyState>
            ) : (
              <EmptyState icon={CheckCircle2} title="Nada que revisar">
                Cuando un documento necesite a una persona, aparecerá aquí con lo que propone el
                asistente.
              </EmptyState>
            )}
          </section>
        ) : (
        <div className="grid gap-3 lg:grid-cols-[300px_minmax(0,1fr)]">
          <ul className="max-h-[560px] overflow-y-auto rounded-[16px] bg-surface p-1 ring-1 ring-line">
            {showAlerts ? (
              openAlerts.length === 0 ? (
                <li>
                  <Empty>Ninguna decisión pasada cambiaría con los datos y reglas de hoy.</Empty>
                </li>
              ) : (
                openAlerts.map((item) => (
                  <li key={item.id}>
                    <button
                      type="button"
                      onClick={() => setParams({ tipo: tab, i: String(item.id) })}
                      className={cn(
                        'mb-0.5 flex w-full items-center gap-2 rounded-[12px] px-2.5 py-2 text-left',
                        item.id === alert?.id
                          ? 'bg-canvas'
                          : 'hover:bg-canvas/70',
                      )}
                    >
                      <FileText size={13} strokeWidth={1.5} className="shrink-0 text-faint" />
                      <span className="min-w-0 flex-1 truncate font-mono text-[12px]">
                        {item.name}
                      </span>
                      <StatusBadge value={item.before} decisionTypes={process.data?.decision_types} />
                      →
                      <StatusBadge value={item.after} decisionTypes={process.data?.decision_types} />
                    </button>
                  </li>
                ))
              )
            ) : items.length === 0 ? (
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

          {showAlerts ? (
            alert ? <AlertDetail key={alert.id} processId={processId} alert={alert} /> : null
          ) : caseId !== undefined && process.data ? (
            <Resolve
              key={caseId}
              process={process.data}
              instanceId={caseId}
              name={current?.name}
              currentDecision={current?.decision}
              onSettled={() => setParams({ tipo: tab, i: String(caseId) })}
            />
          ) : null}
        </div>
        )}
      </div>
    </ProcessScreen>
  )
}

/**
 * reviewer-agent FE-1 (docs/reviewer-agent.md): opening a case makes no LLM call. It only
 * lists the case's open decision proposal; the assistant runs behind "Pedir propuesta al
 * asistente", hidden when a source was down. Only final decision types can be chosen (no
 * ESCALAR). Once a person resolved the case, it shows `SuggestRule` instead of the form.
 * Built on Carlos's patterns from #159; if you are merging a newer version from Carlos, keep
 * his UI and make sure it still does: no POST /proposal when a case opens; the decision
 * proposal's Aceptar / Rechazar stays as on main; options are clickable only while the
 * proposal is `open`; resolving never waits on a rule suggestion.
 */
function Resolve({
  process,
  instanceId,
  name,
  currentDecision,
  onSettled,
}: {
  process: ProcessDetail
  instanceId: number
  /** From the queue; a resolved case opened by `?i=` reads them from the instance. */
  name?: string
  currentDecision?: string | null
  onSettled: () => void
}) {
  const queryClient = useQueryClient()
  const outcomes = process.decision_types
    .filter((outcome) => !outcome.requires_human)
    .map((outcome) => outcome.name)
  const [decision, setDecision] = useState(
    currentDecision && outcomes.includes(currentDecision) ? currentDecision : (outcomes[0] ?? ''),
  )
  const [note, setNote] = useState('')
  const [edited, setEdited] = useState(false)

  const instance = useQuery({
    queryKey: keys.instance(instanceId),
    queryFn: () => api.getInstance(instanceId),
  })
  const history = instance.data?.decisions ?? []
  const engine = history.findLast((item) => item.author === 'engine')
  // The latest decision is a person's: the case is resolved.
  const resolved = history.length > 0 && history.at(-1)?.author !== 'engine'
  // A source that did not answer: the assistant cannot know more than the engine.
  const sourceDown = (engine?.reason ?? '').startsWith('SOURCE_UNAVAILABLE')

  // The case's open escalation proposal, if the manager already asked for one.
  const proposal = useQuery({
    queryKey: keys.caseProposal(instanceId),
    queryFn: async () => {
      const open = await api.listProposals(process.id, 'open')
      return (
        open.find(
          (item) =>
            item.instance_id === instanceId &&
            item.channel === 'escalation' &&
            item.kind === 'decision',
        ) ?? null
      )
    },
  })
  // The assistant is an LLM call: only on the button, and a 502 is not retried by itself.
  const ask = useMutation({
    mutationFn: () => api.proposeDecision(instanceId),
    onSuccess: (created) => queryClient.setQueryData(keys.caseProposal(instanceId), created),
  })
  const payload = proposal.data?.payload as DecisionProposalPayload | undefined
  const proposalId = proposal.data?.status === 'open' ? proposal.data.id : undefined

  // The assistant's proposal is the starting point; the person can overwrite it.
  useEffect(() => {
    if (!edited && payload) setDecision(payload.proposed)
  }, [payload, edited])

  const invalidate = () => {
    for (const name of [...families.decisions, ...families.rules, ...families.proposals]) {
      void queryClient.invalidateQueries({ queryKey: [name] })
    }
    // Keep the case on screen once it leaves the list: "Sugerir regla" comes next.
    onSettled()
  }

  /**
   * Choosing a decision by hand, or another option than the proposed one. With an open
   * proposal, `proposal_id` tells the backend it was not taken. A rule comes after, from
   * the reviewer agent (`SuggestRule`), and resolving never waits for it.
   */
  const resolve = useMutation({
    mutationFn: ({ chosen }: { chosen?: string }) =>
      api.resolve(instanceId, {
        decision: chosen ?? decision,
        reason: note.trim() || 'Resuelta por una persona',
        proposal_id: proposalId ?? null,
      }),
    onSuccess: invalidate,
  })
  /** Accepting resolves the case with the proposed decision; rejecting applies nothing. */
  const settle = useMutation({
    mutationFn: ({ accept }: { accept: boolean }) =>
      accept
        ? api.acceptProposal(proposalId!, note.trim() || undefined)
        : api.rejectProposal(proposalId!, note.trim()),
    onSuccess: invalidate,
  })
  const busy = resolve.isPending || settle.isPending
  const shownDecision = currentDecision ?? instance.data?.decision

  return (
    <div className="space-y-3">
      <div className="rounded-[16px] bg-surface px-4 py-3.5 ring-1 ring-line">
        <div className="flex items-baseline justify-between gap-3">
          <p className="font-mono text-[13px]">{name ?? instance.data?.name ?? '…'}</p>
          <Link
            to={paths.instance(process.id, instanceId)}
            className="shrink-0 text-[12px] text-muted hover:text-ink"
          >
            Ver traza →
          </Link>
        </div>
        {shownDecision ? (
          <p className="mt-1.5">
            <StatusBadge
              value={shownDecision}
              decisionTypes={process.decision_types}
              className={process.decision_types.some((type) => type.name === shownDecision && type.requires_human) ? 'bg-canvas text-muted' : undefined}
            />
          </p>
        ) : null}
        <div className="mt-3">
          {instance.isError ? (
            <ErrorNotice error={instance.error} />
          ) : instance.data ? (
            <WhyEscalated instance={instance.data} />
          ) : null}
        </div>
      </div>

      {resolved && instance.data ? (
        <SuggestRule process={process} instance={instance.data} />
      ) : (
        <>
          <Suggested
            proposal={proposal.data ?? undefined}
            loading={proposal.isPending || ask.isPending}
            error={proposal.error ?? ask.error}
            busy={busy}
            canAsk={!sourceDown}
            canReject={Boolean(note.trim())}
            onAsk={() => ask.mutate()}
            onAccept={() => settle.mutate({ accept: true })}
            onReject={() => settle.mutate({ accept: false })}
            onChoose={(chosen) => resolve.mutate({ chosen })}
          />

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
              <Field label={t('reviewUi.optionalReason')} hint={t('reviewUi.reasonHint')}>
                <Textarea
                  rows={1}
                  value={note}
                  onChange={(event) => setNote(event.target.value)}
                  placeholder="Por qué decides esto"
                  className="mt-1"
                />
              </Field>
            </div>

            {resolve.isError || settle.isError ? (
              <div className="mt-3">
                <ErrorNotice error={resolve.error ?? settle.error} />
              </div>
            ) : null}
            {settle.isSuccess ? (
              <div className="mt-3">
                <Notice
                  title={settle.data.status === 'accepted' ? 'Propuesta aceptada' : 'Propuesta rechazada'}
                >
                  {settle.data.status === 'accepted'
                    ? 'El caso queda resuelto con la decisión propuesta.'
                    : 'No se aplica nada. Resuelve el caso a mano.'}
                </Notice>
              </div>
            ) : null}
            {resolve.isSuccess ? (
              <div className="mt-3">
                <Notice title="Resuelta">La decisión queda en el histórico.</Notice>
              </div>
            ) : null}

            <div className="mt-4 flex flex-wrap gap-2">
              <Button tone="soft" onClick={() => resolve.mutate({})} disabled={busy || !decision}>
                Resolver
              </Button>
            </div>
          </div>
        </>
      )}
      {instance.data ? (
        <div className="px-4"><SenderContact instance={instance.data} /></div>
      ) : null}
    </div>
  )
}

/** A reason's detail, "iban, total", with each symbol's Spanish label. */
function symbolNames(detail: string): string {
  return detail
    .split(', ')
    .map((name) => {
      const label = t(`symbols.${name}`)
      return label === `symbols.${name}` ? name : label
    })
    .join(', ')
}

function sentence(code: string, x = '', y = ''): string {
  return t(`escalationWhy.${code}`).replace('{X}', x).replace('{Y}', y)
}

const RULE_FAILURE = /^(RULE_ERROR|RULE_NEEDS_DATA|RULE_COMPILE_FAILED|SOURCE_UNAVAILABLE) (\d+)/

/**
 * reviewer-agent FE-2 (docs/reviewer-agent.md): the engine's reason as Spanish sentences,
 * one per code, from templates in `i18n/es.ts`. No LLM. Rule failures come joined by " | ".
 */
function explain(reason: string, fired: RuleResult[]): string[] {
  const code = reason.match(/^[A-Z_]+/)?.[0] ?? ''
  const detail = reason.slice(reason.indexOf(': ') + 2)
  if (code === 'MISSING_DATA' || code === 'UNVERIFIED_DATA') return [sentence(code, symbolNames(detail))]
  if (reason.startsWith('SOURCE_UNAVAILABLE: ')) return [sentence('SOURCE_UNAVAILABLE', detail)]
  if (code === 'RULE_CONFLICT' || code === 'SCAN_REVIEW') return [sentence(code)]
  if (RULE_FAILURE.test(reason)) {
    return reason.split(' | ').map((part) => {
      const match = part.match(RULE_FAILURE)
      if (!match) return part
      return match[1] === 'SOURCE_UNAVAILABLE'
        ? sentence('SOURCE_UNAVAILABLE', part.slice(part.indexOf(': ') + 2))
        : sentence('RULE_ERROR', match[2])
    })
  }
  if (!fired.length) return [reason]
  return fired.map((result) =>
    sentence('rule', result.rule_summary || result.rule_text || `Regla ${result.rule_id}`, result.reason),
  )
}

/**
 * What the engine said, in a sentence per reason and an expandable technical detail, and, when
 * there was one, what the reviewer thought. Reads the engine's decision, so a resolved case
 * still says why it escalated. reviewer-agent FE-2: if you are merging a newer version from
 * Carlos, keep his UI and make sure it still explains with templates only (no LLM) and keeps
 * the raw code visible.
 */
function WhyEscalated({ instance }: { instance: InstanceDetail }) {
  const engine = instance.decisions.findLast((item) => item.author === 'engine')
  const reason = engine?.reason ?? instance.reason ?? ''
  const results = (engine?.results ?? []) as RuleResult[]
  const fired = results.filter((result) => result.fires === true)
  const review = instance.reviews.at(-1)
  const fields = reason.match(/^(MISSING_DATA|UNVERIFIED_DATA):\s*(.+)$/s)
  const missing = fields?.[2].split(',').map((field) => field.trim()).filter(Boolean) ?? []

  return (
    <section className="border-t border-hairline pt-4">
      <div className="flex items-start gap-3">
        <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-canvas text-muted">
          <FileSearch size={16} strokeWidth={1.6} />
        </span>
        <div className="min-w-0 flex-1">
          <h3 className="text-[13px] font-medium text-ink">
            {fields ? t(fields[1] === 'MISSING_DATA' ? 'reviewUi.missingFields' : 'reviewUi.unverifiedFields') : t('reviewUi.reviewReason')}
          </h3>
          {fields ? (
            <>
              <p className="mt-1 text-[12px] leading-5 text-muted">{t('reviewUi.missingHint')}</p>
              <ul className="mt-3 flex flex-wrap gap-1.5">
                {missing.map((field) => (
                  <li key={field} className="rounded-md border border-hairline bg-canvas/60 px-2 py-1 text-[11.5px] text-ink">
                    {symbolNames(field)}
                  </li>
                ))}
              </ul>
            </>
          ) : reason ? (
          <ul className="mt-1 space-y-1.5 text-[12.5px] leading-5 text-muted">
            {explain(reason, fired).map((line) => (
              <li key={line} className="break-words">{line}</li>
            ))}
          </ul>
          ) : <p className="mt-1 text-[12px] text-muted">El motor no dejó un motivo.</p>}
        </div>
      </div>
      {reason ? (
        <details className="group mt-4 border-t border-hairline pt-3">
          <summary className="flex cursor-pointer list-none items-center gap-1.5 text-[11.5px] text-muted hover:text-ink [&::-webkit-details-marker]:hidden">
            <ChevronDown size={12} className="transition-transform group-open:rotate-180 motion-reduce:transition-none" />
            {t('reviewUi.technicalReason')}
          </summary>
          <pre className="mt-2 whitespace-pre-wrap break-words rounded-lg bg-canvas p-3 font-mono text-[11px] leading-5 text-muted">{reason}</pre>
        </details>
      ) : null}
      {instance.review_pending && review ? (
        <p className="mt-3 border-t border-hairline pt-3 text-[12px] leading-5 text-muted">
          Revisor ({t(`reviewStatus.${review.status}`)}): {review.recommendation ?? '—'}
          {review.reasoning ? `. ${review.reasoning}` : ''}
        </p>
      ) : null}
    </section>
  )
}

/**
 * The assistant's proposal: why, and each option with its consequence, the proposed one
 * first. Accepting the proposed one resolves the case; another option resolves with it and
 * tells the backend the proposal was not taken. Rejecting takes the reason from "Motivo".
 * reviewer-agent FE-1: nothing is asked until "Pedir propuesta al asistente".
 */
function Suggested({
  proposal,
  loading,
  error,
  busy,
  canAsk,
  canReject,
  onAsk,
  onAccept,
  onReject,
  onChoose,
}: {
  proposal: Proposal | undefined
  loading: boolean
  error: unknown
  busy: boolean
  /** False when a source was down: the assistant would not know more than the engine. */
  canAsk: boolean
  canReject: boolean
  onAsk: () => void
  onAccept: () => void
  onReject: () => void
  onChoose: (decision: string) => void
}) {
  const payload = proposal?.payload as DecisionProposalPayload | undefined
  const open = proposal?.status === 'open'
  const options = payload
    ? [
        ...(payload.options ?? []).filter((option) => option.decision === payload.proposed),
        ...(payload.options ?? []).filter((option) => option.decision !== payload.proposed),
      ]
    : []
  if (payload && !options.some((option) => option.decision === payload.proposed)) {
    options.unshift({ decision: payload.proposed, consequence: proposal?.rationale ?? '' })
  }

  return (
    <div className="rounded-[16px] bg-surface px-4 py-3.5 ring-1 ring-line">
      <p className="text-[13px] font-medium">El asistente propone</p>
      {loading ? (
        <TerminalLoader
          className="mt-2"
          verbs={['leyendo el caso', 'mirando casos parecidos', 'comparando con las reglas', 'redactando la propuesta']}
        />
      ) : error ? (
        <div className="mt-2">
          <ErrorNotice
            error={error}
            action={
              canAsk ? (
                <Button tone="soft" onClick={onAsk}>
                  {t('common.retry')}
                </Button>
              ) : undefined
            }
          />
          <p className="mt-2 text-[13px] text-muted">Puedes resolver el caso a mano.</p>
        </div>
      ) : payload ? (
        <>
          <p className="mt-2 text-[13px] text-muted">{proposal?.rationale}</p>
          {payload.why?.length ? (
            <ul className="mt-1 list-disc space-y-0.5 pl-4 text-[13px] text-muted">
              {payload.why.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          ) : null}
          {options.map((option) => {
            const proposed = option.decision === payload.proposed
            return (
              <div
                key={option.decision}
                className="mt-2 rounded-[10px] bg-canvas px-3 py-2 text-[13px] ring-1 ring-line"
              >
                <p className="flex items-start gap-2">
                  <StatusBadge value={option.decision} className="mt-0.5 shrink-0" />
                  <span className="text-muted">{option.consequence}</span>
                </p>
                {open ? (
                  <div className="mt-2 flex flex-wrap gap-2">
                    <Button
                      tone={proposed ? 'primary' : 'soft'}
                      disabled={busy}
                      onClick={() => (proposed ? onAccept() : onChoose(option.decision))}
                    >
                      Aceptar
                    </Button>
                    {proposed ? (
                      <Button
                        tone="soft"
                        disabled={busy || !canReject}
                        title={canReject ? undefined : 'Escribe el motivo en "Motivo"'}
                        onClick={onReject}
                      >
                        Rechazar
                      </Button>
                    ) : null}
                  </div>
                ) : null}
              </div>
            )
          })}
          {proposal && !open ? (
            <p className="mt-2 text-[12px] text-faint">{t(`proposalStatus.${proposal.status}`)}</p>
          ) : null}
        </>
      ) : canAsk ? (
        <div className="mt-2 space-y-2">
          <p className="text-[13px] text-muted">
            El asistente lee el caso y propone una decisión con sus consecuencias. Decides tú.
          </p>
          <Button tone="soft" disabled={busy} onClick={onAsk}>
            Pedir propuesta al asistente
          </Button>
        </div>
      ) : (
        <p className="mt-2 text-[13px] text-muted">
          Una fuente no respondió: el asistente no sabría más que el motor. Vuelve a ejecutar
          cuando responda, o decide tú.
        </p>
      )}
    </div>
  )
}

/**
 * reviewer-agent FE-3 (docs/reviewer-agent.md): once a person resolved the case, the
 * reviewer agent can amend the escalation rule that fired so similar cases decide
 * themselves next time. Asked only on "Sugerir regla"; the card follows #159's "preview,
 * then accept" and the Definition inbox's "Rechazar needs a reason". Built on Carlos's
 * patterns from #159; if you are merging a newer version from Carlos, keep his UI and make
 * sure it still does: resolving never waits on this; a 409 shows the backend's Spanish
 * `message` as is; the manager can edit the rule before accepting (the textarea, as main's
 * "Regla que entra con esta decisión"; the edit goes as `text` to accept); Aceptar stages
 * the rule in the draft and never publishes; `rejected` (the manager's no) reads apart from
 * `superseded` with its `outcome.cause`. The decision proposal's accept/reject stays.
 */
function SuggestRule({ process, instance }: { process: ProcessDetail; instance: InstanceDetail }) {
  const queryClient = useQueryClient()
  const [rejecting, setRejecting] = useState(false)
  const [reason, setReason] = useState('')
  // The manager's edit of the suggested rule, for the suggestion it was made on.
  const [edit, setEdit] = useState<{ id: number; text: string } | null>(null)
  const resolution = instance.decisions.at(-1)

  // The case's latest rule suggestion (newest first), whatever its status: a settled one
  // says how it ended.
  const latest = useQuery({
    queryKey: keys.caseRuleProposal(instance.id),
    queryFn: async () =>
      (await api.listProposals(process.id)).find(
        (item) =>
          item.instance_id === instance.id && item.channel === 'escalation' && item.kind === 'rule',
      ) ?? null,
  })
  const suggest = useMutation({
    mutationFn: () => api.proposeRule(instance.id),
    onSuccess: (created) => {
      queryClient.setQueryData(keys.caseRuleProposal(instance.id), created)
      void queryClient.invalidateQueries({ queryKey: ['proposals'] })
    },
  })
  const proposal = latest.data ?? undefined
  const payload = proposal?.payload as RuleProposalPayload | undefined
  const ruleText = edit && edit.id === proposal?.id ? edit.text : (payload?.text ?? '')
  const edited = ruleText.trim() !== payload?.text ? ruleText.trim() : undefined
  const settle = useMutation({
    mutationFn: (accept: boolean) =>
      accept
        ? api.acceptProposal(proposal!.id, undefined, edited)
        : api.rejectProposal(proposal!.id, reason.trim()),
    onSuccess: (settled) => {
      queryClient.setQueryData(keys.caseRuleProposal(instance.id), settled)
      for (const name of [...families.proposals, ...families.rules]) {
        void queryClient.invalidateQueries({ queryKey: [name] })
      }
    },
  })

  const outcome = (proposal?.outcome ?? {}) as ProposalOutcome
  const open = proposal?.status === 'open'
  // The new rule compiles in the background: follow it until it leaves `compiling`.
  const rule = useQuery({
    queryKey: keys.rule(outcome.rule_id ?? 0),
    queryFn: () => api.getRule(outcome.rule_id!),
    enabled: proposal?.status === 'accepted' && outcome.rule_id != null,
    refetchInterval: (query) => (query.state.data?.status === 'compiling' ? 1_500 : false),
  })
  // 409: the gate's Spanish reason why no rule can learn this case. An answer, not an error.
  const unlearnable =
    suggest.error instanceof ApiError && suggest.error.status === 409 ? suggest.error.message : null
  const canSuggest =
    latest.isSuccess &&
    !suggest.isPending &&
    !unlearnable &&
    (!proposal || proposal.status === 'rejected' || proposal.status === 'superseded')

  return (
    <div className="rounded-[16px] bg-surface px-4 py-3.5 ring-1 ring-line">
      <p className="text-[13px] font-medium">¿Quieres que esto se decida solo la próxima vez?</p>
      {resolution ? (
        <p className="mt-1 flex items-start gap-2 text-[13px] text-muted">
          <StatusBadge
            value={resolution.decision}
            decisionTypes={process.decision_types}
            className="mt-0.5 shrink-0"
          />
          <span>
            Resuelta por {resolution.author}
            {resolution.reason ? `: ${resolution.reason}` : ''}
          </span>
        </p>
      ) : null}

      {latest.isError ? (
        <div className="mt-2">
          <ErrorNotice error={latest.error} />
        </div>
      ) : null}
      {suggest.isPending ? (
        <TerminalLoader
          className="mt-2"
          verbs={['leyendo tu decisión', 'buscando la regla que lo escaló', 'redactando la excepción']}
        />
      ) : unlearnable ? (
        <div className="mt-2">
          <Notice title="Ninguna regla puede aprender este caso">{unlearnable}</Notice>
        </div>
      ) : suggest.isError ? (
        <div className="mt-2">
          <ErrorNotice
            error={suggest.error}
            action={
              <Button tone="soft" onClick={() => suggest.mutate()}>
                {t('common.retry')}
              </Button>
            }
          />
        </div>
      ) : null}

      {proposal && payload ? (
        <div
          className={cn(
            'mt-3 rounded-[12px] bg-canvas px-3 py-2.5 ring-1 ring-line',
            !open && 'opacity-70',
          )}
        >
          <div className="flex items-start justify-between gap-3">
            <p className="text-[13px] font-medium leading-5 text-ink">{proposal.summary}</p>
            <span className="shrink-0 font-mono text-[11px] text-faint">
              {t(`proposalStatus.${proposal.status}`)}
              {proposal.status === 'superseded' && outcome.cause
                ? ` · ${t(`proposalCause.${outcome.cause}`)}`
                : ''}
            </span>
          </div>
          {proposal.rationale ? (
            <p className="mt-1 text-[12px] leading-5 text-muted">{proposal.rationale}</p>
          ) : null}
          {open ? (
            <Field
              label="Regla que entra con esta decisión"
              hint="Puedes editarla antes de aceptar. Así el proceso resuelve solo los casos parecidos."
              className="mt-2"
            >
              <Textarea
                rows={2}
                value={ruleText}
                onChange={(event) => setEdit({ id: proposal.id, text: event.target.value })}
                className="mt-1"
              />
            </Field>
          ) : (
            <p className="mt-2 text-[12px] leading-5 text-ink">{rule.data?.text ?? payload.text}</p>
          )}
          {outcome.edited && outcome.original_text ? (
            <p className="mt-1 text-[12px] leading-5 text-faint">
              Editada por ti. El agente proponía: {outcome.original_text}
            </p>
          ) : null}
          <Link
            to={paths.rule(process.id, payload.replaces)}
            className="mt-1 inline-block text-[12px] text-muted hover:text-ink"
          >
            Sustituye a la regla {payload.replaces} →
          </Link>

          {open ? (
            <>
              {rejecting ? (
                <Textarea
                  rows={2}
                  value={reason}
                  onChange={(event) => setReason(event.target.value)}
                  placeholder="Por qué no"
                  className="mt-3"
                />
              ) : null}
              {settle.isError ? (
                <div className="mt-3">
                  <ErrorNotice error={settle.error} />
                </div>
              ) : null}
              <div className="mt-3 flex flex-wrap gap-2">
                <Button
                  tone="soft"
                  disabled={settle.isPending || (rejecting && !reason.trim())}
                  onClick={() => (rejecting ? settle.mutate(false) : setRejecting(true))}
                >
                  Rechazar
                </Button>
                <Button
                  tone="primary"
                  disabled={settle.isPending || !ruleText.trim()}
                  onClick={() => settle.mutate(true)}
                >
                  {settle.isPending ? 'Guardando…' : 'Aceptar'}
                </Button>
              </div>
            </>
          ) : proposal.status === 'accepted' && outcome.rule_id != null ? (
            <div className="mt-3">
              <Notice title="La regla entra en el borrador">
                <p>
                  Regla {outcome.rule_id}
                  {outcome.retired != null ? ` en lugar de la regla ${outcome.retired}` : ''}
                  {rule.data ? ` · ${t(`ruleStatus.${rule.data.status}`)}` : ''}. Nada cambia
                  hasta que publiques el borrador.
                </p>
                <p className="mt-1 flex flex-wrap gap-3">
                  <Link to={paths.rule(process.id, outcome.rule_id)} className="underline">
                    Ver la regla
                  </Link>
                  <Link to={`${paths.panel(process.id)}?publicar=1`} className="underline">
                    Panel → Publicar
                  </Link>
                </p>
              </Notice>
            </div>
          ) : proposal.status === 'rejected' && outcome.reason ? (
            <p className="mt-2 text-[12px] text-muted">Motivo: {outcome.reason}</p>
          ) : null}
        </div>
      ) : null}

      {canSuggest ? (
        <div className="mt-3">
          <Button tone="primary" onClick={() => suggest.mutate()}>
            Sugerir regla
          </Button>
        </div>
      ) : null}
    </div>
  )
}

/** What changed, why, and a note to mark it seen. Resolving the case closes it on its own. */
function AlertDetail({ processId, alert }: { processId: number; alert: AlertOut }) {
  const queryClient = useQueryClient()
  const [note, setNote] = useState('')
  const trigger = String(alert.trigger.kind ?? '')
  const evidence = alert.evidence as {
    before?: { author?: string; reason?: string | null }
    after?: { author?: string; reason?: string | null }
  }

  const ack = useMutation({
    mutationFn: () => api.ackAlert(alert.id, note.trim()),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['alerts'] })
    },
  })

  return (
    <div className="space-y-3">
      <div className="rounded-[16px] bg-surface px-4 py-3.5 ring-1 ring-line">
        <div className="flex items-baseline justify-between gap-3">
          <p className="font-mono text-[13px]">{alert.name}</p>
          <Link
            to={paths.instance(processId, alert.instance_id)}
            className="shrink-0 text-[12px] text-muted hover:text-ink"
          >
            Ver traza →
          </Link>
        </div>
        <div className="mt-3">
          <Notice
            tone="warning"
            title={`${alert.before} → ${alert.after} · ${t(`alertTrigger.${trigger}`)}`}
          >
            <p>
              Antes ({evidence.before?.author ?? '—'}): {evidence.before?.reason || '—'}
            </p>
            <p>Ahora (motor): {evidence.after?.reason || '—'}</p>
          </Notice>
        </div>
      </div>

      <div className="rounded-[16px] bg-surface px-4 py-3.5 ring-1 ring-line">
        <Field label="Nota" hint="Queda en la alerta junto a tu nombre.">
          <Textarea
            rows={2}
            value={note}
            onChange={(event) => setNote(event.target.value)}
            placeholder="Por qué no hace falta cambiarla, o qué vas a hacer"
            className="mt-1"
          />
        </Field>
        {ack.isError ? (
          <div className="mt-3">
            <ErrorNotice error={ack.error} />
          </div>
        ) : null}
        <div className="mt-4 flex flex-wrap gap-2">
          <Button tone="primary" onClick={() => ack.mutate()} disabled={ack.isPending}>
            {ack.isPending ? 'Guardando…' : 'Marcar como vista'}
          </Button>
        </div>
      </div>
    </div>
  )
}
