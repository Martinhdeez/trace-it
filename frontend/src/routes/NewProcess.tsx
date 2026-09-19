import { useState } from 'react'
import { useNavigate } from 'react-router'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, X } from 'lucide-react'
import { api } from '../api/client'
import type { Outcome, ProcessDefinition, ProcessInput, ProcessSymbol } from '../api/contracts'
import { Button, Field, Input, Segmented, Select, Textarea } from '../components/shell/Controls'
import { ErrorNotice, Notice } from '../components/shell/Notice'
import { Topbar } from '../components/shell/Topbar'
import { NestedCard, PageIntro } from '../components/shell/Well'
import { invoiceOutcomes, invoiceSymbols } from '../data/seed'
import { paths } from '../lib/paths'

const EMPTY_OUTCOMES: Outcome[] = [
  { nombre: 'REVISAR', prioridad: 2, por_defecto: false, requiere_persona: true },
  { nombre: 'ACEPTAR', prioridad: 1, por_defecto: true, requiere_persona: false },
]

export function NewProcess() {
  const [tab, setTab] = useState<'form' | 'json'>('form')

  return (
    <>
      <Topbar
        crumbs={[{ label: 'Procesos', to: paths.processes }, { label: 'Nuevo proceso' }]}
        actions={
          <Segmented
            value={tab}
            onChange={setTab}
            options={[
              { value: 'form', label: 'A mano' },
              { value: 'json', label: 'Importar JSON' },
            ]}
          />
        }
      />
      {tab === 'form' ? <ByHand /> : <FromDefinition />}
    </>
  )
}

/**
 * The whole process as one JSON file, the same one the backend loads from
 * `procesos/`. Loading it twice is safe: rules whose text already exists are
 * left alone, so a pack can be edited and loaded again.
 */
function FromDefinition() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [text, setText] = useState('')
  const [parseError, setParseError] = useState<string | null>(null)

  const load = useMutation({
    mutationFn: (definition: ProcessDefinition) => api.loadDefinition(definition),
    onSuccess: (result) => {
      void queryClient.invalidateQueries()
      navigate(paths.process(result.proceso.id))
    },
  })

  const submit = () => {
    setParseError(null)
    let definition: ProcessDefinition
    try {
      definition = JSON.parse(text)
    } catch (error) {
      setParseError(error instanceof Error ? error.message : 'JSON inválido')
      return
    }
    load.mutate(definition)
  }

  return (
    <div className="min-h-0 flex-1 overflow-y-auto px-8 pb-10 pt-4">
      <PageIntro
        kicker="Proceso · importar"
        title="Un proceso entero como datos"
        description="Pega aquí un fichero de procesos/. Trae los tipos de decisión, los símbolos, las reglas en texto y los usuarios. Las reglas entran como borrador: se compilan y se activan una a una desde la aplicación."
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
              placeholder='{ "nombre": "Gastos de viaje", "tipos_decision": [...] }'
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
  const [outcomes, setOutcomes] = useState<Outcome[]>(EMPTY_OUTCOMES)
  const [symbols, setSymbols] = useState<ProcessSymbol[]>([])

  const create = useMutation({
    mutationFn: (body: ProcessInput) => api.createProcess(body),
    onSuccess: (process) => {
      void queryClient.invalidateQueries({ queryKey: ['processes'] })
      navigate(paths.definition(process.id))
    },
  })

  const useTemplate = () => {
    setName('Pago de facturas')
    setDescription(
      'Decide si se paga cada factura de proveedor según la Norma_Pagos_v3. Fuentes: proveedores, pedidos y erp. Convenciones de todas las reglas: NIF, IBAN y pedido se normalizan a mayúsculas sin espacios antes de comparar; los importes se comparan en céntimos con Decimal.',
    )
    setOutcomes(invoiceOutcomes)
    setSymbols(invoiceSymbols)
  }

  const defaults = outcomes.filter((outcome) => outcome.por_defecto).length
  const defaultNeedsPerson = outcomes.some(
    (outcome) => outcome.por_defecto && outcome.requiere_persona,
  )
  const anyHuman = outcomes.some((outcome) => outcome.requiere_persona)
  const valid = name.trim().length > 0 && defaults === 1 && !defaultNeedsPerson && anyHuman

  const patch = (index: number, change: Partial<Outcome>) =>
    setOutcomes((current) =>
      current.map((outcome, i) => (i === index ? { ...outcome, ...change } : outcome)),
    )

  return (
    <form
      className="min-h-0 flex-1 overflow-y-auto px-8 pb-10 pt-4"
      onSubmit={(event) => {
        event.preventDefault()
        if (!valid) return
        create.mutate({
          nombre: name.trim(),
          descripcion: description.trim(),
          tipos_decision: outcomes,
          simbolos: symbols,
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
                    nombre: '',
                    prioridad: current.length + 1,
                    por_defecto: false,
                    requiere_persona: false,
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
                  value={outcome.nombre}
                  onChange={(event) => patch(index, { nombre: event.target.value.toUpperCase() })}
                  placeholder="ESCALAR"
                  className="w-40 shrink-0 font-mono"
                />
                <Input
                  type="number"
                  min={1}
                  value={outcome.prioridad}
                  onChange={(event) => patch(index, { prioridad: Number(event.target.value) })}
                  className="w-16 shrink-0 text-center"
                  title="Prioridad"
                />
                <label className="flex shrink-0 items-center gap-1.5 text-[12px] text-muted">
                  <input
                    type="radio"
                    name="por_defecto"
                    checked={outcome.por_defecto}
                    onChange={() =>
                      setOutcomes((current) =>
                        current.map((item, i) => ({ ...item, por_defecto: i === index })),
                      )
                    }
                  />
                  por defecto
                </label>
                <label className="flex shrink-0 items-center gap-1.5 text-[12px] text-muted">
                  <input
                    type="checkbox"
                    checked={outcome.requiere_persona}
                    onChange={(event) => patch(index, { requiere_persona: event.target.checked })}
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
                  { nombre: '', tipo: 'texto', descripcion: '' },
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
                  value={symbol.nombre}
                  onChange={(event) =>
                    setSymbols((current) =>
                      current.map((item, i) =>
                        i === index ? { ...item, nombre: event.target.value } : item,
                      ),
                    )
                  }
                  placeholder="iban"
                  className="w-40 shrink-0 font-mono"
                />
                <Select
                  value={symbol.tipo}
                  onChange={(event) =>
                    setSymbols((current) =>
                      current.map((item, i) =>
                        i === index ? { ...item, tipo: event.target.value } : item,
                      ),
                    )
                  }
                  className="w-28 shrink-0"
                >
                  <option value="texto">texto</option>
                  <option value="numero">número</option>
                  <option value="booleano">booleano</option>
                </Select>
                <Input
                  value={symbol.descripcion}
                  onChange={(event) =>
                    setSymbols((current) =>
                      current.map((item, i) =>
                        i === index ? { ...item, descripcion: event.target.value } : item,
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

const EXAMPLE = JSON.stringify(
  {
    nombre: 'Gastos de viaje',
    descripcion:
      'Aprueba o rechaza cada nota de gastos de un viaje de empresa. Convenciones de todas las reglas: importe está en euros y se compara con Decimal(str(importe)); si falta un símbolo que la regla necesita (None), la regla no salta.',
    tipos_decision: [
      { nombre: 'REVISAR', prioridad: 3, requiere_persona: true },
      { nombre: 'RECHAZAR', prioridad: 2 },
      { nombre: 'APROBAR', prioridad: 1, por_defecto: true },
    ],
    simbolos: [
      { nombre: 'empleado', tipo: 'texto', descripcion: 'Email del empleado que viaja.' },
      { nombre: 'importe', tipo: 'numero', descripcion: 'Total de la nota en euros.' },
      { nombre: 'tiene_ticket', tipo: 'booleano', descripcion: 'La nota adjunta justificante.' },
    ],
    reglas: [
      { texto: '`tiene_ticket` es verdadero.', tipo: 'requisito', decision: 'RECHAZAR' },
      { texto: '`importe` es mayor que 500.', tipo: 'prohibicion', decision: 'REVISAR' },
    ],
  },
  null,
  2,
)
