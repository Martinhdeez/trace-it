/** The Revisión tab that lists open alerts. */
export const ALERTS_TAB = 'alertas'

export const paths = {
  landing: '/',
  processes: '/processes',
  newProcess: '/processes/new',
  /** The manager's inbox: what waits for them, and what was already decided. */
  process: (id: number | string) => `/processes/${id}`,
  history: (id: number | string) => `/processes/${id}?vista=historial`,
  /** The console: panel, definition, runs, review and settings, one tab each. */
  panel: (id: number | string) => `/processes/${id}/panel`,
  definition: (id: number | string) => `/processes/${id}/definition`,
  definitionContext: (id: number | string) => `/processes/${id}/definition/contexto`,
  definitionInputs: (id: number | string) => `/processes/${id}/definition/inputs`,
  definitionSources: (id: number | string) => `/processes/${id}/definition/fuentes`,
  knowledge: (id: number | string) => `/processes/${id}/definition/fuentes`,
  versions: (id: number | string) => `/processes/${id}/definition`,
  review: (id: number | string) => `/processes/${id}/review`,
  processSettings: (id: number | string) => `/processes/${id}/settings`,
  rules: (id: number | string) => `/processes/${id}/definition`,
  rule: (processId: number | string, ruleId: number | string) =>
    `/processes/${processId}/rules/${ruleId}`,
  instances: (id: number | string, runId?: number) =>
    `/processes/${id}/instances${runId ? `?run=${runId}` : ''}`,
  instance: (processId: number | string, instanceId: number | string) =>
    `/processes/${processId}/instances?i=${instanceId}`,
  queue: (id: number | string) => `/processes/${id}/review`,
  audit: (id: number | string) => `/processes/${id}/definition`,
  sources: (id: number | string) => `/processes/${id}/definition/fuentes`,
  settings: '/settings',
} as const

/** The process id that owns the current screen, if any. */
export function processFromPath(pathname: string): number | undefined {
  const match = pathname.match(/\/processes\/(\d+)/)
  return match ? Number(match[1]) : undefined
}
