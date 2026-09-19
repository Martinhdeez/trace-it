/**
 * Mirrors the backend contract, the `schemas.py` of each backend feature.
 * Payload keys stay exactly as the API sends them, which is Spanish; everything
 * else is English. Endpoints nobody has implemented yet answer 501, and routers
 * that are not mounted answer 404; the client then falls back to the mock.
 */

import type { components } from './schema'

export type User = components['schemas']['UserOut']

export type Role = User['role']

type Schemas = components['schemas']
export type ProcessSummary = Schemas['ProcessSummary']
export type ExecutionMetrics = Schemas['ExecutionMetrics']
export type ProcessMetrics = Schemas['ProcessMetrics']
export type PlaneHealth = Schemas['PlaneHealth']
export type VersionDraft = Schemas['VersionDraftOut']
export type VersionOut = Schemas['VersionOut']
export type PublishIn = Schemas['PublishIn']
export type DraftIn = Schemas['DraftIn']
export type ExecutionOut = Schemas['ExecutionOut']
export type ExecutionSettings = Schemas['ExecutionSettings']
export type AgentSettings = Schemas['AgentSettings']
export type ExtractionSettings = Schemas['ExtractionSettings']
export type DecisionReview = Schemas['DecisionReviewConfig']
export type RunSummary = Schemas['RunSummary']
export type InstanceOut = Schemas['InstanceOut']
export type InstanceDetail = Schemas['InstanceDetail']
export type DecisionOut = Schemas['DecisionOut']
export type RuleResult = Schemas['RuleResultOut']
export type ReviewOut = Schemas['DecisionReviewOut']
export type InstanceEvent = Schemas['EventOut']
/** What the assistant proposes for an instance waiting on a person. */
export type Suggestion = Schemas['Suggestion']
export type ResolveIn = Schemas['ResolveIn']
export type RuleIn = Schemas['RuleIn']
export type RuleDetailOut = Schemas['RuleDetail']
export type RunOut = Schemas['RunOut']
export type AlertOut = Schemas['AlertOut']
export type UseCaseOut = Schemas['UseCaseOut']
export type UseCaseDetail = Schemas['UseCaseDetail']
export type AgentConfigOut = Schemas['AgentConfigOut']
export type AlertStatus = 'open' | 'acknowledged' | 'resolved'
export type RunDetail = Schemas['RunDetail']
export type InstanceTrace = Schemas['InstanceTrace']
export type SpanNode = Schemas['SpanNode']
export type ExtractionResult = Schemas['ExtractionResult']
export type FieldReading = Schemas['FieldReading']

/** One agreed symbol inside `InstanceDetail.symbols`: the value and where it came from. */
export type SymbolReading = { value: string | number | boolean | null; origin?: string }

/** Server-side filters of the instance list. */
export type InstanceFilters = { status?: string; decision?: string; q?: string }
export type DocumentUpload = Schemas['DocumentUpload']
export type WorkbookUpload = Schemas['WorkbookUpload']
export type SourceOut = Schemas['SourceOut']
export type SourceDetail = Schemas['SourceDetail']
export type SyncResult = Schemas['SyncResult']

/** Reported after each file of a batch has been uploaded (and re-extracted when it was stale). */
export type UploadProgress = { done: number; total: number; name: string; status: string }

export type Preset = Exclude<ExecutionSettings['preset'], 'custom'>

/** The backend leaves `validation` as free JSON; these are the fields the console reads. */
export type HistoricalCoverage = {
  evaluated: number
  not_evaluable: number
  partial: number
  none: number
  total?: number
}
export type HistoricalCaseWithoutCoverage = {
  instance_id: number
  name: string
  missing_symbols: string[]
  evaluated_rules: number[]
  unavailable_rules: { rule_id: number; symbol: string }[]
}
export type ValidationReport = {
  valid: boolean
  hash: string
  coverage?: HistoricalCoverage
  not_evaluable?: HistoricalCaseWithoutCoverage[]
  conflicts?: { instance_id: number; reason?: string }[]
  errors?: { instance_id: number; reason?: string }[]
  error?: string
  [key: string]: unknown
}

export type UserInput = {
  nombre: string
  email: string
  rol: 'responsable' | 'operador'
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
  /** The use case whose agents (and models) this process shares with others. */
  use_case_id?: number
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

export interface ApiClient {
  health(): Promise<boolean>

  login(email: string): Promise<User>
  me(): Promise<User>
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
  createRule(processId: number, body: RuleIn): Promise<RuleDetailOut>
  compileRule(id: number): Promise<RuleDetail>
  /** What activating, or retiring, this rule would change. Does not change anything. */
  ruleImpact(id: number): Promise<Impact>
  activateRule(id: number): Promise<RuleDetail>
  retireRule(id: number): Promise<RuleDetail>

  summary(processId: number): Promise<ProcessSummary>
  planeMetrics(processId: number, plane: 'execution'): Promise<ExecutionMetrics>
  processMetrics(processId: number): Promise<ProcessMetrics>
  planesHealth(): Promise<PlaneHealth[]>
  /** 404 when the process has no draft. */
  getDraft(processId: number): Promise<VersionDraft>
  validateDraft(processId: number): Promise<VersionDraft>
  publishDraft(processId: number, body: PublishIn): Promise<VersionOut>
  listVersions(processId: number): Promise<VersionOut[]>
  getExecution(processId: number): Promise<ExecutionOut>
  saveDraft(processId: number, body: DraftIn): Promise<VersionDraft>

  run(processId: number): Promise<RunSummary>
  /** Every run of the process, newest first. */
  listRuns(processId: number): Promise<RunOut[]>
  /** One run and the decisions it appended. */
  getRun(id: number): Promise<RunDetail>
  listInstances(processId: number, filters?: InstanceFilters): Promise<InstanceOut[]>
  getInstance(id: number): Promise<InstanceDetail>
  getDocument(instanceId: number): Promise<ExtractionResult>
  /** The decision, its rule results with their text, the file and the span tree. */
  getTrace(instanceId: number): Promise<InstanceTrace>
  /** Where the stored PDF is served, for an iframe or a download link. */
  fileUrl(instanceId: number): string
  /** Everything waiting for a person, including cases the reviewer disagreed with. */
  queue(processId: number): Promise<InstanceOut[]>
  suggestion(instanceId: number): Promise<Suggestion>
  resolve(instanceId: number, body: ResolveIn): Promise<InstanceDetail>

  listFindings(processId: number): Promise<Finding[]>
  /** Past decisions that newer data or rules would decide differently. */
  listAlerts(processId: number, status?: AlertStatus): Promise<AlertOut[]>
  ackAlert(id: number, note?: string): Promise<AlertOut>
  exportOutcomes(processId: number): Promise<string>

  uploadFiles(
    processId: number,
    files: File[],
    onProgress?: (progress: UploadProgress) => void,
  ): Promise<DocumentUpload[]>
  listSources(processId: number): Promise<SourceOut[]>
  /** One source with its rows. `parameters` holds the cut-off date. 404 until loaded. */
  getSource(processId: number, name: string): Promise<SourceDetail>
  /** Excel of suppliers / orders / parameters. The cut-off date is required, there is no default. */
  uploadWorkbook(processId: number, file: File, cutOffDate: string): Promise<WorkbookUpload>
  syncSource(processId: number, name: string): Promise<SyncResult>

  listUseCases(): Promise<UseCaseOut[]>
  /** One use case with its agents and the model each one runs. */
  getUseCase(id: number): Promise<UseCaseDetail>
  /** A new version of that agent's config: the same settings with another model. */
  setAgentModel(useCaseId: number, agent: AgentConfigOut, model: string): Promise<AgentConfigOut>
}
