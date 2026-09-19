import type {
  ApiClient,
  DocumentEvidence,
  IngestedFile,
  Instance,
  InstanceState,
  NormResult,
  NormRule,
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
  User,
} from './contracts'
import { get, getText, post, put, query, upload } from './http'

type RawUser = { id: number; name: string; email: string; role: 'manager' | 'operator' }
type RawProcess = { id: number; name: string; use_case_id: number; description: string }
type RawProcessDetail = RawProcess & {
  decision_types: { name: string; priority: number; is_default: boolean; requires_human: boolean }[]
  symbols: { name: string; type: string; description: string }[]
}
type RawRule = {
  id: number
  process_id: number
  norm_rule_id: number | null
  text: string
  type: 'requirement' | 'prohibition'
  decision: string
  status: 'compiling' | 'draft' | 'active' | 'blocked' | 'retired'
  hash: string | null
  report: Record<string, unknown> | null
  created_at: string
  activated_at: string | null
}
type RawRuleDetail = RawRule & { code: string | null; tests: Record<string, unknown>[] | null }
type RawInstance = { id: number; name: string; status: string; decision: string | null }
type RawUseCase = { id: number; name: string; description: string }
type RawAgentConfig = {
  id: number
  role: string
  version: number
  config: { model: string | null; instructions: string; model_settings: object; limits: object; examples: unknown[] }
  active: boolean
  author: string
  note: string | null
  created_at: string
}
type RawUseCaseDetail = RawUseCase & { agents: RawAgentConfig[] }

const user = (raw: RawUser): User => ({
  id: raw.id,
  nombre: raw.name,
  email: raw.email,
  rol: raw.role === 'manager' ? 'responsable' : 'operador',
})

const process = (raw: RawProcess): Process => ({
  id: raw.id,
  nombre: raw.name,
  descripcion: raw.description,
})

const processDetail = (raw: RawProcessDetail): ProcessDetail => ({
  ...process(raw),
  tipos_decision: raw.decision_types.map((item) => ({
    nombre: item.name,
    prioridad: item.priority,
    por_defecto: item.is_default,
    requiere_persona: item.requires_human,
  })),
  simbolos: raw.symbols.map((item) => ({
    nombre: item.name,
    tipo: item.type,
    descripcion: item.description,
  })),
})

const rawStatus: Record<RawRule['status'], RuleState> = {
  compiling: 'compilando',
  draft: 'borrador',
  active: 'activa',
  blocked: 'bloqueada',
  retired: 'retirada',
}

const report = (value: Record<string, unknown> | null): Rule['informe'] => {
  if (!value) return null
  const rawTests = Array.isArray(value.tests) ? value.tests : []
  return {
    valida: Boolean(value.valid),
    tests: rawTests.map((item, index) => {
      const test = item as Record<string, unknown>
      return {
        autor: 'tester',
        nombre: String(test.name ?? `test ${index + 1}`),
        esperado: Boolean(test.expected),
        a: String(test.got ?? '—'),
        b: String(test.got ?? '—'),
        pasa: Boolean(test.passed),
      }
    }),
    discrepancias: Array.isArray(value.discrepancies)
      ? value.discrepancies.map(String)
      : [],
    intentos: typeof value.attempts === 'number' ? value.attempts : undefined,
    revisiones: Array.isArray(value.reviews) ? value.reviews : [],
    necesita_datos:
      value.needs_data && typeof value.needs_data === 'object'
        ? (value.needs_data as NonNullable<Rule['informe']>['necesita_datos'])
        : undefined,
  }
}

const rule = (raw: RawRule): Rule => ({
  id: raw.id,
  proceso_id: raw.process_id,
  texto: raw.text,
  tipo: raw.type === 'requirement' ? 'requisito' : 'prohibicion',
  decision: raw.decision,
  estado: rawStatus[raw.status],
  hash: raw.hash,
  informe: report(raw.report),
  creada: raw.created_at,
  activada: raw.activated_at,
})

const ruleDetail = (raw: RawRuleDetail): RuleDetail => ({
  ...rule(raw),
  codigo: raw.code,
  tests: (raw.tests ?? []) as RuleDetail['tests'],
  // Compatibility with old UI paths while the mock still models two compilers.
  codigo_a: raw.code,
  codigo_b: null,
  tests_a: (raw.tests ?? []) as RuleDetail['tests_a'],
  tests_b: null,
})

const instance = (raw: RawInstance): Instance => ({
  id: raw.id,
  nombre: raw.name,
  estado:
    raw.status === 'DECIDED'
      ? 'DECIDIDA'
      : raw.status === 'REVIEW'
        ? 'REVISION'
        : 'PENDIENTE',
  decision: raw.decision,
})

const normRule = (raw: {
  id: number
  number: number
  text: string
  policies?: string[]
  created_at?: string
  rules?: { id: number; text: string; decision: string; status: RawRule['status'] }[]
}): NormRule => ({
  id: raw.id,
  numero: raw.number,
  texto: raw.text,
  politicas: raw.policies ?? [],
  creada: raw.created_at ?? new Date().toISOString(),
  reglas: (raw.rules ?? []).map((item) => ({
    id: item.id,
    texto: item.text,
    decision: item.decision,
    estado: rawStatus[item.status],
  })),
})

const definitionBody = (body: ProcessDefinition | ProcessInput) => ({
  name: body.nombre,
  description: body.descripcion,
  decision_types: body.tipos_decision.map((item) => ({
    name: item.nombre,
    priority: item.prioridad,
    is_default: item.por_defecto,
    requires_human: item.requiere_persona,
  })),
  symbols: body.simbolos.map((item) => ({
    name: item.nombre,
    type: item.tipo,
    description: item.descripcion,
  })),
  ...('reglas' in body
    ? {
        rules: (body.reglas ?? []).map((item) => ({
          text: item.texto,
          type: item.tipo === 'requisito' ? 'requirement' : 'prohibition',
          decision: item.decision,
        })),
        users: (body.usuarios ?? []).map((item) => ({
          name: item.nombre,
          email: item.email,
          role: item.rol === 'responsable' ? 'manager' : 'operator',
        })),
      }
    : {}),
})

/** The current English FastAPI API, adapted to the Spanish UI vocabulary at the edge. */
export const liveClient: ApiClient = {
  health: async () => {
    const body = await get<{ status: string }>('/health')
    return body.status === 'ok'
  },

  login: async (email) => user(await post<RawUser>('/login', { email })),
  listUsers: async () => (await get<RawUser[]>('/users')).map(user),

  listProcesses: async () => (await get<RawProcess[]>('/processes')).map(process),
  getProcess: async (id) => processDetail(await get<RawProcessDetail>(`/processes/${id}`)),
  createProcess: async (body: ProcessInput) => {
    const loaded = await post<{ process: RawProcessDetail }>('/processes/definition', definitionBody(body))
    return processDetail(loaded.process)
  },
  loadDefinition: async (body: ProcessDefinition) => {
    const loaded = await post<{
      process: RawProcessDetail
      new_rules: number
      new_users: number
    }>('/processes/definition', definitionBody(body))
    return {
      proceso: processDetail(loaded.process),
      reglas_nuevas: loaded.new_rules,
      usuarios_nuevos: loaded.new_users,
    }
  },
  replaceSymbols: async (id, symbols: ProcessSymbol[]) => {
    const current = await liveClient.getProcess(id)
    return liveClient.createProcess({ ...current, simbolos: symbols })
  },

  listRules: (processId, state?: RuleState) =>
    get<RawRule[]>(
      `/processes/${processId}/rules${query({
        status: state
          ? ({
              compilando: 'compiling',
              borrador: 'draft',
              bloqueada: 'blocked',
              rechazada: 'blocked',
              activa: 'active',
              retirada: 'retired',
            } as const)[state]
          : undefined,
      })}`,
    ).then((items) => items.map(rule)),
  listNormRules: async (processId) =>
    (await get<Parameters<typeof normRule>[0][]>(`/processes/${processId}/norm-rules`)).map(
      normRule,
    ),
  normalizeNorm: async (processId, text) => {
    const raw = await post<{
      norm_rules: {
        id: number
        number: number
        text: string
        policies: string[]
        checks: {
          rule_id: number
          text: string
          decision: string
        }[]
      }[]
    }>(`/processes/${processId}/norm`, { text })
    const result: NormResult = {
      reglas_norma: raw.norm_rules.map((item) => ({
        id: item.id,
        numero: item.number,
        texto: item.text,
        politicas: item.policies,
        creada: new Date().toISOString(),
        reglas: item.checks.map((check) => ({
          id: check.rule_id,
          texto: check.text,
          decision: check.decision,
          estado: 'compilando',
        })),
      })),
    }
    return result
  },
  getRule: async (id) => ruleDetail(await get<RawRuleDetail>(`/rules/${id}`)),
  createRule: async (processId, body: RuleInput) =>
    ruleDetail(
      await post<RawRuleDetail>(`/processes/${processId}/rules`, {
        text: body.texto,
        type: body.tipo === 'requisito' ? 'requirement' : 'prohibition',
        decision: body.decision,
      }),
    ),
  compileRule: async (id) => ruleDetail(await post<RawRuleDetail>(`/rules/${id}/compile`)),
  ruleImpact: async (id) => {
    const raw = await get<{
      unchanged: number
      changes: { instance_id: number; name: string; before: string; after: string; previous_author: string; reason: string }[]
      conflicts: { instance_id: number; name: string; before: string; after: string; previous_author: string; reason: string }[]
    }>(`/rules/${id}/impact`)
    const change = (item: (typeof raw.changes)[number]) => ({
      instancia_id: item.instance_id,
      nombre: item.name,
      antes: item.before,
      despues: item.after,
      autor_anterior: item.previous_author,
      motivo: item.reason,
    })
    return { sin_cambio: raw.unchanged, cambios: raw.changes.map(change), conflictos: raw.conflicts.map(change) }
  },
  activateRule: async (id) => ruleDetail(await post<RawRuleDetail>(`/rules/${id}/activate`)),
  retireRule: async (id) => ruleDetail(await post<RawRuleDetail>(`/rules/${id}/retire`)),

  run: async (processId) => {
    const raw = await post<{ decided: number; by_decision: Record<string, number> }>(
      `/processes/${processId}/run`,
    )
    return { decididas: raw.decided, por_decision: raw.by_decision }
  },
  listInstances: async (processId, state?: InstanceState) => {
    // Current backend has no REVIEW state: unread documents remain PENDING.
    if (state === 'REVISION') return []
    const items = await get<RawInstance[]>(
      `/processes/${processId}/instances${query({
        status: state === 'DECIDIDA' ? 'DECIDED' : state === 'PENDIENTE' ? 'PENDING' : undefined,
      })}`,
    )
    return items.map(instance)
  },
  getInstance: async (id) => {
    const raw = await get<{
      id: number
      name: string
      status: string
      decision: string | null
      file_hash: string
      symbols: Record<string, unknown> | null
      decisions: {
        id: number
        decision: string
        author: string
        reason: string | null
        results: { rule_id: number; hash: string | null; fires: boolean | null; reason: string }[]
        rules_hash: string
        created_at: string
      }[]
      events: { step: string; data: Record<string, unknown> | null; latency_ms: number | null; created_at: string }[]
    }>(`/instances/${id}`)
    const symbols =
      raw.symbols == null
        ? null
        : Object.fromEntries(
            Object.entries(raw.symbols).map(([name, value]) => {
              if (value && typeof value === 'object' && !Array.isArray(value)) {
                const item = value as Record<string, unknown>
                return [
                  name,
                  {
                    valor: item.value ?? item.valor ?? null,
                    origen:
                      typeof (item.origin ?? item.origen) === 'string'
                        ? String(item.origin ?? item.origen)
                        : undefined,
                  },
                ]
              }
              return [name, { valor: value as string | number | boolean | null }]
            }),
          )
    return {
      ...instance(raw),
      fichero_hash: raw.file_hash,
      simbolos: symbols,
      decisiones: raw.decisions.map((item) => ({
        id: item.id,
        decision: item.decision,
        autor: item.author === 'engine' ? 'motor' : item.author,
        motivo: item.reason,
        resultados: item.results.map((result) => ({
          regla_id: result.rule_id,
          hash: result.hash,
          salta: result.fires,
          motivo: result.reason,
        })),
        reglas_hash: item.rules_hash,
        creada: item.created_at,
      })),
      eventos: raw.events.map((item) => ({
        paso: item.step,
        datos: item.data,
        latencia_ms: item.latency_ms,
        creado: item.created_at,
      })),
    }
  },
  getDocument: (instanceId) =>
    get<DocumentEvidence>(`/instances/${instanceId}/document`),
  queue: (processId, outcome?: string) =>
    get<RawInstance[]>(`/processes/${processId}/queue${query({ type: outcome })}`).then((items) =>
      items.map(instance),
    ),
  suggestion: async (instanceId) => {
    const raw = await get<{
      decision: string
      reasoning: string
      proposed_rule: string
      proposed_type: 'requirement' | 'prohibition'
    }>(`/instances/${instanceId}/suggestion`)
    return {
      decision: raw.decision,
      razonamiento: raw.reasoning,
      regla_propuesta: raw.proposed_rule,
      tipo_propuesto: raw.proposed_type === 'requirement' ? 'requisito' : 'prohibicion',
    }
  },
  resolve: async (instanceId, body: Resolution) => {
    await post(`/instances/${instanceId}/resolve`, {
      decision: body.decision,
      reason: body.motivo,
    })
    return liveClient.getInstance(instanceId)
  },

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
  exportOutcomes: (processId) => getText(`/processes/${processId}/export`),

  listFiles: async (processId) => {
    const items = await liveClient.listInstances(processId)
    return items.map((item) => ({
      hash: '',
      nombre: item.nombre,
      bytes: 0,
      tiene_texto: true,
      ingerido: '',
    }))
  },
  uploadFiles: async (processId, files) => {
    const results: IngestedFile[] = []
    for (const file of files) {
      const form = new FormData()
      form.append('file', file)
      const raw = await upload<{
        name: string
        file_hash: string
        extraction?: { text?: string }
        symbols?: Record<string, { value?: unknown } | null>
      }>(`/processes/${processId}/files`, form)
      const filled = raw.symbols
        ? Object.entries(raw.symbols).some(
            ([key, item]) =>
              key !== 'file_id' &&
              key !== 'free_text' &&
              item != null &&
              item.value != null &&
              item.value !== '',
          )
        : Boolean(raw.extraction?.text)
      results.push({
        hash: raw.file_hash,
        nombre: raw.name,
        bytes: file.size,
        tiene_texto: filled,
        ingerido: new Date().toISOString(),
      })
    }
    return results
  },
  listSources: async (processId) => {
    const items = await get<
      { name: string; origin: string; rows: number; loaded_at: string }[]
    >(`/processes/${processId}/sources`)
    return items.map((item) => ({
      nombre: item.name,
      origen: item.origin,
      filas: item.rows,
      cargada: item.loaded_at,
    }))
  },
  uploadWorkbook: async (processId, file, cutOffDate = '2026-09-18') => {
    const form = new FormData()
    form.append('file', file)
    form.append('cut_off_date', cutOffDate)
    const raw = await upload<{
      sources: { name: string; rows: number }[]
      file_hash: string
    }>(`/processes/${processId}/sources/workbook`, form)
    return raw.sources.map((item) => ({
      nombre: item.name,
      origen: file.name,
      filas: item.rows,
      cargada: new Date().toISOString(),
    }))
  },
  uploadSource: async (processId, name, file) => {
    const loads = await liveClient.uploadWorkbook(processId, file)
    return loads.find((item) => item.nombre === name) ?? loads[0]
  },
  syncErp: async (processId) => {
    const raw = await post<{ origin: string; rows: number }>(
      `/processes/${processId}/sources/erp/sync`,
    )
    return {
      nombre: 'erp',
      origen: raw.origin,
      filas: raw.rows,
      cargada: new Date().toISOString(),
    }
  },

  listLlmConfig: async () => {
    const cases = await get<RawUseCase[]>('/use-cases')
    const details = await Promise.all(
      cases.map((item) => get<RawUseCaseDetail>(`/use-cases/${item.id}`)),
    )
    return details.flatMap((item) =>
      item.agents.map((agent) => ({
        papel: `${item.id}:${agent.role}`,
        modelo: agent.config.model ?? '',
      })),
    )
  },
  setLlmConfig: async (key, model) => {
    const [useCaseId, role] = key.split(':')
    const detail = await get<RawUseCaseDetail>(`/use-cases/${useCaseId}`)
    const current = detail.agents.find((agent) => agent.role === role)
    const raw = await put<RawAgentConfig>(`/use-cases/${useCaseId}/agents/${role}`, {
      config: { ...current?.config, model },
      note: 'Cambiado desde la consola',
    })
    return { papel: `${useCaseId}:${raw.role}`, modelo: raw.config.model ?? '' }
  },
}
