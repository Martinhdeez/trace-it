import { useEffect, useRef, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowUp, ChevronDown, Hammer, Paperclip, Plus, Sparkles, X } from 'lucide-react'
import { api } from '../api/client'
import { keys } from '../api/queries'
import type {
  Finding,
  ProcessDetail,
  ProcessSymbol,
  Rule,
  RuleInput,
  RuleKind,
  VersionOut,
} from '../api/contracts'
import { DefinitionSwitch } from '../components/process/DefinitionSwitch'
import {
  FileChip,
  revokePreview,
  toPreview,
  type FilePreview,
} from '../components/process/FileChip'
import { ProcessScreen } from '../components/process/ProcessScreen'
import { TruthSources } from '../components/process/TruthSources'
import { Button, Input, Select, Textarea } from '../components/shell/Controls'
import { ErrorNotice, Empty } from '../components/shell/Notice'
import { NestedCard } from '../components/shell/Well'
import { cn } from '../lib/cn'
import { definitionTabFromPath, type DefinitionTabId } from '../lib/definitionTabs'
import { formatRunDate } from '../lib/format'
import { paths } from '../lib/paths'
import { toRuleIn } from '../lib/rules'

type Attachment = FilePreview & { file: File }

type Proposal =
  | {
      id: string
      kind: 'add_rule'
      texto: string
      tipo: RuleKind
      decision: string
    }
  | {
      id: string
      kind: 'retire_rule'
      ruleId: number
      texto: string
    }
  | {
      id: string
      kind: 'update_context'
      texto: string
    }
  | {
      id: string
      kind: 'add_symbol'
      nombre: string
      tipo: string
      descripcion: string
    }
  | {
      id: string
      kind: 'source_note'
      texto: string
    }

type Turn = {
  id: string
  prompt: string
  files: Attachment[]
  proposals: Proposal[]
}

const PANE_CHAT = {
  normas: {
    chips: ['El IBAN debe coincidir con el maestro', 'Si falta el pedido, ESCALAR', 'NIF del emisor dado de alta'],
    placeholder: 'Un cambio en la norma, un ejemplo, o suelta un archivo.',
    proposals: 'Propuestas · aplicar abre una versión',
  },
  contexto: {
    chips: ['NIF en mayúsculas, sin espacios', 'Importes en euros', 'Si falta un valor, ESCALAR'],
    placeholder: 'Cómo se lee un NIF, un euro, una fecha vacía…',
    proposals: 'Propuestas · aplicar entra al contexto',
  },
  inputs: {
    chips: ['nif_emisor', 'iban_cobro', 'numero_pedido'],
    placeholder: 'nif_emisor, el NIF del emisor sin espacios.',
    proposals: 'Propuestas · aplicar suma el símbolo',
  },
  fuentes: {
    chips: ['Maestro de proveedores', 'Pedidos abiertos', 'Parámetros del ERP'],
    placeholder: 'Maestro de proveedores, pedidos, el conector del ERP…',
    proposals: 'Propuestas',
  },
} as const

export function Definition() {
  const processId = Number(useParams().processId)
  const location = useLocation()
  const pane = definitionTabFromPath(location.pathname)
  const chat = PANE_CHAT[pane]
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [turns, setTurns] = useState<Turn[]>([])
  const [accepted, setAccepted] = useState<Set<string>>(new Set())
  const [draft, setDraft] = useState('')
  const [focusTick, setFocusTick] = useState(0)

  useEffect(() => {
    setDraft('')
  }, [pane])

  const process = useQuery({
    queryKey: keys.process(processId),
    queryFn: () => api.getProcess(processId),
  })
  const findings = useQuery({
    queryKey: keys.findings(processId),
    queryFn: () => api.listFindings(processId),
  })
  const versions = useQuery({
    queryKey: keys.versions(processId),
    queryFn: () => api.listVersions(processId),
  })
  const rules = useQuery({
    queryKey: keys.rules(processId),
    queryFn: () => api.listRules(processId),
    refetchInterval: (query) =>
      query.state.data?.some((rule) => rule.estado === 'compilando') ? 2_000 : false,
  })

  const all = rules.data ?? []
  const outcomes = process.data?.tipos_decision.map((outcome) => outcome.nombre) ?? []
  const latestVersion = versions.data?.reduce<VersionOut | undefined>(
    (latest, version) => (!latest || version.number > latest.number ? version : latest),
    undefined,
  )

  const create = useMutation({
    mutationFn: (body: RuleInput) => api.createRule(processId, toRuleIn(body)),
    onSuccess: (rule) => {
      void queryClient.invalidateQueries({ queryKey: ['rules'] })
      navigate(paths.rule(processId, rule.id))
    },
  })
  const retire = useMutation({
    mutationFn: (id: number) => api.retireRule(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['rules'] })
    },
  })
  const saveContext = useMutation({
    mutationFn: async (texto: string) => {
      if (!process.data) throw new Error('Sin proceso')
      const current = process.data.descripcion.trim()
      return api.loadDefinition({
        nombre: process.data.nombre,
        descripcion: current ? `${current}\n${texto.trim()}` : texto.trim(),
        tipos_decision: process.data.tipos_decision,
        simbolos: process.data.simbolos,
      })
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['process'] })
      void queryClient.invalidateQueries({ queryKey: ['processes'] })
    },
  })
  const addSymbol = useMutation({
    mutationFn: async (symbol: ProcessSymbol) => {
      const current = process.data?.simbolos ?? []
      if (current.some((item) => item.nombre === symbol.nombre)) return process.data
      return api.replaceSymbols(processId, [...current, symbol])
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: keys.process(processId) })
    },
  })

  const busy =
    create.isPending || retire.isPending || saveContext.isPending || addSymbol.isPending

  const propose = (prompt: string, files: Attachment[]) => {
    const proposals = proposalsFrom(pane, prompt, all, process.data?.simbolos ?? [], outcomes[0] ?? 'ESCALAR')
    setTurns((current) => [
      ...current,
      { id: crypto.randomUUID(), prompt, files, proposals },
    ])
  }

  const apply = (proposal: Proposal) => {
    if (accepted.has(proposal.id)) return
    setAccepted((current) => new Set(current).add(proposal.id))
    if (proposal.kind === 'add_rule') {
      create.mutate({
        texto: proposal.texto,
        tipo: proposal.tipo,
        decision: proposal.decision,
      })
    }
    if (proposal.kind === 'retire_rule') {
      retire.mutate(proposal.ruleId)
    }
    if (proposal.kind === 'update_context') {
      saveContext.mutate(proposal.texto)
    }
    if (proposal.kind === 'add_symbol') {
      addSymbol.mutate({
        nombre: proposal.nombre,
        tipo: proposal.tipo,
        descripcion: proposal.descripcion,
      })
    }
  }

  return (
    <ProcessScreen
      processId={processId}
      crumbs={[
        { label: 'Procesos', to: paths.processes },
        { label: process.data?.nombre ?? '…', to: paths.process(processId) },
        { label: 'Definición' },
      ]}
    >
      <div className="grid min-h-0 flex-1 lg:grid-cols-[minmax(0,1fr)_minmax(22rem,1fr)]">
        <section className="flex min-h-0 flex-col border-b border-hairline lg:border-b-0 lg:border-r">
          <div className="min-h-0 flex-1 overflow-y-auto px-5 py-5">
            {turns.length > 0 ? (
              <ol className="space-y-6">
                {turns.map((turn) => (
                  <li key={turn.id} className="space-y-3">
                    <div className="rounded-[16px] bg-surface px-4 py-3 ring-1 ring-line">
                      <p className="text-[13px] leading-6 text-ink">{turn.prompt}</p>
                      {turn.files.length ? (
                        <ul className="mt-2 flex flex-wrap gap-2">
                          {turn.files.map((file) => (
                            <li key={file.id}>
                              <FileChip file={file} />
                            </li>
                          ))}
                        </ul>
                      ) : null}
                    </div>
                    <div className="flex items-center gap-1.5 text-[12px] text-muted">
                      <Sparkles size={13} strokeWidth={1.6} />
                      {chat.proposals}
                    </div>
                    <ul className="space-y-2">
                      {turn.proposals.map((proposal) => (
                        <ProposalCard
                          key={proposal.id}
                          proposal={proposal}
                          outcomes={outcomes}
                          applied={accepted.has(proposal.id)}
                          busy={busy}
                          onChange={(next) =>
                            setTurns((current) =>
                              current.map((item) =>
                                item.id === turn.id
                                  ? {
                                      ...item,
                                      proposals: item.proposals.map((entry) =>
                                        entry.id === next.id ? next : entry,
                                      ),
                                    }
                                  : item,
                              ),
                            )
                          }
                          onApply={() => apply(proposal)}
                        />
                      ))}
                    </ul>
                  </li>
                ))}
              </ol>
            ) : null}

            {create.isError ? (
              <div className="mt-4">
                <ErrorNotice error={create.error} />
              </div>
            ) : null}
            {retire.isError ? (
              <div className="mt-4">
                <ErrorNotice error={retire.error} />
              </div>
            ) : null}
            {saveContext.isError ? (
              <div className="mt-4">
                <ErrorNotice error={saveContext.error} />
              </div>
            ) : null}
            {addSymbol.isError ? (
              <div className="mt-4">
                <ErrorNotice error={addSymbol.error} />
              </div>
            ) : null}
          </div>

          {turns.length === 0 ? (
            <div className="flex flex-wrap gap-2 px-5 pb-1">
              {chat.chips.map((chip) => (
                <button
                  key={chip}
                  type="button"
                  onClick={() => {
                    setDraft(chip)
                    setFocusTick((tick) => tick + 1)
                  }}
                  className={cn(
                    'rounded-full px-3 py-1.5 text-left text-[12px] ring-1',
                    draft === chip
                      ? 'bg-surface text-ink shadow-lift ring-line'
                      : 'bg-canvas text-ink/75 ring-line hover:bg-surface hover:text-ink',
                  )}
                >
                  {chip}
                </button>
              ))}
            </div>
          ) : null}

          <Composer
            placeholder={chat.placeholder}
            draft={draft}
            onDraft={setDraft}
            focusTick={focusTick}
            onSend={(text, files) => {
              propose(text, files)
              setDraft('')
            }}
          />
        </section>

        <aside className="flex min-h-0 flex-col">
          <header className="flex shrink-0 items-start justify-between gap-3 border-b border-hairline px-5 py-3">
            <DefinitionSwitch processId={processId} />
            <VersionChip
              label={latestVersion ? `v${latestVersion.number}` : 'borrador'}
              hash={latestVersion?.content_hash.slice(0, 8) ?? ''}
              stamp={latestVersion?.created_at}
              findings={findings.data ?? []}
            />
          </header>
          <div className="min-h-0 flex-1 overflow-y-auto px-5 py-5">
            {pane === 'normas' ? (
              <RulesPane processId={processId} rules={all} outcomes={outcomes} />
            ) : null}
            {pane === 'contexto' ? <ContextPane process={process.data} /> : null}
            {pane === 'inputs' ? (
              <InputsPane processId={processId} process={process.data} />
            ) : null}
            {pane === 'fuentes' ? <TruthSources processId={processId} /> : null}
          </div>
        </aside>
      </div>
    </ProcessScreen>
  )
}

const RULE_STATUS: Record<
  Rule['estado'],
  { dot: string; ink: string; soft: string; pill: string; ring: string }
> = {
  activa: {
    dot: 'bg-pagar',
    ink: 'text-pagar',
    soft: 'bg-pagar-soft',
    pill: 'group-hover:bg-pagar-soft [@media(hover:none)]:bg-pagar-soft',
    ring: 'border-pagar/20 border-t-pagar',
  },
  compilando: {
    dot: 'bg-ocr',
    ink: 'text-ocr',
    soft: 'bg-ocr-soft',
    pill: 'group-hover:bg-ocr-soft [@media(hover:none)]:bg-ocr-soft',
    ring: 'border-ocr/20 border-t-ocr',
  },
  borrador: {
    dot: 'bg-faint',
    ink: 'text-muted',
    soft: 'bg-well',
    pill: 'group-hover:bg-well [@media(hover:none)]:bg-well',
    ring: 'border-faint/25 border-t-faint',
  },
  bloqueada: {
    dot: 'bg-escalar',
    ink: 'text-escalar',
    soft: 'bg-escalar-soft',
    pill: 'group-hover:bg-escalar-soft [@media(hover:none)]:bg-escalar-soft',
    ring: 'border-escalar/20 border-t-escalar',
  },
  rechazada: {
    dot: 'bg-nopagar',
    ink: 'text-nopagar',
    soft: 'bg-nopagar-soft',
    pill: 'group-hover:bg-nopagar-soft [@media(hover:none)]:bg-nopagar-soft',
    ring: 'border-nopagar/20 border-t-nopagar',
  },
  retirada: {
    dot: 'bg-faint/50',
    ink: 'text-faint',
    soft: 'bg-well',
    pill: 'group-hover:bg-well [@media(hover:none)]:bg-well',
    ring: 'border-faint/20 border-t-faint',
  },
}

function RulesPane({
  processId,
  rules,
  outcomes,
}: {
  processId: number
  rules: Rule[]
  outcomes: string[]
}) {
  const queryClient = useQueryClient()
  const input = useRef<HTMLInputElement>(null)
  const [adding, setAdding] = useState(false)
  const [text, setText] = useState('')
  const [pending, setPending] = useState<Set<number>>(new Set())

  useEffect(() => {
    if (adding) input.current?.focus()
  }, [adding])

  const create = useMutation({
    mutationFn: (body: RuleInput) => api.createRule(processId, toRuleIn(body)),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['rules'] })
      setText('')
      requestAnimationFrame(() => input.current?.focus())
    },
  })

  const compile = useMutation({
    mutationFn: (id: number) => api.compileRule(id),
    onMutate: (id) => {
      setPending((current) => new Set(current).add(id))
    },
    onSettled: (_data, _error, id) => {
      setPending((current) => {
        const next = new Set(current)
        next.delete(id)
        return next
      })
      void queryClient.invalidateQueries({ queryKey: ['rules'] })
    },
  })

  const submit = () => {
    const texto = text.trim()
    if (!texto || create.isPending) return
    create.mutate({
      texto,
      tipo: 'requisito',
      decision: outcomes[0] ?? 'ESCALAR',
    })
  }

  return (
    <>
      <p className="mb-2 font-mono text-[11px] tracking-[0.12em] text-faint">
        NORMA · {rules.length}
      </p>
      <ul className="divide-y divide-hairline">
        {rules.map((rule) => {
          const working = pending.has(rule.id) || rule.estado === 'compilando'
          const canCompile = !working && (rule.estado === 'borrador' || rule.estado === 'bloqueada')
          return (
            <li key={rule.id} className="group flex h-9 items-center gap-2">
              <Link
                to={paths.rule(processId, rule.id)}
                className="min-w-0 flex-1 truncate text-[13px] leading-5 text-ink hover:text-ink"
              >
                {rule.texto}
              </Link>
              <RuleStatus
                estado={rule.estado}
                working={working}
                action={canCompile ? 'Compilar' : undefined}
                onAction={canCompile ? () => compile.mutate(rule.id) : undefined}
              />
            </li>
          )
        })}
      </ul>

      {adding ? (
        <div className="flex items-center gap-2 py-2">
          <Plus size={12} strokeWidth={2} className="shrink-0 text-faint" />
          <input
            ref={input}
            value={text}
            disabled={create.isPending}
            onChange={(event) => setText(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter') {
                event.preventDefault()
                submit()
              }
              if (event.key === 'Escape') {
                setAdding(false)
                setText('')
              }
            }}
            onBlur={() => {
              if (!text.trim() && !create.isPending) setAdding(false)
            }}
            placeholder="Una frase. Enter guarda, Esc cancela."
            className="min-w-0 flex-1 bg-transparent text-[13px] text-ink outline-none placeholder:text-faint disabled:opacity-60"
          />
        </div>
      ) : (
        <button
          type="button"
          onClick={() => setAdding(true)}
          className="mt-1 flex w-full items-center gap-2 py-2 text-left text-[13px] text-muted hover:text-ink"
        >
          <Plus size={12} strokeWidth={2} />
          Añadir regla
        </button>
      )}

      {create.isError ? (
        <div className="mt-3">
          <ErrorNotice error={create.error} />
        </div>
      ) : null}
      {compile.isError ? (
        <div className="mt-3">
          <ErrorNotice error={compile.error} />
        </div>
      ) : null}
    </>
  )
}

function RuleStatus({
  estado,
  working,
  action,
  onAction,
}: {
  estado: Rule['estado']
  working: boolean
  action?: string
  onAction?: () => void
}) {
  const [seconds, setSeconds] = useState(0)
  const tone = RULE_STATUS[estado]
  const label = working ? `${seconds}s` : estado

  useEffect(() => {
    if (!working) {
      setSeconds(0)
      return
    }
    const id = window.setInterval(() => setSeconds((value) => value + 1), 1000)
    return () => window.clearInterval(id)
  }, [working])

  return (
    <div
      className={cn(
        'inline-flex h-5 max-w-2 shrink-0 items-center overflow-hidden rounded-full',
        'transition-[max-width,padding,gap,background-color] duration-150 ease-out',
        'group-hover:max-w-[12rem] group-hover:gap-1 group-hover:px-1',
        '[@media(hover:none)]:max-w-[12rem] [@media(hover:none)]:gap-1 [@media(hover:none)]:px-1',
        working && 'max-w-[12rem] gap-1 px-1',
        tone.pill,
        working && tone.soft,
      )}
    >
      <span className="relative h-2 w-2 shrink-0">
        {working ? (
          <>
            <span className={cn('absolute inset-[2px] rounded-full', tone.dot)} />
            <span
              aria-hidden
              className={cn(
                'absolute inset-0 rounded-full border-[1.5px] animate-spin motion-reduce:animate-none',
                tone.ring,
              )}
            />
          </>
        ) : (
          <span className={cn('absolute inset-0 rounded-full', tone.dot)} />
        )}
      </span>
      <span
        className={cn(
          'whitespace-nowrap text-[11px] leading-none tabular-nums',
          'opacity-0 transition-opacity duration-150 ease-out',
          'group-hover:opacity-100 [@media(hover:none)]:opacity-100',
          working && 'opacity-100',
          tone.ink,
        )}
      >
        {label}
      </span>
      {action && onAction && !working ? (
        <button
          type="button"
          title={action}
          onClick={onAction}
          className={cn(
            'grid h-4 w-4 shrink-0 place-items-center text-faint',
            'opacity-0 transition-opacity duration-150 ease-out',
            'group-hover:opacity-100 hover:text-ink',
            '[@media(hover:none)]:opacity-100',
          )}
        >
          <Hammer size={11} strokeWidth={1.7} />
        </button>
      ) : null}
    </div>
  )
}

function ContextPane({ process }: { process: ProcessDetail | undefined }) {
  const queryClient = useQueryClient()
  const [text, setText] = useState('')

  useEffect(() => {
    setText(process?.descripcion ?? '')
  }, [process?.descripcion])

  const save = useMutation({
    mutationFn: async () => {
      if (!process) throw new Error('Sin proceso')
      return api.loadDefinition({
        nombre: process.nombre,
        descripcion: text.trim(),
        tipos_decision: process.tipos_decision,
        simbolos: process.simbolos,
      })
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['process'] })
      void queryClient.invalidateQueries({ queryKey: ['processes'] })
    },
  })

  const dirty = text.trim() !== (process?.descripcion ?? '').trim()

  return (
    <NestedCard label="convenciones del agente">
        <div className="space-y-3 px-3.5 py-3">
          <Textarea
            rows={8}
            value={text}
            onChange={(event) => setText(event.target.value)}
            placeholder="NIF en mayúsculas, sin espacios. Importes en euros. Si falta el pedido, ESCALAR."
          />
          <div className="flex items-center justify-between gap-3">
            <p className="text-[11px] text-faint">
              Entra en cada compilación. No es una regla: es el marco.
            </p>
            <Button
              tone="primary"
              disabled={!dirty || !process || save.isPending}
              onClick={() => save.mutate()}
            >
              {save.isPending ? 'Guardando…' : 'Guardar'}
            </Button>
          </div>
          {save.isError ? <ErrorNotice error={save.error} /> : null}
        </div>
      </NestedCard>
    )
}

function InputsPane({
  processId,
  process,
}: {
  processId: number
  process: ProcessDetail | undefined
}) {
  const queryClient = useQueryClient()
  const symbols = process?.simbolos ?? []
  const outcomes = process?.tipos_decision ?? []
  const [draft, setDraft] = useState({ nombre: '', tipo: 'texto', descripcion: '' })

  const replace = useMutation({
    mutationFn: (next: ProcessSymbol[]) => api.replaceSymbols(processId, next),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: keys.process(processId) })
    },
  })

  const add = () => {
    const nombre = draft.nombre.trim()
    if (!nombre) return
    if (symbols.some((item) => item.nombre === nombre)) return
    replace.mutate([
      ...symbols,
      { nombre, tipo: draft.tipo.trim() || 'texto', descripcion: draft.descripcion.trim() },
    ])
    setDraft({ nombre: '', tipo: 'texto', descripcion: '' })
  }

  return (
    <div className="space-y-8">
      <section>
        <p className="mb-3 font-mono text-[11px] tracking-[0.12em] text-faint">
          SÍMBOLOS · {symbols.length}
        </p>
        <NestedCard
          label="campos del documento"
          action={
            replace.isPending ? (
              <span className="font-mono text-[11px] text-faint">guardando…</span>
            ) : null
          }
        >
          {symbols.length ? (
            <ul className="divide-y divide-hairline">
              {symbols.map((symbol) => (
                <li key={symbol.nombre} className="flex items-start gap-3 px-3.5 py-2.5">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-baseline gap-2">
                      <span className="font-mono text-[12px]">{symbol.nombre}</span>
                      <span className="text-[11px] text-faint">{symbol.tipo}</span>
                    </div>
                    <p className="mt-0.5 text-[12px] text-muted">{symbol.descripcion}</p>
                  </div>
                  <button
                    type="button"
                    className="grid h-6 w-6 shrink-0 place-items-center rounded-full text-faint hover:bg-canvas hover:text-ink"
                    title="Quitar"
                    onClick={() =>
                      replace.mutate(symbols.filter((item) => item.nombre !== symbol.nombre))
                    }
                  >
                    <X size={12} strokeWidth={1.8} />
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <Empty>Ningún símbolo. Las reglas no tienen de qué leer.</Empty>
          )}
          <div className="grid gap-2 border-t border-hairline px-3.5 py-3">
            <Input
              value={draft.nombre}
              onChange={(event) => setDraft((current) => ({ ...current, nombre: event.target.value }))}
              placeholder="nif_emisor"
            />
            <div className="grid grid-cols-[7rem_minmax(0,1fr)] gap-2">
              <Input
                value={draft.tipo}
                onChange={(event) => setDraft((current) => ({ ...current, tipo: event.target.value }))}
                placeholder="texto"
              />
              <Input
                value={draft.descripcion}
                onChange={(event) =>
                  setDraft((current) => ({ ...current, descripcion: event.target.value }))
                }
                placeholder="NIF del emisor, sin espacios."
              />
            </div>
            <Button tone="soft" disabled={!draft.nombre.trim() || replace.isPending} onClick={add}>
              <Plus size={12} strokeWidth={2} />
              Añadir
            </Button>
          </div>
          {replace.isError ? (
            <div className="px-3.5 pb-3">
              <ErrorNotice error={replace.error} />
            </div>
          ) : null}
        </NestedCard>
      </section>

      <section>
        <p className="mb-3 font-mono text-[11px] tracking-[0.12em] text-faint">
          SALIDAS · {outcomes.length}
        </p>
        <NestedCard label="tipos de decisión">
          {outcomes.length ? (
            <ul className="divide-y divide-hairline">
              {outcomes.map((outcome) => (
                <li key={outcome.nombre} className="flex items-center gap-3 px-3.5 py-2.5">
                  <span className="min-w-0 flex-1 font-mono text-[12px]">{outcome.nombre}</span>
                  <span className="font-mono text-[11px] text-faint">p{outcome.prioridad}</span>
                  {outcome.por_defecto ? (
                    <span className="text-[11px] text-muted">por defecto</span>
                  ) : null}
                  {outcome.requiere_persona ? (
                    <span className="text-[11px] text-escalar">persona</span>
                  ) : null}
                </li>
              ))}
            </ul>
          ) : (
            <Empty>Sin tipos de decisión.</Empty>
          )}
        </NestedCard>
      </section>
    </div>
  )
}

function VersionChip({
  label,
  hash,
  stamp,
  findings,
}: {
  label: string
  hash: string
  stamp: string | undefined
  findings: Finding[]
}) {
  const [open, setOpen] = useState(false)
  const root = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const onPointer = (event: MouseEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false)
    }
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', onPointer)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onPointer)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  return (
    <div ref={root} className="relative shrink-0">
      <button
        type="button"
        aria-expanded={open}
        aria-haspopup="menu"
        onClick={() => setOpen((next) => !next)}
        className="inline-flex items-center gap-1 rounded-full bg-canvas px-2.5 py-1 font-mono text-[11px] text-ink ring-1 ring-line hover:bg-surface"
      >
        {label}
        <ChevronDown
          size={11}
          strokeWidth={1.75}
          className={cn('text-faint transition-transform', open && 'rotate-180')}
        />
      </button>
      {open ? (
        <div
          role="menu"
          className="absolute right-0 z-20 mt-1 w-56 origin-top-right rounded-[12px] bg-surface p-1 shadow-float ring-1 ring-line"
        >
          <div className="px-2.5 py-2">
            <p className="font-mono text-[12px] text-ink">{label} · en vigor</p>
            <p className="mt-0.5 font-mono text-[10px] text-faint">
              {hash || 'sin hash'}
              {stamp ? ` · ${formatRunDate(stamp)}` : ''}
            </p>
          </div>
          <button
            type="button"
            role="menuitem"
            className="flex w-full rounded-[8px] px-2.5 py-1.5 text-left text-[12px] text-muted hover:bg-canvas hover:text-ink"
            onClick={() => setOpen(false)}
          >
            {findings.length
              ? `Backtesting · ${findings.length} contradicción${findings.length === 1 ? '' : 'es'}`
              : 'Backtesting contra el histórico'}
          </button>
          {findings.length ? (
            <ul className="max-h-40 overflow-y-auto border-t border-hairline py-1">
              {findings.slice(0, 6).map((finding) => (
                <li key={finding.id} className="px-2.5 py-1 text-[11px] leading-4 text-muted">
                  {finding.tipo.replaceAll('_', ' ')}
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}

function ProposalCard({
  proposal,
  outcomes,
  applied,
  busy,
  onChange,
  onApply,
}: {
  proposal: Proposal
  outcomes: string[]
  applied: boolean
  busy: boolean
  onChange: (proposal: Proposal) => void
  onApply: () => void
}) {
  const label =
    proposal.kind === 'add_rule'
      ? 'Alta'
      : proposal.kind === 'retire_rule'
        ? 'Baja'
        : proposal.kind === 'add_symbol'
          ? 'Símbolo'
          : proposal.kind === 'source_note'
            ? 'Fuente'
            : 'Contexto'

  const canApply = proposal.kind !== 'source_note'

  return (
    <li className="rounded-[16px] bg-surface px-4 py-3 ring-1 ring-line">
      <div className="flex items-start justify-between gap-3">
        <p className="font-mono text-[11px] tracking-[0.12em] text-faint">{label}</p>
        {applied ? (
          <span className="text-[12px] text-pagar">Aplicada</span>
        ) : canApply ? (
          <Button tone="primary" disabled={busy} onClick={onApply}>
            Aplicar
          </Button>
        ) : (
          <span className="text-[12px] text-muted">A la derecha</span>
        )}
      </div>

      {proposal.kind === 'add_rule' ? (
        <div className="mt-3 space-y-2">
          <Textarea
            rows={2}
            value={proposal.texto}
            onChange={(event) => onChange({ ...proposal, texto: event.target.value })}
            disabled={applied}
          />
          <div className="flex gap-2">
            <Select
              value={proposal.tipo}
              disabled={applied}
              onChange={(event) =>
                onChange({ ...proposal, tipo: event.target.value as RuleKind })
              }
            >
              <option value="requisito">Requisito</option>
              <option value="prohibicion">Prohibición</option>
            </Select>
            <Select
              value={proposal.decision}
              disabled={applied}
              onChange={(event) => onChange({ ...proposal, decision: event.target.value })}
            >
              {outcomes.map((outcome) => (
                <option key={outcome} value={outcome}>
                  {outcome}
                </option>
              ))}
            </Select>
          </div>
        </div>
      ) : proposal.kind === 'add_symbol' ? (
        <p className="mt-2 text-[13px] leading-6 text-ink">
          <span className="font-mono text-[12px]">{proposal.nombre}</span>
          <span className="text-faint"> · {proposal.tipo}</span>
          <span className="mt-1 block text-muted">{proposal.descripcion}</span>
        </p>
      ) : (
        <p className="mt-2 text-[13px] leading-6 text-ink">{proposal.texto}</p>
      )}
    </li>
  )
}

function Composer({
  placeholder,
  draft,
  onDraft,
  focusTick,
  onSend,
}: {
  placeholder: string
  draft: string
  onDraft: (text: string) => void
  focusTick: number
  onSend: (text: string, files: Attachment[]) => void
}) {
  const input = useRef<HTMLInputElement>(null)
  const box = useRef<HTMLDivElement>(null)
  const [files, setFiles] = useState<Attachment[]>([])
  const [over, setOver] = useState(false)

  useEffect(() => {
    if (!focusTick) return
    const field = box.current?.querySelector('textarea')
    if (!field) return
    field.focus()
    const end = field.value.length
    field.setSelectionRange(end, end)
  }, [focusTick])

  const send = () => {
    const prompt = draft.trim()
    if (!prompt && files.length === 0) return
    onSend(prompt || 'Revisa los adjuntos y propone cambios.', files)
    onDraft('')
    setFiles([])
  }

  const addFiles = (incoming: File[]) => {
    setFiles((current) => [...current, ...incoming.map(toPreview)])
  }

  const remove = (id: string) => {
    setFiles((current) => {
      const gone = current.find((item) => item.id === id)
      if (gone) revokePreview(gone)
      return current.filter((item) => item.id !== id)
    })
  }

  return (
    <div className="shrink-0 border-t border-hairline px-5 py-4">
      <div
        ref={box}
        className={cn(
          'rounded-[16px] bg-surface p-2 ring-1 transition-colors',
          over ? 'ring-focus' : 'ring-line',
        )}
        onDragOver={(event) => {
          event.preventDefault()
          setOver(true)
        }}
        onDragLeave={() => setOver(false)}
        onDrop={(event) => {
          event.preventDefault()
          setOver(false)
          addFiles([...event.dataTransfer.files])
        }}
      >
        {files.length ? (
          <ul className="mb-1.5 flex flex-wrap gap-2 px-1.5 pt-1">
            {files.map((file) => (
              <li key={file.id}>
                <FileChip file={file} onRemove={() => remove(file.id)} />
              </li>
            ))}
          </ul>
        ) : null}
        <Textarea
          rows={3}
          value={draft}
          onChange={(event) => onDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) {
              event.preventDefault()
              send()
            }
          }}
          placeholder={placeholder}
          className="border-0 bg-transparent ring-0"
        />
        <div className="flex items-center justify-between px-1 pb-0.5">
          <button
            type="button"
            onClick={() => input.current?.click()}
            className="grid h-8 w-8 place-items-center rounded-full text-muted hover:bg-canvas hover:text-ink"
            title="Adjuntar"
          >
            <Paperclip size={14} strokeWidth={1.6} />
          </button>
          <Button
            tone="primary"
            disabled={!draft.trim() && files.length === 0}
            onClick={send}
            className="h-8 px-3"
          >
            <ArrowUp size={13} strokeWidth={2} />
            Proponer
          </Button>
        </div>
      </div>
      <input
        ref={input}
        type="file"
        multiple
        hidden
        accept="image/*,.pdf,.xlsx,.xls,.csv,.ods,.docx,.doc,.pptx,.ppt,.json,.txt,.md,.zip,.xml"
        onChange={(event) => {
          addFiles([...(event.target.files ?? [])])
          event.target.value = ''
        }}
      />
      <p className="mt-2 px-1 text-[11px] text-faint">
        ⌘⏎ para enviar. Los adjuntos enseñan al proceso, no entran al lote.
      </p>
    </div>
  )
}

function proposalsFrom(
  pane: DefinitionTabId,
  prompt: string,
  rules: Rule[],
  symbols: ProcessSymbol[],
  fallbackDecision: string,
): Proposal[] {
  const text = prompt.trim()
  const lower = text.toLowerCase()

  if (pane === 'contexto') {
    return [{ id: crypto.randomUUID(), kind: 'update_context', texto: text }]
  }

  if (pane === 'inputs') {
    const slug =
      lower.match(/[a-z][a-z0-9_]{1,32}/)?.[0] ??
      (text
        .normalize('NFD')
        .replace(/\p{M}/gu, '')
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '_')
        .replace(/^_|_$/g, '')
        .slice(0, 24) || 'campo')
    const taken = new Set(symbols.map((item) => item.nombre))
    let nombre = slug
    let n = 2
    while (taken.has(nombre)) {
      nombre = `${slug}_${n}`
      n += 1
    }
    return [
      {
        id: crypto.randomUUID(),
        kind: 'add_symbol',
        nombre,
        tipo: /\b(numero|importe|cantidad|iva|total|base)\b/.test(lower) ? 'numero' : 'texto',
        descripcion: text || nombre,
      },
    ]
  }

  if (pane === 'fuentes') {
    return [
      {
        id: crypto.randomUUID(),
        kind: 'source_note',
        texto: text
          ? `Cárgalo a la derecha: ${text}`
          : 'El Excel o el ERP se suben en el panel de la derecha.',
      },
    ]
  }

  const items: Proposal[] = []
  const retire = rules.find((rule) => {
    const snippet = rule.texto.slice(0, 28).toLowerCase()
    return (
      snippet.length > 12 &&
      lower.includes(snippet) &&
      /\b(quita|elimina|borra|retira|deja de)\b/.test(lower)
    )
  })
  if (retire) {
    items.push({
      id: crypto.randomUUID(),
      kind: 'retire_rule',
      ruleId: retire.id,
      texto: `Retirar: ${retire.texto}`,
    })
  }

  if (/\b(normaliza|convenci[oó]n|contexto|instrucci[oó]n|tolerancia)\b/.test(lower)) {
    items.push({
      id: crypto.randomUUID(),
      kind: 'update_context',
      texto: text,
    })
  }

  if (!retire || text.length > 40) {
    items.push({
      id: crypto.randomUUID(),
      kind: 'add_rule',
      texto: text || 'Nueva comprobación a partir de los adjuntos.',
      tipo: /\bno debe|prohib|nunca\b/.test(lower) ? 'prohibicion' : 'requisito',
      decision: fallbackDecision,
    })
  }

  return items
}
