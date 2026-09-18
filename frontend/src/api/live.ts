import type {
  ApiClient,
  DefinitionLoad,
  Finding,
  Impact,
  IngestedFile,
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
  Rule,
  RuleDetail,
  RuleInput,
  RuleState,
  RunSummary,
  SourceLoad,
  Suggestion,
  User,
} from './contracts'
import { get, getText, post, put, query, upload } from './http'

/** The FastAPI backend. Endpoints nobody has written yet answer 501 or 404. */
export const liveClient: ApiClient = {
  health: async () => {
    const body = await get<{ estado: string }>('/salud')
    return body.estado === 'ok'
  },

  login: (email) => post<User>('/login', { email }),
  listUsers: () => get<User[]>('/usuarios'),

  listProcesses: () => get<Process[]>('/procesos'),
  getProcess: (id) => get<ProcessDetail>(`/procesos/${id}`),
  createProcess: (body: ProcessInput) => post<ProcessDetail>('/procesos', body),
  loadDefinition: (body: ProcessDefinition) => post<DefinitionLoad>('/procesos/definicion', body),
  replaceSymbols: (id, symbols: ProcessSymbol[]) =>
    put<ProcessDetail>(`/procesos/${id}/simbolos`, symbols),

  listRules: (processId, state?: RuleState) =>
    get<Rule[]>(`/procesos/${processId}/reglas${query({ estado: state })}`),
  getRule: (id) => get<RuleDetail>(`/reglas/${id}`),
  createRule: (processId, body: RuleInput) =>
    post<RuleDetail>(`/procesos/${processId}/reglas`, body),
  compileRule: (id) => post<RuleDetail>(`/reglas/${id}/compilar`),
  ruleImpact: (id) => get<Impact>(`/reglas/${id}/impacto`),
  activateRule: (id) => post<RuleDetail>(`/reglas/${id}/activar`),
  retireRule: (id) => post<RuleDetail>(`/reglas/${id}/retirar`),

  run: (processId) => post<RunSummary>(`/procesos/${processId}/ejecutar`),
  listInstances: (processId, state?: InstanceState) =>
    get<Instance[]>(`/procesos/${processId}/instancias${query({ estado: state })}`),
  getInstance: (id) => get<InstanceDetail>(`/instancias/${id}`),
  queue: (processId, outcome?: string) =>
    get<Instance[]>(`/procesos/${processId}/cola${query({ tipo: outcome })}`),
  suggestion: (instanceId) => get<Suggestion>(`/instancias/${instanceId}/sugerencia`),
  resolve: (instanceId, body: Resolution) =>
    post<InstanceDetail>(`/instancias/${instanceId}/resolver`, body),

  listFindings: (processId) => get<Finding[]>(`/procesos/${processId}/hallazgos`),
  exportOutcomes: (processId) => getText(`/procesos/${processId}/exportar`),

  listFiles: (processId) => get<IngestedFile[]>(`/procesos/${processId}/ficheros`),
  uploadFiles: (processId, files) => {
    const form = new FormData()
    for (const file of files) form.append('ficheros', file)
    return upload<IngestedFile[]>(`/procesos/${processId}/ficheros`, form)
  },
  listSources: (processId) => get<SourceLoad[]>(`/procesos/${processId}/fuentes`),
  uploadSource: (processId, name, file) => {
    const form = new FormData()
    form.append('nombre', name)
    form.append('fichero', file)
    return upload<SourceLoad>(`/procesos/${processId}/fuentes`, form)
  },
  syncErp: (processId) => post<SourceLoad>(`/procesos/${processId}/fuentes/erp`),

  listLlmConfig: () => get<LlmConfig[]>('/llm/config'),
  setLlmConfig: (role, model) => put<LlmConfig>(`/llm/config/${role}`, { modelo: model }),
}
