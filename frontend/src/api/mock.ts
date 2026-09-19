/**
 * In-memory backend with the same contract as the real one.
 * It carries the Caja lote 1 so the console, the queues and the export can be
 * operated before the endpoints exist. Every piece here has a counterpart in
 * `docs/plano-aplicacion.md`.
 */
import type {
  ApiClient,
  CrossTest,
  DecisionRecord,
  DefinitionLoad,
  Finding,
  Impact,
  Instance,
  InstanceDetail,
  InstanceState,
  LlmConfig,
  Process,
  ProcessDefinition,
  ProcessDetail,
  ProcessInput,
  ProcessSymbol,
  Resolution,
  RuleDetail,
  RuleInput,
  RuleOutcome,
  RuleState,
  Suggestion,
  SymbolValue,
  TraceEvent,
  User,
} from './contracts'
import { ApiError } from './http'
import { classifiedInvoices } from '../data/invoices.generated'
import { extractedDocuments, imageOnlyFiles } from '../data/documents.generated'
import {
  LLM_ROLES,
  invoiceOutcomes,
  invoiceSymbols,
  seedRules,
  type RuleHints,
} from '../data/seed'

/** A stored rule plus the hints the fake compiler needs to write code. */
type StoredRule = RuleDetail & Partial<RuleHints>

const imageOnly = new Set(imageOnlyFiles)
const NOW = '2026-09-18T11:39:00'

/** Screens that moved to the English API types have no simulator. */
function noMock(): never {
  throw new ApiError(501, 'not_implemented', 'Sin mock')
}

function wait<T>(value: T, ms = 40): Promise<T> {
  return new Promise((resolve) => {
    window.setTimeout(() => resolve(value), ms)
  })
}

function hash(seed: string): string {
  let value = 0
  for (const char of seed) value = (value * 31 + char.charCodeAt(0)) >>> 0
  return value.toString(16).padStart(8, '0').repeat(2).slice(0, 12)
}

const users: User[] = [
  { id: 1, name: 'Alberto Núñez', email: 'alberto@miralmar.es', role: 'manager' },
  { id: 2, name: 'Sonia Prats', email: 'sonia@miralmar.es', role: 'operator' },
]

const processes: ProcessDetail[] = [
  {
    id: 1,
    nombre: 'Pago de facturas',
    descripcion:
      '500 PDFs de La Caja, el Excel de Alberto y un ERP de 2009. La norma decide PAGAR, NO_PAGAR o ESCALAR.',
    tipos_decision: invoiceOutcomes,
    simbolos: invoiceSymbols,
  },
  {
    id: 2,
    nombre: 'Gastos de viaje',
    descripcion:
      'Aprueba o rechaza cada nota de gastos de un viaje de empresa. Otro problema, las mismas piezas.',
    tipos_decision: [
      { nombre: 'REVISAR', prioridad: 3, por_defecto: false, requiere_persona: true },
      { nombre: 'RECHAZAR', prioridad: 2, por_defecto: false, requiere_persona: false },
      { nombre: 'APROBAR', prioridad: 1, por_defecto: true, requiere_persona: false },
    ],
    simbolos: [
      { nombre: 'empleado', tipo: 'texto', descripcion: 'Email del empleado que viaja.' },
      { nombre: 'importe', tipo: 'numero', descripcion: 'Total de la nota en euros.' },
      { nombre: 'tiene_ticket', tipo: 'booleano', descripcion: 'La nota adjunta justificante.' },
    ],
  },
]

const rules: StoredRule[] = []

let nextRuleId = 1
for (const seed of seedRules) {
  const active = seed.estado === 'activa'
  const rule: StoredRule = {
    ...seed,
    id: nextRuleId,
    proceso_id: 1,
    hash: active ? hash(seed.texto) : null,
    informe: null,
    codigo_a: null,
    codigo_b: null,
    tests_a: null,
    tests_b: null,
    creada: '2026-09-18T09:12:00',
    activada: active ? '2026-09-18T09:30:00' : null,
  }
  if (active) {
    rule.codigo_a = codeFor(rule, 'a')
    rule.codigo_b = codeFor(rule, 'b')
    rule.tests_a = testsFor(rule)
    rule.tests_b = testsFor(rule)
    rule.informe = {
      valida: true,
      tests: crossTests(rule),
      historico: { instancias: 0, coinciden: 0 },
      discrepancias: [],
    }
  }
  rules.push(rule)
  nextRuleId += 1
}

// --- Instances: lote 1 de La Caja ------------------------------------------

type Row = {
  instance: Instance
  /** The reason the engine recorded. Not in the contract; drives the fake trace. */
  reason: string
  latencyMs: number
  decisions: DecisionRecord[]
}

const REASONS: Record<string, { code: string; rule: number }> = {
  'Importe no cuadra': { code: 'IMPORTE_DISTINTO', rule: 4 },
  'Pedido no encontrado': { code: 'PEDIDO_INEXISTENTE', rule: 3 },
  'IBAN distinto al maestro': { code: 'IBAN_DISTINTO', rule: 2 },
  'NIF fuera del maestro': { code: 'NIF_DESCONOCIDO', rule: 1 },
  'Pedido ya pagado en el ERP': { code: 'PEDIDO_PAGADO', rule: 7 },
}

function reasonFor(text: string): { code: string; rule: number } {
  return REASONS[text] ?? { code: 'PEDIDO_DUPLICADO', rule: 8 }
}

function ruleOutcomes(firingRule: number, code: string): RuleOutcome[] {
  return rules
    .filter((rule) => rule.estado === 'activa')
    .map((rule) => {
      const fires = rule.id === firingRule
      return {
        regla_id: rule.id,
        hash: rule.hash,
        salta: fires,
        motivo: fires ? code : 'OK',
      }
    })
}

const instances: Row[] = classifiedInvoices.map((invoice, index) => {
  const scanned = imageOnly.has(invoice.fileId)
  // A scan nobody could read agrees with neither extractor, so it waits in REVISION.
  // Anything else without a result is simply still pending, and blocks the export.
  const unreadable = scanned && invoice.result !== 'ESCALAR'
  const undecided = unreadable || invoice.result === null
  const { code, rule } = reasonFor(invoice.reason)
  const reason = unreadable ? 'LECTURA_NO_FIABLE' : invoice.result === 'PAGAR' ? '' : code
  const instance: Instance = {
    id: index + 1,
    nombre: invoice.fileId,
    estado: unreadable ? 'REVISION' : undecided ? 'PENDIENTE' : 'DECIDIDA',
    decision: undecided ? null : invoice.result,
  }
  const decisions: DecisionRecord[] = undecided
    ? []
    : [
      {
          id: index + 1,
          decision: invoice.result ?? 'ESCALAR',
          motivo: reason || null,
          autor: 'motor',
          reglas_hash: hash('norma-v3'),
          resultados: ruleOutcomes(invoice.result === 'PAGAR' ? -1 : rule, code),
          creada: NOW,
        },
      ]
  return { instance, reason, latencyMs: invoice.latencyMs, decisions }
})

function row(id: number): Row {
  const found = instances.find((item) => item.instance.id === id)
  if (!found) throw new ApiError(404, 'not_found', `No hay instancia ${id}`)
  return found
}

function ofProcess(processId: number): Row[] {
  return processId === 1 ? instances : []
}

function processById(id: number): ProcessDetail {
  const process = processes.find((item) => item.id === id)
  if (!process) throw new ApiError(404, 'not_found', `No hay proceso ${id}`)
  return process
}

function symbolsOf(name: string): Record<string, SymbolValue> {
  const doc = extractedDocuments[name]
  if (!doc) return {}
  const origin = `${name} · texto`
  return {
    nif_emisor: { valor: doc.nif, origen: origin },
    iban: { valor: doc.iban, origen: origin },
    numero_factura: { valor: doc.invoiceNumber, origen: origin },
    pedido: { valor: doc.pedido, origen: origin },
    base: { valor: doc.base, origen: origin },
    tipo_iva: { valor: Math.round(doc.ivaRate * 100), origen: origin },
    cuota_iva: { valor: doc.ivaAmount, origen: origin },
    total: { valor: doc.total, origen: origin },
    fecha: { valor: doc.date, origen: origin },
  }
}

function eventsOf(item: Row): TraceEvent[] {
  const scanned = imageOnly.has(item.instance.nombre)
  const events: TraceEvent[] = [
    {
      paso: 'ingesta',
      datos: { fichero: item.instance.nombre, hash: hash(item.instance.nombre) },
      latencia_ms: 4,
      creado: NOW,
    },
    {
      paso: 'extraccion',
      datos: {
        fuente: scanned ? 'vision · render 300 dpi' : 'pdftotext',
        simbolos: Object.keys(symbolsOf(item.instance.nombre)).length,
        ...(scanned
          ? { input_tokens: 2140, output_tokens: 96 }
          : { input_tokens: 0, output_tokens: 0 }),
      },
      latencia_ms: scanned ? 1840 : 180,
      creado: NOW,
    },
  ]
  if (item.instance.estado === 'REVISION') {
    events.push({
      paso: 'revision',
      datos: { motivo: 'LECTURA_NO_FIABLE', detalle: 'extractor_1 ≠ extractor_2' },
      latencia_ms: item.latencyMs,
      creado: NOW,
    })
    return events
  }
  events.push({
    paso: 'decision',
    datos: {
      decision: item.instance.decision,
      reglas_hash: hash('norma-v3'),
      reglas: rules.filter((rule) => rule.estado === 'activa').length,
    },
    latencia_ms: item.latencyMs,
    creado: NOW,
  })
  return events
}

const findings: Finding[] = []
const llmConfig: LlmConfig[] = LLM_ROLES.map((role, index) => ({
  papel: role,
  modelo: index % 2 === 0 ? 'anthropic/claude-opus-5' : 'openai/gpt-5',
}))

// --- Compilation and audit --------------------------------------------------

function codeFor(rule: StoredRule, variant: 'a' | 'b'): string {
  const guard =
    variant === 'a'
      ? 'if valor is None:\n        return {"salta": False, "motivo": "SIN_DATO"}'
      : 'if valor in (None, ""):\n        return {"salta": False, "motivo": "SIN_DATO"}'
  return `from decimal import Decimal

MOTIVO = ${JSON.stringify(rule.reason ?? 'ANOMALIA')}


def evaluar(instancia: dict, fuentes: dict, otras: list[dict]) -> dict:
    """${rule.texto}"""
    valor = instancia.get(${JSON.stringify(rule.symbol ?? 'total')})
    ${guard}
    ${rule.body ?? 'salta = False'}
    return {"salta": salta, "motivo": MOTIVO if salta else "OK"}
`
}

function testsFor(rule: StoredRule) {
  const symbol = rule.symbol ?? 'total'
  return [
    {
      nombre: 'cumple',
      instancia: { [symbol]: rule.passing ?? '—' },
      fuentes: {},
      otras: [],
      salta: false,
    },
    {
      nombre: 'no cumple',
      instancia: { [symbol]: rule.failing ?? '' },
      fuentes: {},
      otras: [],
      salta: true,
    },
    { nombre: 'sin dato', instancia: {}, fuentes: {}, otras: [], salta: false },
  ]
}

/** The cross-test table: every test of A and of B, run through both codes (P9). */
function crossTests(rule: StoredRule): CrossTest[] {
  return (['A', 'B'] as const).flatMap((author) =>
    testsFor(rule).map((test) => ({
      autor: author,
      nombre: test.nombre,
      esperado: test.salta,
      a: test.salta ? `salta (${rule.reason ?? 'ANOMALIA'})` : 'no salta',
      b: test.salta ? `salta (${rule.reason ?? 'ANOMALIA'})` : 'no salta',
      pasa: true,
    })),
  )
}

/** Replays the rule over the stored symbols, like `auditoria.comprobar` does. */
function impactOf(rule: StoredRule): Impact {
  const affected = instances.filter(
    (item) =>
      item.reason === rule.reason &&
      item.instance.decision !== null &&
      item.instance.decision !== rule.decision,
  )
  const byPerson = (item: Row) => item.decisions.at(-1)?.autor !== 'motor'
  const change = (item: Row, reason: string) => ({
    instancia_id: item.instance.id,
    nombre: item.instance.nombre,
    antes: item.instance.decision ?? '—',
    despues: rule.decision,
    autor_anterior: item.decisions.at(-1)?.autor ?? 'motor',
    motivo: reason,
  })
  const changes = affected.filter((item) => !byPerson(item)).map((item) => change(item, rule.reason ?? 'ANOMALIA'))
  // Contradicting a decision a person took is a conflict, not a change (P15).
  const conflicts = affected
    .filter(byPerson)
    .map((item) => change(item, 'Contradice una decisión que tomó una persona'))
  return {
    sin_cambio: instances.length - changes.length - conflicts.length,
    cambios: changes,
    conflictos: conflicts,
  }
}

function ruleById(id: number): StoredRule {
  const rule = rules.find((item) => item.id === id)
  if (!rule) throw new ApiError(404, 'not_found', `No hay regla ${id}`)
  return rule
}

function currentUser(): User {
  return users.find((item) => item.id === session) ?? users[1]
}

let session = 1

// --- Client -----------------------------------------------------------------

export const mockClient: ApiClient = {
  health: () => wait(true),

  login: async (email) => {
    const user = users.find((item) => item.email === email)
    if (!user) throw new ApiError(404, 'not_found', `No hay usuario con email ${email}`)
    session = user.id
    return wait(user)
  },
  me: async () => wait(currentUser()),
  listUsers: () => wait([...users]),

  listProcesses: () =>
    wait(processes.map(({ id, nombre, descripcion }): Process => ({ id, nombre, descripcion }))),

  getProcess: async (id) => wait(processById(id)),

  createProcess: async (body: ProcessInput) => {
    if (body.tipos_decision.filter((outcome) => outcome.por_defecto).length !== 1) {
      throw new ApiError(409, 'conflict', 'Debe haber exactamente un tipo de decisión por defecto')
    }
    const process: ProcessDetail = {
      id: Math.max(...processes.map((item) => item.id)) + 1,
      nombre: body.nombre,
      descripcion: body.descripcion,
      tipos_decision: body.tipos_decision,
      simbolos: body.simbolos,
    }
    processes.push(process)
    return wait(process, 220)
  },

  loadDefinition: async (body: ProcessDefinition) => {
    const existing = processes.find((item) => item.nombre === body.nombre)
    const process =
      existing ??
      (await mockClient.createProcess({
        nombre: body.nombre,
        descripcion: body.descripcion,
        tipos_decision: body.tipos_decision,
        simbolos: body.simbolos,
      }))
    if (existing) {
      existing.descripcion = body.descripcion
      existing.tipos_decision = body.tipos_decision
      existing.simbolos = body.simbolos
    }
    // Loading the same file twice must not duplicate rules: they are keyed by text.
    const texts = new Set(rules.filter((r) => r.proceso_id === process.id).map((r) => r.texto))
    const newRules = (body.reglas ?? []).filter((rule) => !texts.has(rule.texto))
    for (const rule of newRules) await mockClient.createRule(process.id, rule)

    const emails = new Set(users.map((item) => item.email))
    const newUsers = (body.usuarios ?? []).filter((item) => !emails.has(item.email))
    for (const item of newUsers) {
      users.push({
        id: users.length + 1,
        name: item.nombre,
        email: item.email,
        role: item.rol === 'responsable' ? 'manager' : 'operator',
      })
    }

    return wait<DefinitionLoad>(
      { proceso: process, reglas_nuevas: newRules.length, usuarios_nuevos: newUsers.length },
      600,
    )
  },

  replaceSymbols: async (id, symbols: ProcessSymbol[]) => {
    const process = processById(id)
    process.simbolos = symbols
    return wait(process)
  },

  listRules: (processId, state?: RuleState) =>
    wait(rules.filter((rule) => rule.proceso_id === processId && (!state || rule.estado === state))),

  listNormRules: (processId) =>
    wait(
      rules
        .filter((rule) => rule.proceso_id === processId)
        .map((rule, index) => ({
          id: rule.id,
          numero: index + 1,
          texto: rule.texto,
          politicas: [],
          creada: rule.creada,
          reglas: [
            {
              id: rule.id,
              texto: rule.texto,
              decision: rule.decision,
              estado: rule.estado,
            },
          ],
        })),
    ),

  normalizeNorm: async (processId, text) => {
    const lines = text
      .split(/\n+/)
      .map((line) => line.replace(/^\s*\d+[.)]\s*/, '').trim())
      .filter(Boolean)
    const created = []
    for (const [index, line] of lines.entries()) {
      const rule = await mockClient.createRule(processId, {
        texto: line,
        tipo: 'requisito',
        decision: processById(processId).tipos_decision.find((item) => !item.por_defecto)
          ?.nombre ?? 'REVISAR',
      })
      created.push({
        id: rule.id,
        numero: index + 1,
        texto: line,
        politicas: [],
        creada: rule.creada,
        reglas: [
          {
            id: rule.id,
            texto: rule.texto,
            decision: rule.decision,
            estado: rule.estado,
          },
        ],
      })
    }
    return wait({ reglas_norma: created })
  },

  getRule: async (id) => wait(ruleById(id)),

  createRule: async (processId, body: RuleInput) => {
    const process = processById(processId)
    if (!process.tipos_decision.some((outcome) => outcome.nombre === body.decision)) {
      throw new ApiError(409, 'conflict', `${body.decision} no es un tipo de decisión del proceso`)
    }
    const rule: StoredRule = {
      id: nextRuleId++,
      proceso_id: processId,
      texto: body.texto,
      tipo: body.tipo,
      decision: body.decision,
      estado: 'borrador',
      hash: null,
      informe: null,
      creada: new Date().toISOString(),
      activada: null,
      codigo_a: null,
      codigo_b: null,
      tests_a: null,
      tests_b: null,
      reason: 'ANOMALIA',
    }
    rules.push(rule)
    return wait(rule, 200)
  },

  compileRule: async (id) => {
    const rule = ruleById(id)
    if (rule.estado !== 'borrador') {
      throw new ApiError(
        409,
        'conflict',
        `Solo se compila una regla en borrador (está ${rule.estado})`,
      )
    }
    rule.codigo_a = codeFor(rule, 'a')
    rule.codigo_b = codeFor(rule, 'b')
    rule.tests_a = testsFor(rule)
    rule.tests_b = testsFor(rule)
    rule.hash = hash(rule.texto + rule.decision)
    rule.informe = {
      valida: true,
      tests: crossTests(rule),
      historico: { instancias: instances.length, coinciden: instances.length },
      discrepancias: [],
    }
    // Two agents, two LLM round trips: the real one takes 30-60 s.
    return wait(rule, 2600)
  },

  ruleImpact: async (id) => wait(impactOf(ruleById(id)), 400),

  activateRule: async (id) => {
    const rule = ruleById(id)
    if (currentUser().role !== 'manager') {
      throw new ApiError(403, 'permission_denied', 'Solo un responsable puede activar reglas')
    }
    if (!rule.informe?.valida) {
      throw new ApiError(
        409,
        'conflict',
        'La regla tiene discrepancias sin resolver o no está compilada',
      )
    }
    // Activation runs the audit and refuses to contradict a person (P15).
    const impact = impactOf(rule)
    if (impact.conflictos.length > 0) {
      throw new ApiError(
        409,
        'conflict',
        `${impact.conflictos.length} decisiones tomadas por una persona cambiarían: ${impact.conflictos
          .slice(0, 5)
          .map((change) => change.nombre)
          .join(', ')}. Resuélvelas antes de aplicar esta regla`,
      )
    }
    rule.estado = 'activa'
    rule.activada = new Date().toISOString()
    for (const change of impact.cambios) {
      findings.push({
        id: findings.length + 1,
        decision_id: change.instancia_id,
        regla_id: rule.id,
        tipo: change.despues === 'NO_PAGAR' ? 'pagada_indebidamente' : 'no_pagada_debiendo',
        detalle: `${change.nombre}: se decidió ${change.antes} y con esta regla sería ${change.despues}`,
        creado: new Date().toISOString(),
      })
    }
    return wait(rule, 500)
  },

  retireRule: async (id) => {
    const rule = ruleById(id)
    if (currentUser().role !== 'manager') {
      throw new ApiError(403, 'permission_denied', 'Solo un responsable puede retirar reglas')
    }
    rule.estado = 'retirada'
    return wait(rule, 300)
  },

  summary: noMock,
  planeMetrics: noMock,
  processMetrics: noMock,
  planesHealth: noMock,
  getDraft: noMock,
  validateDraft: noMock,
  publishDraft: noMock,
  listVersions: noMock,
  getExecution: noMock,
  saveDraft: noMock,

  run: noMock,
  listInstances: (processId, state?: InstanceState) =>
    wait(
      ofProcess(processId)
        .map((item) => item.instance)
        .filter((item) => !state || item.estado === state),
    ),

  getInstance: async (id) => {
    const item = row(id)
    const detail: InstanceDetail = {
      ...item.instance,
      fichero_hash: hash(item.instance.nombre),
      simbolos: symbolsOf(item.instance.nombre),
      decisiones: item.decisions,
      eventos: eventsOf(item),
    }
    return wait(detail)
  },

  getDocument: () => wait(null),

  queue: (processId, outcome?: string) => {
    const human = new Set(
      processById(processId)
        .tipos_decision.filter((item) => item.requiere_persona)
        .map((item) => item.nombre),
    )
    const wanted = outcome ? new Set([outcome]) : human
    return wait(
      ofProcess(processId)
        .filter((item) => item.instance.decision && wanted.has(item.instance.decision))
        .map((item) => item.instance),
    )
  },

  suggestion: async (instanceId) => {
    const item = row(instanceId)
    const proposals: Record<string, Suggestion> = {
      IMPORTE_DISTINTO: {
        decision: 'NO_PAGAR',
        razonamiento:
          'El total de la factura no coincide con el importe del pedido. El propio documento demuestra la diferencia, así que no hace falta información externa.',
        regla_propuesta:
          'Si el total de la factura difiere del importe del pedido en más de 0,01 €, no se paga.',
        tipo_propuesto: 'prohibicion',
      },
      PEDIDO_DUPLICADO: {
        decision: 'NO_PAGAR',
        razonamiento:
          'Otra instancia del proceso cita el mismo pedido. Pagar las dos duplicaría el importe, y el ERP solo tiene un asiento.',
        regla_propuesta:
          'Si otra instancia del proceso cita el mismo pedido, solo se paga la primera por fecha.',
        tipo_propuesto: 'prohibicion',
      },
      LECTURA_NO_FIABLE: {
        decision: 'ESCALAR',
        razonamiento:
          'Las dos extracciones no coinciden en un campo obligatorio. Decidir con un dato sin verificar rompe la norma 6.',
        regla_propuesta:
          'Si los dos extractores no coinciden en un campo obligatorio, la factura se escala.',
        tipo_propuesto: 'requisito',
      },
    }
    const suggestion = proposals[item.reason] ?? {
      decision: 'ESCALAR',
      razonamiento: `Anomalía ${item.reason || 'sin motivo'}. Sin regla que la cubra, la norma manda escalar antes que pagar.`,
      regla_propuesta: `Si se detecta ${item.reason || 'esta anomalía'}, la instancia se escala con ese motivo.`,
      tipo_propuesto: 'requisito' as const,
    }
    return wait(suggestion, 700)
  },

  resolve: async (instanceId, body: Resolution) => {
    const item = row(instanceId)
    const previous = item.decisions.at(-1)
    item.decisions.push({
      id: item.decisions.length + 1,
      decision: body.decision,
      motivo: body.motivo,
      autor: currentUser().name,
      reglas_hash: previous?.reglas_hash ?? '',
      resultados: [],
      creada: new Date().toISOString(),
    })
    item.instance.estado = 'DECIDIDA'
    item.instance.decision = body.decision
    item.reason = body.motivo
    return mockClient.getInstance(instanceId)
  },

  listFindings: (processId) => wait(processId === 1 ? [...findings] : []),

  exportOutcomes: async (processId) => {
    const batch = ofProcess(processId)
    const blocked = batch.filter((item) => item.decisions.length === 0)
    if (blocked.length > 0) {
      throw new ApiError(
        409,
        'conflict',
        `${blocked.length} instancias sin decidir: ${blocked
          .slice(0, 5)
          .map((item) => item.instance.nombre)
          .join(', ')}`,
      )
    }
    const lines = batch.map((item) =>
      JSON.stringify({ file_id: item.instance.nombre, result: item.instance.decision }),
    )
    return wait(lines.join('\n'), 400)
  },

  uploadFiles: noMock,
  listSources: noMock,
  getSource: noMock,
  uploadWorkbook: noMock,
  syncSource: noMock,

  listLlmConfig: () => wait([...llmConfig]),

  setLlmConfig: async (role, model) => {
    const config = llmConfig.find((item) => item.papel === role)
    if (!config) throw new ApiError(404, 'not_found', `Papel desconocido: ${role}`)
    config.modelo = model
    return wait(config, 200)
  },
}
