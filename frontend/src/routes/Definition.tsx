import { useState } from 'react'
import { Link, useLocation, useParams } from 'react-router'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus, X } from 'lucide-react'
import { api, ApiError } from '../api/client'
import { keys } from '../api/queries'
import type {
  ProcessDetail,
  SymbolIn,
  SymbolIO,
} from '../api/contracts'
import { VersionChip, VersionView } from '../components/process/ProcessVersions'
import { useDraft } from '../components/process/useDraft'
import { RulesPane } from '../components/process/RulesPane'
import { DefinitionSwitch } from '../components/process/DefinitionSwitch'
import { ProcessScreen } from '../components/process/ProcessScreen'
import { TruthSources } from '../components/process/TruthSources'
import { Button, Input, Select, Textarea } from '../components/shell/Controls'
import { ErrorNotice, Empty, Notice } from '../components/shell/Notice'
import { ExpandableText } from '../components/shell/ExpandableText'
import { NestedCard } from '../components/shell/Well'
import { t } from '../i18n'
import { definitionTabFromPath } from '../lib/definitionTabs'
import { paths } from '../lib/paths'
import { useSession } from '../state/session'

/** A stale revision means someone else edited the draft. */
function draftError(error: unknown): unknown {
  return error instanceof ApiError && error.status === 409
    ? new ApiError(409, error.code, 'Recarga: alguien cambió el borrador')
    : error
}

export function Definition() {
  const processId = Number(useParams().processId)
  const location = useLocation()
  const pane = definitionTabFromPath(location.pathname)
  const { isManager } = useSession()

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
      query.state.data?.some((rule) => rule.status === 'compiling') ? 2_000 : false,
  })

  const all = rules.data ?? []
  const outcomes = process.data?.decision_types.map((outcome) => outcome.name) ?? []
  const history = [...(versions.data ?? [])].sort((a, b) => b.number - a.number)
  const latestVersion = history[0]
  // A selected version is read only; null shows the live definition panes.
  const [viewing, setViewing] = useState<number | null>(null)
  const viewed = history.find((version) => version.id === viewing)

  return (
    <ProcessScreen
      processId={processId}
      crumbs={[
        { label: 'Procesos', to: paths.processes },
        { label: process.data?.name ?? '…', to: paths.process(processId) },
        { label: 'Definición' },
      ]}
      actions={isManager ? (
        <Link to={paths.processChat(processId)}>
          <Button tone="ghost">Volver al chat</Button>
        </Link>
      ) : undefined}
    >
      <div className="min-h-0 flex-1 overflow-y-auto px-5 py-5">
        <header className="mx-auto flex max-w-5xl items-start justify-between gap-3 border-b border-hairline pb-3">
          <DefinitionSwitch processId={processId} />
          <VersionChip
            versions={history}
            selected={viewed ?? latestVersion}
            onSelect={(version) => setViewing(version.id)}
            findings={findings.data ?? []}
          />
        </header>
        <div className="mx-auto max-w-5xl py-5">
          {viewed && latestVersion ? (
            <VersionView
              key={viewed.id}
              processId={processId}
              version={viewed}
              current={latestVersion}
              rules={all}
              onBack={() => setViewing(null)}
            />
          ) : null}
          {viewed ? null : pane === 'normas' ? (
            <RulesPane processId={processId} rules={all} outcomes={outcomes} />
          ) : null}
          {!viewed && pane === 'contexto' ? (
            <ContextPane processId={processId} process={process.data} />
          ) : null}
          {!viewed && pane === 'inputs' ? (
            <InputsPane processId={processId} process={process.data} />
          ) : null}
          {!viewed && pane === 'fuentes' ? <TruthSources processId={processId} /> : null}
        </div>
      </div>
    </ProcessScreen>
  )
}

function ContextPane({
  processId,
  process,
}: {
  processId: number
  process: ProcessDetail | undefined
}) {
  const queryClient = useQueryClient()
  const { revision, snapshot } = useDraft(processId)
  // The draft's description when one exists, else the published one.
  const current =
    typeof snapshot?.description === 'string' ? snapshot.description : (process?.description ?? '')
  const [text, setText] = useState<string | null>(null)
  const value = text ?? current

  // Only the description: every other field of the draft keeps its value.
  const save = useMutation({
    mutationFn: () =>
      api.saveDraft(processId, {
        ...(revision != null ? { expected_revision: revision } : {}),
        description: value.trim(),
        refresh_agents: false,
      }),
    onSuccess: () => {
      setText(null)
      void queryClient.invalidateQueries({ queryKey: keys.execution(processId) })
      void queryClient.invalidateQueries({ queryKey: keys.draft(processId) })
    },
  })

  const dirty = value.trim() !== current.trim()
  // Read first: the lead sentence, the conventions one click away. Editing is asked for.
  const editing = text != null || !current.trim()

  return (
    <NestedCard
      label="convenciones del agente"
      action={
        editing && current.trim() ? (
          <Button tone="ghost" disabled={save.isPending} onClick={() => setText(null)}>
            Cancelar
          </Button>
        ) : !editing ? (
          <Button tone="ghost" onClick={() => setText(current)}>
            Editar
          </Button>
        ) : null
      }
    >
      <div className="space-y-3 px-3.5 py-3">
        {editing ? (
          <>
            <Textarea
              rows={8}
              value={value}
              onChange={(event) => setText(event.target.value)}
              placeholder="NIF en mayúsculas, sin espacios. Importes en euros. Si falta el pedido, ESCALAR."
            />
            <div className="flex items-center justify-between gap-3">
              <p className="text-[11px] text-faint">
                Entra en cada compilación. No es una regla: es el marco. Queda en el borrador.
              </p>
              <Button
                tone="primary"
                disabled={!dirty || !process || save.isPending}
                onClick={() => save.mutate()}
              >
                {save.isPending ? 'Guardando…' : 'Guardar'}
              </Button>
            </div>
          </>
        ) : (
          <ExpandableText text={current} className="text-[13px] leading-6 text-ink" />
        )}
        {save.isError ? <ErrorNotice error={draftError(save.error)} /> : null}
        {save.isSuccess ? <DraftSaved processId={processId} /> : null}
      </div>
    </NestedCard>
  )
}

function DraftSaved({ processId }: { processId: number }) {
  return (
    <Notice
      title="Queda en el borrador. Publica para que se aplique"
      action={
        <Link
          to={`${paths.panel(processId)}?publicar=1`}
          className="text-[12px] text-muted hover:text-ink"
        >
          Publicar
        </Link>
      }
    />
  )
}

const SYMBOL_TYPES = ['text', 'number', 'date'] as const

function InputsPane({
  processId,
  process,
}: {
  processId: number
  process: ProcessDetail | undefined
}) {
  const queryClient = useQueryClient()
  const { revision, snapshot } = useDraft(processId)
  // The draft's symbols when one exists, with `required` and `extraction` as they are.
  const symbols: SymbolIO[] = Array.isArray(snapshot?.symbols)
    ? (snapshot.symbols as SymbolIO[])
    : (process?.symbols ?? [])
  const outcomes = process?.decision_types ?? []
  const [draft, setDraft] = useState({ name: '', type: 'text', description: '' })

  // Always the full list, so no symbol loses what the form does not show.
  const replace = useMutation({
    mutationFn: (next: SymbolIO[]) =>
      api.saveDraft(processId, {
        ...(revision != null ? { expected_revision: revision } : {}),
        // The backend accepts only its enum; what it sent back is already in it.
        symbols: next as SymbolIn[],
        refresh_agents: false,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: keys.execution(processId) })
      void queryClient.invalidateQueries({ queryKey: keys.draft(processId) })
    },
  })

  const add = () => {
    const name = draft.name.trim()
    if (!name) return
    if (symbols.some((item) => item.name === name)) return
    replace.mutate([
      ...symbols,
      { name, type: draft.type, description: draft.description.trim(), required: false },
    ])
    setDraft({ name: '', type: 'text', description: '' })
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
                <li key={symbol.name} className="flex items-start gap-3 px-3.5 py-2.5">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-baseline gap-2">
                      <span className="font-mono text-[12px]">{symbol.name}</span>
                      <span className="text-[11px] text-faint">
                        {t(`symbolType.${symbol.type}`)}
                      </span>
                    </div>
                    <ExpandableText
                      text={symbol.description ?? ''}
                      className="mt-0.5 text-[12px] leading-5 text-muted"
                    />
                  </div>
                  <button
                    type="button"
                    className="grid h-6 w-6 shrink-0 place-items-center rounded-full text-faint hover:bg-canvas hover:text-ink"
                    title="Quitar"
                    onClick={() =>
                      replace.mutate(symbols.filter((item) => item.name !== symbol.name))
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
              value={draft.name}
              onChange={(event) => setDraft((current) => ({ ...current, name: event.target.value }))}
              placeholder="issuer_nif"
            />
            <div className="grid grid-cols-[7rem_minmax(0,1fr)] gap-2">
              <Select
                value={draft.type}
                onChange={(event) => setDraft((current) => ({ ...current, type: event.target.value }))}
              >
                {SYMBOL_TYPES.map((type) => (
                  <option key={type} value={type}>
                    {t(`symbolType.${type}`)}
                  </option>
                ))}
              </Select>
              <Input
                value={draft.description}
                onChange={(event) =>
                  setDraft((current) => ({ ...current, description: event.target.value }))
                }
                placeholder="NIF del emisor, sin espacios."
              />
            </div>
            <Button tone="soft" disabled={!draft.name.trim() || replace.isPending} onClick={add}>
              <Plus size={12} strokeWidth={2} />
              Añadir
            </Button>
          </div>
          {replace.isError ? (
            <div className="px-3.5 pb-3">
              <ErrorNotice error={draftError(replace.error)} />
            </div>
          ) : null}
          {replace.isSuccess ? (
            <div className="px-3.5 pb-3">
              <DraftSaved processId={processId} />
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
                <li key={outcome.name} className="flex items-center gap-3 px-3.5 py-2.5">
                  <span className="min-w-0 flex-1 font-mono text-[12px]">{outcome.name}</span>
                  <span className="font-mono text-[11px] text-faint">p{outcome.priority}</span>
                  {outcome.is_default ? (
                    <span className="text-[11px] text-muted">por defecto</span>
                  ) : null}
                  {outcome.requires_human ? (
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
