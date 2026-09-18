import type {
  ApiClient,
  Escalation,
  InstanceDetail,
  QueueItem,
  Run,
} from './types'
import { catalogQueue, invoiceById, toDetail, cajaFileCount } from '../data/catalog'
import { initialRuns, processes } from '../data/seed'
import { PROCESS } from '../lib/paths'
import { instanceId } from '../lib/ids'
import { defaultVersionId } from '../data/versions'
import { processCopy } from '../i18n'

const store = {
  processes: [...processes],
  runs: [...initialRuns],
}

function wait<T>(value: T, ms = 40): Promise<T> {
  return new Promise((resolve) => {
    window.setTimeout(() => resolve(value), ms)
  })
}

function stubQueue(run: Run): QueueItem[] {
  const files =
    run.processId === PROCESS.landRegistry
      ? ['finca_2218.pdf', 'nota_simple_004.pdf', 'carga_hipoteca.pdf']
      : ['tarjeta_fiscal.pdf', 'certificado_iban.pdf', 'alta_proveedor.pdf']
  return files.map((fileId, index) => ({
    id: instanceId(fileId),
    runId: run.id,
    fileId,
    result: index === 2 ? 'ESCALAR' : null,
    reason: index === 2 ? 'Dato incompleto' : 'Lectura de prueba',
    state: index === 2 ? 'PENDIENTE_HUMANO' : 'OCR',
    latencyMs: 400 + index * 80,
  }))
}

function instancesFor(runId: string): QueueItem[] {
  const run = store.runs.find((item) => item.id === runId)
  if (!run) return []
  if (run.processId === PROCESS.reconcilePayments) {
    const latest = store.runs.find((item) => item.processId === PROCESS.reconcilePayments)
    if (latest?.id !== run.id) return []
    return catalogQueue(runId)
  }
  return stubQueue(run)
}

function detailFor(id: string): InstanceDetail | undefined {
  for (const run of store.runs) {
    const items = instancesFor(run.id)
    const item = items.find((entry) => entry.id === id)
    if (!item) continue
    const invoice = invoiceById(item.fileId)
    if (invoice) return toDetail(invoice, run.id, `Norma ${run.normaVersion}`)
    return {
      id: item.id,
      fileId: item.fileId,
      runId: run.id,
      result: item.result,
      confidence: 70,
      state: item.state,
      reason: item.reason,
      document: null,
      ocrNote: 'Run de prueba. Sin facsímil de La Caja.',
      ruleHits: [],
      meta: {
        archivo: item.fileId,
        proveedor: '—',
        herramienta: 'mock',
        norma: `Norma ${run.normaVersion}`,
      },
      trace: [],
    }
  }
  return undefined
}

function escalations(): Escalation[] {
  const latest = store.runs.find((run) => run.processId === PROCESS.reconcilePayments)
  if (!latest) return []
  return instancesFor(latest.id)
    .filter((item) => item.result === 'ESCALAR' || item.state === 'PENDIENTE_HUMANO')
    .map((item) => ({
      id: `esc-${item.id}`,
      instanceId: item.id,
      fileId: item.fileId,
      processId: latest.processId,
      processName: processCopy(latest.processId).name,
      runId: latest.id,
      runLabel: latest.label,
      reason: item.reason,
      proposedDecision: item.result === 'NO_PAGAR' ? 'NO_PAGAR' : 'ESCALAR',
      proposedRule: item.reason,
      waitingSince: '11:50',
    }))
}

export const mockClient: ApiClient = {
  listProcesses: () => wait(store.processes.map((item) => ({ ...item, ...processCopy(item.id) }))),

  getProcess: async (id) => {
    const process = store.processes.find((item) => item.id === id)
    if (!process) throw new Error(`Proceso no encontrado: ${id}`)
    return wait({ ...process, ...processCopy(id) })
  },

  listRuns: (processId) =>
    wait(store.runs.filter((run) => run.processId === processId)),

  listAllRuns: () => wait([...store.runs]),

  getRun: async (id) => {
    const run = store.runs.find((item) => item.id === id)
    if (!run) throw new Error(`Run no encontrado: ${id}`)
    return wait(run)
  },

  listInstances: (runId) => wait(instancesFor(runId)),

  getInstance: async (id) => {
    const detail = detailFor(id)
    if (!detail) throw new Error(`Instancia no encontrada: ${id}`)
    return wait(detail)
  },

  listEscalations: () => wait(escalations()),

  createProcess: async (input) => {
    const process = {
      id: input.name.toLowerCase().replace(/\s+/g, '-'),
      name: input.name,
      description: input.description,
      summary: input.description,
      instanceCount: 0,
    }
    store.processes.push(process)
    return wait(process)
  },

  createRun: async ({ processId }) => {
    const existing = store.runs.filter((run) => run.processId === processId)
    const n = existing.length + 1
    const isCaja = processId === PROCESS.reconcilePayments
    const fileCount = isCaja ? cajaFileCount : 3
    const run: Run = {
      id: `run-${processId}-${Date.now()}`,
      processId,
      label: `Run ${String(n).padStart(3, '0')}`,
      status: 'en_curso',
      normaVersion: defaultVersionId(processId),
      costPerFile: 0.012,
      fileCount,
      startedAt: new Date().toISOString(),
      thumbnail: 'mix',
      counts: isCaja
        ? catalogQueue('tmp').reduce(
            (acc, item) => {
              if (item.result === 'PAGAR') acc.pagar += 1
              else if (item.result === 'NO_PAGAR') acc.noPagar += 1
              else if (item.result === 'ESCALAR') acc.escalar += 1
              else acc.pending += 1
              return acc
            },
            { pagar: 0, noPagar: 0, escalar: 0, pending: 0 },
          )
        : { pagar: 0, noPagar: 0, escalar: 1, pending: 2 },
    }
    store.runs.unshift(run)
    const process = store.processes.find((item) => item.id === processId)
    if (process) process.instanceCount = fileCount
    return wait(run, 280)
  },
}
