export type Decision = 'PAGAR' | 'NO_PAGAR' | 'ESCALAR'

export type InstanceState =
  | 'RECIBIDA'
  | 'EXTRAIDA'
  | 'VALIDADA'
  | 'CRUZADA'
  | 'DECIDIDA'
  | 'EXPORTADA'
  | 'PENDIENTE_HUMANO'
  | 'REINTENTO'
  | 'OCR'

export type RunStatus = 'en_curso' | 'completado' | 'pausado'

export type Process = {
  id: string
  name: string
  description: string
  summary: string
  instanceCount: number
}

export type Run = {
  id: string
  processId: string
  label: string
  status: RunStatus
  normaVersion: string
  costPerFile: number
  fileCount: number
  startedAt: string
  thumbnail: 'mix' | 'pagar' | 'escalar' | 'ocr'
  counts: {
    pagar: number
    noPagar: number
    escalar: number
    pending: number
  }
}

export type QueueItem = {
  id: string
  runId: string
  fileId: string
  result: Decision | null
  reason: string
  state: InstanceState
  latencyMs: number
  decidedAt?: string
}

export type LineItem = {
  description: string
  qty: number
  unitPrice: number
  base: number
}

export type InvoiceDocument = {
  supplierName: string
  supplierActivity?: string
  address: string
  phone?: string
  email?: string
  nif: string
  iban: string
  invoiceNumber: string
  date: string
  clientName: string
  clientNif: string
  pedido: string
  albaran?: string
  paymentMethod?: string
  lines: LineItem[]
  base: number
  ivaRate: number
  ivaAmount: number
  total: number
  conditions?: string
  signature?: string
  page: string
  inputKind: string
  sizeKb: number
}

export type RuleHit = {
  id: string
  ok: boolean
  title: string
  detail: string
  latencyMs: number
}

export type TraceStep = {
  step: string
  input: string
  output: string
  latencyMs: number
  retries: number
}

export type InstanceDetail = {
  id: string
  fileId: string
  runId: string
  result: Decision | null
  confidence: number | null
  state: InstanceState
  reason: string
  document: InvoiceDocument | null
  ocrNote?: string
  ruleHits: RuleHit[]
  meta: {
    archivo: string
    proveedor: string
    herramienta: string
    norma: string
  }
  trace: TraceStep[]
}

export type Escalation = {
  id: string
  instanceId: string
  fileId: string
  processId: string
  processName: string
  runId: string
  runLabel: string
  reason: string
  proposedDecision: Decision
  proposedRule: string
  waitingSince: string
}

export type CreateProcessInput = {
  name: string
  description: string
}

export type CreateRunInput = {
  processId: string
}

export interface ApiClient {
  listProcesses(): Promise<Process[]>
  getProcess(id: string): Promise<Process>
  listRuns(processId: string): Promise<Run[]>
  listAllRuns(): Promise<Run[]>
  getRun(id: string): Promise<Run>
  listInstances(runId: string): Promise<QueueItem[]>
  getInstance(id: string): Promise<InstanceDetail>
  listEscalations(): Promise<Escalation[]>
  createProcess(input: CreateProcessInput): Promise<Process>
  createRun(input: CreateRunInput): Promise<Run>
}
