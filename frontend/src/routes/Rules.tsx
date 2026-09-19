import { useState } from 'react'
import { useNavigate, useParams } from 'react-router'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { BookOpenText, Plus } from 'lucide-react'
import { api } from '../api/client'
import { keys } from '../api/queries'
import type { NormRule, RuleInput, RuleKind, RuleState } from '../api/contracts'
import { Button, Field, Segmented, Select, Textarea } from '../components/shell/Controls'
import { DataTable } from '../components/shell/DataTable'
import { Empty, ErrorNotice } from '../components/shell/Notice'
import { StatusBadge } from '../components/shell/StatusBadge'
import { Topbar } from '../components/shell/Topbar'
import { NestedCard, PageIntro } from '../components/shell/Well'
import { paths } from '../lib/paths'

type Filter = RuleState | 'todas'

export function Rules() {
  const processId = Number(useParams().processId)
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [filter, setFilter] = useState<Filter>('todas')
  const [formOpen, setFormOpen] = useState(false)

  const process = useQuery({
    queryKey: keys.process(processId),
    queryFn: () => api.getProcess(processId),
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

  const create = useMutation({
    mutationFn: (body: RuleInput) => api.createRule(processId, body),
    // Saving starts background compilation; the rule page polls while it runs.
    onSuccess: (rule) => {
      void queryClient.invalidateQueries({ queryKey: ['rules'] })
      navigate(paths.rule(processId, rule.id))
    },
  })

  const all = rules.data ?? []
  const count = (state: RuleState) => all.filter((rule) => rule.estado === state).length
  const rows = filter === 'todas' ? all : all.filter((rule) => rule.estado === filter)

  return (
    <>
      <Topbar
        crumbs={[
          { label: 'Procesos', to: paths.processes },
          { label: process.data?.nombre ?? '…', to: paths.process(processId) },
          { label: 'Reglas y versiones' },
        ]}
        actions={
          <Button tone="primary" onClick={() => setFormOpen((open) => !open)}>
            <Plus size={12} strokeWidth={2} />
            Nueva regla
          </Button>
        }
      />

      <div className="min-h-0 flex-1 overflow-y-auto px-8 pb-10 pt-4">
        <PageIntro
          kicker="Configuración"
          title="Reglas y versiones"
          description="Cada regla conserva su estado, validación y hash. Activa una versión solo cuando sus pruebas y su impacto histórico estén claros."
        />

        {formOpen ? (
          <NewRule
            outcomes={process.data?.tipos_decision.map((outcome) => outcome.nombre) ?? []}
            sending={create.isPending}
            error={create.error}
            onCancel={() => setFormOpen(false)}
            onCreate={(body) => create.mutate(body)}
          />
        ) : null}

        <NormPanel
          rows={norm.data ?? []}
          loading={norm.isLoading}
          onNormalized={() => {
            void queryClient.invalidateQueries({ queryKey: keys.norm(processId) })
            void queryClient.invalidateQueries({ queryKey: ['rules'] })
          }}
          processId={processId}
        />

        <div className="mb-3 mt-6">
          <Segmented
            value={filter}
            onChange={setFilter}
            options={[
              { value: 'todas', label: 'Todas', count: all.length },
              { value: 'activa', label: 'Activas', count: count('activa') },
              { value: 'compilando', label: 'Compilando', count: count('compilando') },
              { value: 'bloqueada', label: 'Bloqueadas', count: count('bloqueada') },
              { value: 'borrador', label: 'Borrador', count: count('borrador') },
              { value: 'retirada', label: 'Retiradas', count: count('retirada') },
            ]}
          />
        </div>

        {rules.isError ? <ErrorNotice error={rules.error} /> : null}

        <NestedCard label={`${rows.length} reglas`}>
          {rows.length === 0 ? (
            <Empty>No hay reglas en ese estado.</Empty>
          ) : (
            <DataTable
              framed={false}
              rows={rows.map((rule) => ({ ...rule, id: String(rule.id) }))}
              onRowClick={(row) => navigate(paths.rule(processId, row.id))}
              columns={[
                {
                  key: 'texto',
                  header: 'Regla',
                  render: (row) => <span className="text-[13px] text-ink">{row.texto}</span>,
                },
                {
                  key: 'tipo',
                  header: 'Tipo',
                  width: '7rem',
                  render: (row) => <span className="text-[12px] text-muted">{row.tipo}</span>,
                },
                {
                  key: 'decision',
                  header: 'Si salta',
                  width: '8rem',
                  render: (row) => <StatusBadge value={row.decision} />,
                },
                {
                  key: 'estado',
                  header: 'Estado',
                  width: '7rem',
                  render: (row) => <StatusBadge value={row.estado} />,
                },
                {
                  key: 'hash',
                  header: 'Hash',
                  width: '8rem',
                  render: (row) => (
                    <span className="font-mono text-[11px] text-faint">
                      {row.hash ? row.hash.slice(0, 12) : '—'}
                    </span>
                  ),
                },
              ]}
            />
          )}
        </NestedCard>
      </div>
    </>
  )
}

function NormPanel({
  rows,
  loading,
  processId,
  onNormalized,
}: {
  rows: NormRule[]
  loading: boolean
  processId: number
  onNormalized: () => void
}) {
  const [open, setOpen] = useState(false)
  const [text, setText] = useState('')
  const normalize = useMutation({
    mutationFn: () => api.normalizeNorm(processId, text.trim()),
    onSuccess: () => {
      setText('')
      setOpen(false)
      onNormalized()
    },
  })

  return (
    <section className="mt-6">
      <NestedCard
        label={
          <span className="flex items-center gap-1.5">
            <BookOpenText size={12} strokeWidth={1.75} />
            norma del cliente · {rows.length} apartados
          </span>
        }
        action={
          <Button tone="ghost" onClick={() => setOpen((value) => !value)}>
            {open ? 'Cerrar' : rows.length ? 'Añadir norma' : 'Pegar norma'}
          </Button>
        }
      >
        {open ? (
          <div className="border-t border-hairline px-3.5 py-3">
            <Field
              label="Norma en lenguaje natural"
              hint="Conservamos cada frase tal cual. El normalizador la separa en comprobaciones atómicas y las manda a compilar en segundo plano."
            >
              <Textarea
                autoFocus
                rows={6}
                value={text}
                onChange={(event) => setText(event.target.value)}
                placeholder={'1. El proveedor debe estar en el maestro.\\n2. El IBAN debe coincidir…'}
                className="mt-1"
              />
            </Field>
            {normalize.isError ? <ErrorNotice error={normalize.error} /> : null}
            <Button
              tone="primary"
              className="mt-3"
              disabled={!text.trim() || normalize.isPending}
              onClick={() => normalize.mutate()}
            >
              {normalize.isPending ? 'Leyendo la norma…' : 'Convertir en comprobaciones'}
            </Button>
          </div>
        ) : rows.length ? (
          <ul className="divide-y divide-hairline border-t border-hairline">
            {rows.map((row) => (
              <li key={row.id} className="grid gap-2 px-3.5 py-3 md:grid-cols-[2rem_1fr_auto]">
                <span className="font-mono text-[11px] text-faint">
                  {String(row.numero).padStart(2, '0')}
                </span>
                <div>
                  <p className="text-[13px] leading-6">{row.texto}</p>
                  {row.politicas.length ? (
                    <p className="mt-1 text-[11.5px] text-muted">
                      Política: {row.politicas.join(' · ')}
                    </p>
                  ) : null}
                </div>
                <div className="flex flex-wrap items-center justify-end gap-1.5">
                  {row.reglas.map((check) => (
                    <StatusBadge key={check.id} value={check.estado}>
                      {`#${check.id} · ${check.estado}`}
                    </StatusBadge>
                  ))}
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <p className="border-t border-hairline px-3.5 py-5 text-[13px] text-muted">
            {loading
              ? 'Cargando la norma…'
              : 'Pega la norma completa. Verás sus frases y las comprobaciones que salen de cada una.'}
          </p>
        )}
      </NestedCard>
    </section>
  )
}

function NewRule({
  outcomes,
  sending,
  error,
  onCreate,
  onCancel,
}: {
  outcomes: string[]
  sending: boolean
  error: unknown
  onCreate: (body: RuleInput) => void
  onCancel: () => void
}) {
  const [text, setText] = useState('')
  const [kind, setKind] = useState<RuleKind>('requisito')
  const [decision, setDecision] = useState(outcomes[0] ?? '')

  return (
    <form
      className="max-w-2xl"
      onSubmit={(event) => {
        event.preventDefault()
        if (!text.trim()) return
        onCreate({ texto: text.trim(), tipo: kind, decision: decision || outcomes[0] })
      }}
    >
      <NestedCard label="regla nueva">
        <div className="space-y-4 px-3.5 py-3">
          <Field
            label="Qué dice la regla"
            hint="En una frase, como se la contarías a una persona. El compilador escribe el código."
          >
            <Textarea
              autoFocus
              rows={2}
              value={text}
              onChange={(event) => setText(event.target.value)}
              placeholder="El IBAN de la factura coincide con el IBAN del proveedor en el maestro."
              className="mt-1"
            />
          </Field>

          <div className="grid gap-3 sm:grid-cols-2">
            <Field
              label="Tipo"
              hint={
                kind === 'requisito'
                  ? 'Algo que debe cumplirse. Salta si no se cumple.'
                  : 'Algo que no debe darse. Salta si se da.'
              }
            >
              <Select
                value={kind}
                onChange={(event) => setKind(event.target.value as RuleKind)}
                className="mt-1"
              >
                <option value="requisito">Requisito</option>
                <option value="prohibicion">Prohibición</option>
              </Select>
            </Field>

            <Field label="Decisión si salta" hint="Si saltan varias, gana la de mayor prioridad.">
              <Select
                value={decision}
                onChange={(event) => setDecision(event.target.value)}
                className="mt-1"
              >
                {outcomes.map((outcome) => (
                  <option key={outcome} value={outcome}>
                    {outcome}
                  </option>
                ))}
              </Select>
            </Field>
          </div>

          {error ? <ErrorNotice error={error} /> : null}

          <div className="flex gap-2">
            <Button type="submit" tone="primary" disabled={sending || !text.trim()}>
              {sending ? 'Creando…' : 'Crear y compilar'}
            </Button>
            <Button tone="ghost" onClick={onCancel}>
              Cancelar
            </Button>
          </div>
        </div>
      </NestedCard>
    </form>
  )
}
