import { useState } from 'react'
import { useNavigate } from 'react-router'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, X } from 'lucide-react'
import { api } from '../api/client'
import type { DecisionType, Definition } from '../api/contracts'
import { ProcessDraftChat } from '../components/process/ProcessDraftChat'
import { Button, Field, Input, Segmented, Select, Textarea } from '../components/shell/Controls'
import { ErrorNotice, Notice } from '../components/shell/Notice'
import { Topbar } from '../components/shell/Topbar'
import { NestedCard, PageIntro } from '../components/shell/Well'
import { invoiceDecisionTypes, invoiceSymbols } from '../data/seed'
import { t } from '../i18n'
import { paths } from '../lib/paths'

type SymbolIn = Definition['symbols'][number]

const SYMBOL_TYPES = ['text', 'number', 'date'] as const

const EMPTY_OUTCOMES: DecisionType[] = [
  { name: 'REVISAR', priority: 2, is_default: false, requires_human: true },
  { name: 'ACEPTAR', priority: 1, is_default: true, requires_human: false },
]

export function NewProcess() {
  const [tab, setTab] = useState<'chat' | 'form' | 'json'>('chat')

  return (
    <>
      <Topbar
        crumbs={[{ label: 'Procesos', to: paths.processes }, { label: 'Nuevo proceso' }]}
        actions={
          <Segmented
            value={tab}
            onChange={setTab}
            options={[
              { value: 'chat', label: 'Chat' },
              { value: 'form', label: 'A mano' },
              { value: 'json', label: 'Importar JSON' },
            ]}
          />
        }
      />
      {tab === 'chat' ? <ProcessDraftChat /> : tab === 'form' ? <ByHand /> : <FromDefinition />}
    </>
  )
}

/**
 * The whole process as one JSON file, the same shape as the packs under `processes/`,
 * posted as it is. The backend's validation and its 409s are shown as they come.
 */
function FromDefinition() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [text, setText] = useState('')
  const [parseError, setParseError] = useState<string | null>(null)

  const load = useMutation({
    mutationFn: (definition: Definition) => api.loadDefinition(definition),
    onSuccess: (result) => {
      void queryClient.invalidateQueries()
      navigate(paths.processChat(result.process.id))
    },
  })

  const submit = () => {
    setParseError(null)
    let definition: Definition
    try {
      definition = JSON.parse(text)
    } catch (error) {
      setParseError(error instanceof Error ? error.message : 'JSON inválido')
      return
    }
    load.mutate(definition)
  }

  return (
    <div className="min-h-0 flex-1 overflow-y-auto px-4 pb-10 pt-4 sm:px-6">
      <PageIntro
        kicker="Proceso · importar"
        title="Un proceso entero como datos"
        description="Pega aquí un fichero de processes/. Trae los tipos de decisión, los símbolos, las reglas en texto y los usuarios. Las reglas entran como borrador: se compilan y se añaden a la versión desde la aplicación."
      />

      <div className="max-w-3xl space-y-3">
        <NestedCard
          label="process.json"
          action={
            <Button tone="ghost" onClick={() => setText(EXAMPLE)}>
              Cargar un ejemplo
            </Button>
          }
        >
          <div className="space-y-3 px-3.5 py-3">
            <Textarea
              rows={18}
              value={text}
              onChange={(event) => setText(event.target.value)}
              placeholder='{ "name": "Travel expenses", "decision_types": [...] }'
              className="font-mono text-[12px] leading-5"
              spellCheck={false}
            />
            {parseError ? (
              <Notice tone="error" title="Eso no es JSON válido">
                {parseError}
              </Notice>
            ) : null}
            {load.isError ? <ErrorNotice error={load.error} /> : null}
            <div className="flex items-center gap-2">
              <Button
                tone="primary"
                onClick={submit}
                disabled={load.isPending || !text.trim()}
              >
                {load.isPending ? 'Cargando…' : 'Cargar el proceso'}
              </Button>
              <p className="text-[12px] text-faint">
                Se puede repetir sin miedo: nada de lo que ya decidiste se sobrescribe.
              </p>
            </div>
          </div>
        </NestedCard>
      </div>
    </div>
  )
}

function ByHand() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [outcomes, setOutcomes] = useState<DecisionType[]>(EMPTY_OUTCOMES)
  const [symbols, setSymbols] = useState<SymbolIn[]>([])

  const create = useMutation({
    mutationFn: (body: Definition) => api.loadDefinition(body),
    onSuccess: (result) => {
      void queryClient.invalidateQueries({ queryKey: ['processes'] })
      navigate(paths.processChat(result.process.id))
    },
  })

  const useTemplate = () => {
    setName('Pago de facturas')
    setDescription(
      'Decide si se paga cada factura de proveedor según la Norma_Pagos_v3. Fuentes: proveedores, pedidos y erp. Convenciones de todas las reglas: NIF, IBAN y pedido se normalizan a mayúsculas sin espacios antes de comparar; los importes se comparan en céntimos con Decimal.',
    )
    setOutcomes(invoiceDecisionTypes)
    setSymbols(invoiceSymbols as SymbolIn[])
  }

  const defaults = outcomes.filter((outcome) => outcome.is_default).length
  const defaultNeedsPerson = outcomes.some(
    (outcome) => outcome.is_default && outcome.requires_human,
  )
  const anyHuman = outcomes.some((outcome) => outcome.requires_human)
  const valid = name.trim().length > 0 && defaults === 1 && !defaultNeedsPerson && anyHuman

  const patch = (index: number, change: Partial<DecisionType>) =>
    setOutcomes((current) =>
      current.map((outcome, i) => (i === index ? { ...outcome, ...change } : outcome)),
    )

  return (
    <form
      className="min-h-0 flex-1 overflow-y-auto px-4 pb-10 pt-4 sm:px-6"
      onSubmit={(event) => {
        event.preventDefault()
        if (!valid) return
        create.mutate({
          name: name.trim(),
          description: description.trim(),
          decision_types: outcomes,
          symbols,
          rules: [],
          users: [],
        })
      }}
    >
      <PageIntro
        kicker="Proceso · nuevo"
        title="Nuevo proceso"
        description="Un proceso son sus tipos de decisión, sus símbolos y sus reglas. Empieza por lo primero: las reglas se añaden una a una después, y cada una se compila y se valida por su cuenta."
      />

      <div className="max-w-2xl space-y-3">
        <NestedCard
          label="proceso"
          action={
            <Button tone="ghost" onClick={useTemplate}>
              Usar la plantilla de facturas
            </Button>
          }
        >
          <div className="space-y-4 px-3.5 py-3">
            <Field label="Nombre">
              <Input
                autoFocus
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="Pago de facturas"
                className="mt-1"
              />
            </Field>
            <Field
              label="Qué decide y con qué convenciones"
              hint="Los agentes reciben este texto como contexto de cada regla: normalización, unidades, tolerancias, qué hacer si falta un valor."
            >
              <Textarea
                rows={3}
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                placeholder="Para cada factura, si se paga, no se paga o la ve una persona."
                className="mt-1"
              />
            </Field>
          </div>
        </NestedCard>

        <NestedCard
          label="tipos de decisión"
          action={
            <Button
              tone="ghost"
              onClick={() =>
                setOutcomes((current) => [
                  ...current,
                  {
                    name: '',
                    priority: current.length + 1,
                    is_default: false,
                    requires_human: false,
                  },
                ])
              }
            >
              <Plus size={12} strokeWidth={2} />
              Añadir
            </Button>
          }
        >
          <div className="space-y-2 px-3.5 py-3">
            <p className="text-[12px] text-muted">
              Si saltan varias reglas gana la de mayor prioridad. El tipo por defecto es el que sale
              cuando no salta ninguna. Los marcados con «persona» van a la cola del responsable, y
              hace falta al menos uno: es donde el motor deja lo que no puede decidir.
            </p>
            {outcomes.map((outcome, index) => (
              <div key={index} className="flex flex-wrap items-center gap-2">
                <Input
                  value={outcome.name}
                  onChange={(event) => patch(index, { name: event.target.value.toUpperCase() })}
                  placeholder="ESCALAR"
                  className="w-40 shrink-0 font-mono"
                />
                <Input
                  type="number"
                  min={1}
                  value={outcome.priority}
                  onChange={(event) => patch(index, { priority: Number(event.target.value) })}
                  className="w-16 shrink-0 text-center"
                  title="Prioridad"
                />
                <label className="flex shrink-0 items-center gap-1.5 text-[12px] text-muted">
                  <input
                    type="radio"
                    name="por_defecto"
                    checked={outcome.is_default}
                    onChange={() =>
                      setOutcomes((current) =>
                        current.map((item, i) => ({ ...item, is_default: i === index })),
                      )
                    }
                  />
                  por defecto
                </label>
                <label className="flex shrink-0 items-center gap-1.5 text-[12px] text-muted">
                  <input
                    type="checkbox"
                    checked={outcome.requires_human}
                    onChange={(event) => patch(index, { requires_human: event.target.checked })}
                  />
                  persona
                </label>
                <Button
                  tone="ghost"
                  onClick={() => setOutcomes((current) => current.filter((_, i) => i !== index))}
                  className="ml-auto shrink-0 px-2"
                  title="Quitar"
                >
                  <X size={13} strokeWidth={2} />
                </Button>
              </div>
            ))}
            {defaults !== 1 ? (
              <p className="text-[12px] text-nopagar">
                Marca exactamente un tipo por defecto. Ahora hay {defaults}.
              </p>
            ) : null}
            {defaultNeedsPerson ? (
              <p className="text-[12px] text-nopagar">
                El tipo por defecto no puede requerir persona: es lo que sale cuando todo va bien.
              </p>
            ) : null}
            {!anyHuman ? (
              <p className="text-[12px] text-nopagar">
                Marca al menos un tipo como «persona». Sin eso el motor no tiene dónde dejar un caso
                que no puede decidir.
              </p>
            ) : null}
          </div>
        </NestedCard>

        <NestedCard
          label="símbolos"
          action={
            <Button
              tone="ghost"
              onClick={() =>
                setSymbols((current) => [
                  ...current,
                  { name: '', type: 'text', description: '', required: false },
                ])
              }
            >
              <Plus size={12} strokeWidth={2} />
              Añadir
            </Button>
          }
        >
          <div className="space-y-2 px-3.5 py-3">
            <p className="text-[12px] text-muted">
              Los datos con nombre que usan las reglas. Se pueden cambiar después: si una regla
              nueva pide un símbolo que falta, se saca del texto ya guardado.
            </p>
            {symbols.length === 0 ? (
              <p className="text-[12px] text-faint">Ninguno todavía.</p>
            ) : null}
            {symbols.map((symbol, index) => (
              <div key={index} className="flex items-center gap-2">
                <Input
                  value={symbol.name}
                  onChange={(event) =>
                    setSymbols((current) =>
                      current.map((item, i) =>
                        i === index ? { ...item, name: event.target.value } : item,
                      ),
                    )
                  }
                  placeholder="iban"
                  className="w-40 shrink-0 font-mono"
                />
                <Select
                  value={symbol.type}
                  onChange={(event) =>
                    setSymbols((current) =>
                      current.map((item, i) =>
                        i === index
                          ? { ...item, type: event.target.value as SymbolIn['type'] }
                          : item,
                      ),
                    )
                  }
                  className="w-28 shrink-0"
                >
                  {SYMBOL_TYPES.map((type) => (
                    <option key={type} value={type}>
                      {t(`symbolType.${type}`)}
                    </option>
                  ))}
                </Select>
                <Input
                  value={symbol.description}
                  onChange={(event) =>
                    setSymbols((current) =>
                      current.map((item, i) =>
                        i === index ? { ...item, description: event.target.value } : item,
                      ),
                    )
                  }
                  placeholder="IBAN de cobro que figura en la factura"
                />
                <Button
                  tone="ghost"
                  onClick={() => setSymbols((current) => current.filter((_, i) => i !== index))}
                  className="shrink-0 px-2"
                  title="Quitar"
                >
                  <X size={13} strokeWidth={2} />
                </Button>
              </div>
            ))}
          </div>
        </NestedCard>

        {create.isError ? <ErrorNotice error={create.error} /> : null}

        <div className="flex gap-2 pt-2">
          <Button type="submit" tone="primary" disabled={!valid || create.isPending}>
            {create.isPending ? 'Creando…' : 'Crear proceso'}
          </Button>
          <Button tone="ghost" onClick={() => navigate(-1)}>
            Cancelar
          </Button>
        </div>
        <p className="text-[12px] text-faint">
          Al crearlo vas a Definición. Ahí están la norma, el contexto, los inputs y las fuentes de verdad.
        </p>
      </div>
    </form>
  )
}

/** `processes/travel-expenses.json`, as it is in the repo. */
const EXAMPLE = JSON.stringify(
  {
    name: 'Travel expenses',
    description:
      'Approves or rejects each expense report of a business trip. Conventions for every rule: amount is in euros and is compared with Decimal(str(amount)); if a symbol the rule needs is missing (None), the rule does not fire.',
    decision_types: [
      { name: 'ESCALATE', priority: 3, requires_human: true },
      { name: 'REJECT', priority: 2 },
      { name: 'APPROVE', priority: 1, is_default: true },
    ],
    symbols: [
      { name: 'employee', type: 'text', description: 'Email of the travelling employee.' },
      { name: 'amount', type: 'number', description: 'Total of the report in euros.' },
      { name: 'has_receipt', type: 'boolean', description: 'The report attaches a receipt.' },
    ],
    rules: [
      { text: '`has_receipt` is true.', type: 'requirement', decision: 'REJECT' },
      { text: '`amount` is greater than 500.', type: 'prohibition', decision: 'ESCALATE' },
    ],
  },
  null,
  2,
)
