export const paths = {
  landing: '/',
  processes: '/processes',
  newProcess: '/processes/new',
  process: (id: number | string) => `/processes/${id}`,
  rules: (id: number | string) => `/processes/${id}/rules`,
  rule: (processId: number | string, ruleId: number | string) =>
    `/processes/${processId}/rules/${ruleId}`,
  instances: (id: number | string) => `/processes/${id}/instances`,
  instance: (processId: number | string, instanceId: number | string) =>
    `/processes/${processId}/instances?i=${instanceId}`,
  queue: (id: number | string) => `/processes/${id}/queue`,
  audit: (id: number | string) => `/processes/${id}/audit`,
  sources: (id: number | string) => `/processes/${id}/sources`,
  settings: '/settings',
} as const

/** The process id that owns the current screen, if any. */
export function processFromPath(pathname: string): number | undefined {
  const match = pathname.match(/\/processes\/(\d+)/)
  return match ? Number(match[1]) : undefined
}
