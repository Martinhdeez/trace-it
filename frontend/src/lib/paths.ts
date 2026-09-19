export const paths = {
  landing: '/',
  login: '/login',
  processes: '/processes',
  newProcess: '/processes/new',
  process: (id: number | string) => `/processes/${id}`,
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
  instances: (id: number | string) => `/processes/${id}/instances`,
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
