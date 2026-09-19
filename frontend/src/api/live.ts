import type {
  AgentConfigOut,
  AlertOut,
  ApiClient,
  Definition,
  DiscoverySession,
  DiscoverySessionSummary,
  DocumentUpload,
  DraftIn,
  ExecutionMetrics,
  ExecutionOut,
  ExtractionResult,
  Impact,
  InstanceDetail,
  InstanceOut,
  InstanceTrace,
  LoadResult,
  NormOut,
  NormRule,
  PlaneHealth,
  ProcessDetail,
  Proposal,
  ProcessMetrics,
  ProcessOut,
  ProcessSummary,
  PublishIn,
  Rule,
  RuleDetail,
  RunDetail,
  RunOut,
  RunSummary,
  SourceDetail,
  SourceOut,
  Suggestion,
  SyncResult,
  UseCaseDetail,
  UseCaseOut,
  User,
  VersionDraft,
  VersionOut,
  WorkbookUpload,
} from './contracts'
import { BASE, get, getText, post, put, query, upload } from './http'

/** The FastAPI API, as it is. Only findings still get Spanish keys at the edge. */
export const liveClient: ApiClient = {
  health: async () => {
    const body = await get<{ status: string }>('/health')
    return body.status === 'ok'
  },

  login: (email) => post<User>('/login', { email }),
  me: () => get<User>('/me'),
  listUsers: () => get<User[]>('/users'),

  listProcesses: () => get<ProcessOut[]>('/processes'),
  getProcess: (id) => get<ProcessDetail>(`/processes/${id}`),
  loadDefinition: (body: Definition) => post<LoadResult>('/processes/definition', body),

  listRules: (processId, status) =>
    get<Rule[]>(`/processes/${processId}/rules${query({ status })}`),
  listNormRules: (processId) => get<NormRule[]>(`/processes/${processId}/norm-rules`),
  normalizeNorm: (processId, text) => post<NormOut>(`/processes/${processId}/norm`, { text }),
  getRule: (id) => get<RuleDetail>(`/rules/${id}`),
  createRule: (processId, body) => post<RuleDetail>(`/processes/${processId}/rules`, body),
  compileRule: (id) => post<RuleDetail>(`/rules/${id}/compile`),
  ruleImpact: (id) => get<Impact>(`/rules/${id}/impact`),
  activateRule: (id) => post<RuleDetail>(`/rules/${id}/activate`),
  retireRule: (id) => post<RuleDetail>(`/rules/${id}/retire`),

  listDiscoverySessions: () => get<DiscoverySessionSummary[]>('/process-drafts'),
  startDiscoverySession: (processId, name) =>
    post<DiscoverySession>('/process-drafts', { process_id: processId, name }),
  messageDiscoverySession: (id, revision, message) =>
    post<DiscoverySession>(`/process-drafts/${id}/messages`, { revision, message, mode: 'discuss' }),
  uploadDraftWorkbook: (id, revision, file) => {
    const form = new FormData()
    form.append('file', file)
    form.append('revision', String(revision))
    return upload<DiscoverySession>(`/process-drafts/${id}/workbooks`, form)
  },

  summary: (processId) => get<ProcessSummary>(`/processes/${processId}/summary`),
  planeMetrics: (processId, plane) =>
    get<ExecutionMetrics>(`/processes/${processId}/metrics/${plane}`),
  processMetrics: (processId) => get<ProcessMetrics>(`/processes/${processId}/metrics`),
  planesHealth: () => get<PlaneHealth[]>('/health/planes'),
  getDraft: (processId) => get<VersionDraft>(`/processes/${processId}/draft`),
  validateDraft: (processId) => post<VersionDraft>(`/processes/${processId}/draft/validate`),
  publishDraft: (processId, body: PublishIn) =>
    post<VersionOut>(`/processes/${processId}/draft/publish`, body),
  listVersions: (processId) => get<VersionOut[]>(`/processes/${processId}/versions`),
  getExecution: (processId) => get<ExecutionOut>(`/processes/${processId}/execution`),
  saveDraft: (processId, body: DraftIn) => put<VersionDraft>(`/processes/${processId}/draft`, body),

  run: (processId) => post<RunSummary>(`/processes/${processId}/run`),
  listRuns: (processId) => get<RunOut[]>(`/processes/${processId}/runs`),
  getRun: (id) => get<RunDetail>(`/runs/${id}`),
  listInstances: (processId, filters) =>
    get<InstanceOut[]>(`/processes/${processId}/instances${query({ ...filters })}`),
  getInstance: (id) => get<InstanceDetail>(`/instances/${id}`),
  getDocument: (instanceId) => get<ExtractionResult>(`/instances/${instanceId}/document`),
  getTrace: (instanceId) => get<InstanceTrace>(`/instances/${instanceId}/trace`),
  fileUrl: (instanceId) => `${BASE}/instances/${instanceId}/file`,
  queue: (processId) => get<InstanceOut[]>(`/processes/${processId}/queue`),
  suggestion: (instanceId) => get<Suggestion>(`/instances/${instanceId}/suggestion`),
  resolve: (instanceId, body) => post<InstanceDetail>(`/instances/${instanceId}/resolve`, body),
  proposeDecision: (instanceId) => post<Proposal>(`/instances/${instanceId}/proposal`),
  listProposals: (processId, status) =>
    get<Proposal[]>(`/processes/${processId}/proposals${query({ status })}`),
  acceptProposal: (id, reason) => post<Proposal>(`/proposals/${id}/accept`, { reason: reason ?? '' }),
  rejectProposal: (id, reason) => post<Proposal>(`/proposals/${id}/reject`, { reason }),

  listFindings: async (processId) => {
    const raw = await get<
      { id: number; decision_id: number; rule_id: number | null; type: string; detail: string | null; created_at: string }[]
    >(`/processes/${processId}/findings`)
    return raw.map((item) => ({
      id: item.id,
      decision_id: item.decision_id,
      regla_id: item.rule_id,
      tipo: item.type,
      detalle: item.detail,
      creado: item.created_at,
    }))
  },
  listAlerts: (processId, status) =>
    get<AlertOut[]>(`/processes/${processId}/alerts${query({ status })}`),
  ackAlert: (id, note) => post<AlertOut>(`/alerts/${id}/ack`, { note: note || null }),
  exportOutcomes: (processId) => getText(`/processes/${processId}/export`),

  uploadFiles: async (processId, files, onProgress) => {
    const results: DocumentUpload[] = []
    for (const file of files) {
      const form = new FormData()
      form.append('file', file)
      let result = await upload<DocumentUpload>(`/processes/${processId}/files`, form)
      // The same file again: a PENDING instance keeps the symbols it had, so read it again.
      if (!result.created && result.status === 'PENDING') {
        result = await post<DocumentUpload>(`/instances/${result.instance_id}/extract`, {})
      }
      results.push(result)
      onProgress?.({
        done: results.length,
        total: files.length,
        name: result.name,
        status: result.status,
      })
    }
    return results
  },
  listSources: (processId) => get<SourceOut[]>(`/processes/${processId}/sources`),
  getSource: (processId, name) =>
    get<SourceDetail>(`/processes/${processId}/sources/${encodeURIComponent(name)}`),
  uploadWorkbook: (processId, file, cutOffDate) => {
    const form = new FormData()
    form.append('file', file)
    form.append('cut_off_date', cutOffDate)
    return upload<WorkbookUpload>(`/processes/${processId}/sources/workbook`, form)
  },
  syncSource: (processId, name) =>
    post<SyncResult>(`/processes/${processId}/sources/${encodeURIComponent(name)}/sync`),

  listUseCases: () => get<UseCaseOut[]>('/use-cases'),
  getUseCase: (id) => get<UseCaseDetail>(`/use-cases/${id}`),
  setAgentModel: (useCaseId, agent, model) =>
    put<AgentConfigOut>(`/use-cases/${useCaseId}/agents/${agent.role}`, {
      config: { ...agent.config, model },
      note: 'Cambiado desde la consola',
    }),
}
