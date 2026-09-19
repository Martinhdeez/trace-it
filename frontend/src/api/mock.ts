/**
 * The offline simulator (`VITE_API_MODE=mock`). Screens moved to the English API one by
 * one, and each move replaced its method here with a 501 "Sin mock", which the
 * `ErrorNotice` shows as "Endpoint pendiente". Package 12 deletes this file.
 */
import type { ApiClient, User } from './contracts'
import { ApiError } from './http'

/** Screens that moved to the English API types have no simulator. */
function noMock(): never {
  throw new ApiError(501, 'not_implemented', 'Sin mock')
}

function wait<T>(value: T, ms = 40): Promise<T> {
  return new Promise((resolve) => {
    window.setTimeout(() => resolve(value), ms)
  })
}

const users: User[] = [
  { id: 1, name: 'Alberto Núñez', email: 'alberto@miralmar.es', role: 'manager' },
  { id: 2, name: 'Sonia Prats', email: 'sonia@miralmar.es', role: 'operator' },
]

let session = 1

function currentUser(): User {
  return users.find((item) => item.id === session) ?? users[1]
}

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

  listProcesses: noMock,
  getProcess: noMock,
  loadDefinition: noMock,

  listRules: noMock,
  listNormRules: noMock,
  normalizeNorm: noMock,
  getRule: noMock,
  createRule: noMock,
  compileRule: noMock,
  ruleImpact: noMock,
  activateRule: noMock,
  retireRule: noMock,

  listDiscoverySessions: noMock,
  startDiscoverySession: noMock,
  messageDiscoverySession: noMock,
  uploadDraftWorkbook: noMock,

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
  listRuns: noMock,
  getRun: noMock,
  listInstances: noMock,
  getInstance: noMock,
  getDocument: noMock,
  getTrace: noMock,
  fileUrl: () => '',
  queue: noMock,
  suggestion: noMock,
  resolve: noMock,

  listFindings: () => wait([]),
  listAlerts: noMock,
  ackAlert: noMock,
  exportOutcomes: noMock,

  uploadFiles: noMock,
  listSources: noMock,
  getSource: noMock,
  uploadWorkbook: noMock,
  syncSource: noMock,

  listUseCases: noMock,
  getUseCase: noMock,
  setAgentModel: noMock,
}
