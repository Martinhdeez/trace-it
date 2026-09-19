/**
 * Mirrors the backend contract, the `schemas.py` of each backend feature.
 * Payload keys stay exactly as the API sends them, which is Spanish; everything
 * else is English. Endpoints nobody has implemented yet answer 501, and routers
 * that are not mounted answer 404; the client then falls back to the mock.
 */

export type Role = 'responsable' | 'operador'

export type User = {
  id: number
  nombre: string
  email: string
  rol: Role
}

export type UserInput = {
  nombre: string
  email: string
  rol: Role
}

export type ProcessSymbol = {
  nombre: string
  tipo: string
  descripcion: string
}

export type Outcome = {
  nombre: string
  /** Highest wins when several rules fire. */
  prioridad: number
  /** Exactly one per process: what comes out when no rule fires. */
  por_defecto: boolean
  /** Its instances wait for a manager in the queue, and the assistant suggests. */
  requiere_persona: boolean
}

export type Process = {
  id: number
  nombre: string
  descripcion: string
}

export type ProcessDetail = Process & {
  tipos_decision: Outcome[]
  simbolos: ProcessSymbol[]
}

export type ProcessInput = {
  nombre: string
  descripcion: string
  tipos_decision: Outcome[]
  simbolos: ProcessSymbol[]
}

/**
 * A whole process as data: the same shape as the files under `procesos/`.
 * Loading it twice is safe. Rules whose text already exists are left alone.
 */
export type ProcessDefinition = ProcessInput & {
  reglas?: RuleInput[]
  usuarios?: UserInput[]
}

export type DefinitionLoad = {
  proceso: ProcessDetail
  reglas_nuevas: number
  usuarios_nuevos: number
}

export type RuleState = 'compilando' | 'borrador' | 'bloqueada' | 'rechazada' | 'activa' | 'retirada'
export type RuleKind = 'requisito' | 'prohibicion'

export type RuleInput = {
  texto: string
  tipo: RuleKind
  decision: string
}

export type Rule = {
  id: number
  proceso_id: number
  texto: string
  tipo: RuleKind
  decision: string
  estado: RuleState
  hash: string | null
  informe: RuleReport | null
  creada: string
  activada: string | null
}

export type RuleDetail = Rule & {
  /** Current compiler: one autonomous coder, checked by a blind tester. */
  codigo?: string | null
  tests?: RuleTest[] | null
  /** Kept for old mock fixtures created before the compiler architecture changed. */
  codigo_a: string | null
  codigo_b: string | null
  tests_a: RuleTest[] | null
  tests_b: RuleTest[] | null
}

/** A case an agent wrote from the rule text alone. */
export type RuleTest = {
  nombre: string
  instancia: Record<string, unknown>
  fuentes: Record<string, unknown[]>
  otras: Record<string, unknown>[]
  salta: boolean
}

/** One case run through both codes. `a` and `b` read like `salta (MOTIVO)` or `no salta`. */
export type CrossTest = {
  autor: string
  nombre: string
  esperado: boolean
  a: string
  b: string
  pasa: boolean
}

/**
 * Validation report of a compilation (P9). `valida` is what activation checks:
 * both codes pass every test and agree on every past instance.
 */
export type RuleReport = {
  valida?: boolean
  tests?: CrossTest[]
  historico?: { instancias: number; coinciden: number }
  discrepancias?: string[]
  intentos?: number
  revisiones?: unknown[]
  necesita_datos?: {
    by?: string
    missing?: string[]
    explanation?: string
  }
}

export type NormCheck = {
  id: number
  texto: string
  decision: string
  estado: RuleState
}

export type NormRule = {
  id: number
  numero: number
  texto: string
  politicas: string[]
  creada: string
  reglas: NormCheck[]
}

export type NormResult = {
  reglas_norma: NormRule[]
}

export type AuditChange = {
  instancia_id: number
  nombre: string
  antes: string
  despues: string
  autor_anterior: string
  motivo: string
}

/**
 * What activating or retiring a rule would do to the decisions already taken
 * (3.6, 3.7). Three groups because they need three different answers.
 */
export type Impact = {
  sin_cambio: number
  /** The engine decided it, and would now decide otherwise. */
  cambios: AuditChange[]
  /** A person decided it, and the rules would now contradict them. Blocks the change. */
  conflictos: AuditChange[]
}

export type InstanceState = 'PENDIENTE' | 'REVISION' | 'DECIDIDA'

export type Instance = {
  id: number
  /** The exact file name, which is the `file_id` of the export. */
  nombre: string
  estado: InstanceState
  /** The latest decision, if any. */
  decision: string | null
}

/** One agreed symbol: the value both extractions settled on, and where it came from. */
export type SymbolValue = {
  valor: string | number | boolean | null
  origen?: string
}

export type RuleOutcome = {
  regla_id: number
  hash: string | null
  /** `null` when the rule could not be evaluated; the engine then asks a person. */
  salta: boolean | null
  motivo: string
}

export type DecisionRecord = {
  id: number
  decision: string
  /** `motor`, or the name of the person who resolved it. */
  autor: string
  motivo: string | null
  resultados: RuleOutcome[]
  reglas_hash: string
  creada: string
}

export type TraceEvent = {
  paso: string
  datos: Record<string, unknown> | null
  latencia_ms: number | null
  creado: string
}

export type InstanceDetail = Instance & {
  fichero_hash: string
  /** `{name: {valor, origen}}`, or null while nobody has extracted them. */
  simbolos: Record<string, SymbolValue> | null
  /** Append-only history, oldest first. */
  decisiones: DecisionRecord[]
  eventos: TraceEvent[]
}

export type FindingKind = 'pagada_indebidamente' | 'no_pagada_debiendo' | (string & {})

/** A past decision a later rule says was wrong. A notice, never a correction (P14). */
export type Finding = {
  id: number
  decision_id: number
  regla_id: number | null
  tipo: FindingKind
  detalle: string | null
  creado: string
}

/** What the assistant proposes for an instance waiting on a person (3.4). */
export type Suggestion = {
  decision: string
  razonamiento: string
  regla_propuesta: string
  tipo_propuesto: RuleKind
}

export type Resolution = {
  decision: string
  motivo: string
}

export type RunSummary = {
  decididas: number
  por_decision: Record<string, number>
}

export type IngestedFile = {
  hash: string
  nombre: string
  bytes: number
  tiene_texto: boolean
  ingerido: string
}

export type ReadingLocation = {
  candidate: number
  page: number | null
  raw: string
  value: string | null
  method: string
  locator: string
  precision: 'text' | 'ocr' | 'region' | 'page' | 'unavailable'
  boxes: number[][]
}

export type DocumentLocations = {
  extraction_id: string
  sha256: string
  pages: { number: number; width: number; height: number }[]
  fields: Record<string, ReadingLocation[]>
  symbol_fields: Record<string, string>
}

export type DocumentEvidence = {
  id: string
  file_id: string
  sha256: string
  kind: 'invoice' | 'workbook'
  fields: Record<
    string,
    {
      value: string | null
      text: string | null
      selected_by: string | null
      confidence: number | null
      proposed_value?: string | null
      verification?: string
    }
  >
  text: string
  warnings: Record<string, unknown>[]
  metrics: Record<string, unknown>
  cache_hit: boolean
  pipeline_version: string
}

export type SourceLoad = {
  nombre: string
  origen: string
  filas: number
  cargada: string
}

export type LlmConfig = {
  papel: string
  modelo: string
}

export interface ApiClient {
  health(): Promise<boolean>

  login(email: string): Promise<User>
  listUsers(): Promise<User[]>

  listProcesses(): Promise<Process[]>
  getProcess(id: number): Promise<ProcessDetail>
  createProcess(body: ProcessInput): Promise<ProcessDetail>
  loadDefinition(body: ProcessDefinition): Promise<DefinitionLoad>
  replaceSymbols(id: number, symbols: ProcessSymbol[]): Promise<ProcessDetail>

  listRules(processId: number, state?: RuleState): Promise<Rule[]>
  listNormRules(processId: number): Promise<NormRule[]>
  normalizeNorm(processId: number, text: string): Promise<NormResult>
  getRule(id: number): Promise<RuleDetail>
  createRule(processId: number, body: RuleInput): Promise<RuleDetail>
  compileRule(id: number): Promise<RuleDetail>
  /** What activating, or retiring, this rule would change. Does not change anything. */
  ruleImpact(id: number): Promise<Impact>
  activateRule(id: number): Promise<RuleDetail>
  retireRule(id: number): Promise<RuleDetail>

  run(processId: number): Promise<RunSummary>
  listInstances(processId: number, state?: InstanceState): Promise<Instance[]>
  getInstance(id: number): Promise<InstanceDetail>
  getDocument(instanceId: number): Promise<DocumentEvidence | null>
  /** Everything waiting for a person. Without `outcome`, every one with `requiere_persona`. */
  queue(processId: number, outcome?: string): Promise<Instance[]>
  suggestion(instanceId: number): Promise<Suggestion>
  resolve(instanceId: number, body: Resolution): Promise<InstanceDetail>

  listFindings(processId: number): Promise<Finding[]>
  exportOutcomes(processId: number): Promise<string>

  listFiles(processId: number): Promise<IngestedFile[]>
  uploadFiles(processId: number, files: File[]): Promise<IngestedFile[]>
  listSources(processId: number): Promise<SourceLoad[]>
  /** Excel of suppliers / orders / parameters. Same call as the live demo. */
  uploadWorkbook(processId: number, file: File, cutOffDate?: string): Promise<SourceLoad[]>
  uploadSource(processId: number, name: string, file: File): Promise<SourceLoad>
  syncErp(processId: number): Promise<SourceLoad>

  listLlmConfig(): Promise<LlmConfig[]>
  setLlmConfig(role: string, model: string): Promise<LlmConfig>
}
