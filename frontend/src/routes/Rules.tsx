import { useState } from 'react'
import { useNavigate, useParams } from 'react-router'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus } from 'lucide-react'
import { api } from '../api/client'
import { keys } from '../api/queries'
import type { RuleInput, RuleKind, RuleState } from '../api/contracts'
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
  })

  const create = useMutation({
    mutationFn: (body: RuleInput) => api.createRule(processId, body),
    // Adding a rule and compiling it is one move: the rule page picks it up.
    onSuccess: (rule) => {
      void queryClient.invalidateQueries({ queryKey: ['rules'] })
      navigate(`${paths.rule(processId, rule.id)}?compile=1`)
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
          { label: 'Reglas' },
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
          kicker="Reglas"
          title="Reglas del proceso"
          description="Se escriben en texto. Al crearla, dos agentes independientes la compilan a código con sus tests, se cruzan los tests y se comprueba el histórico. Tarda entre 30 y 60 segundos, y hasta que no sale limpia no se puede activar."
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

        <div className="mb-3 mt-6">
          <Segmented
            value={filter}
            onChange={setFilter}
            options={[
              { value: 'todas', label: 'Todas', count: all.length },
              { value: 'activa', label: 'Activas', count: count('activa') },
              { value: 'borrador', label: 'Borrador', count: count('borrador') },
              { value: 'rechazada', label: 'Rechazadas', count: count('rechazada') },
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
