export const PROCESS = {
  reconcilePayments: 'reconcile-payments',
  landRegistry: 'land-registry',
  vendorOnboarding: 'vendor-onboarding',
} as const

export type ProcessId = (typeof PROCESS)[keyof typeof PROCESS]

export const paths = {
  home: '/',
  processes: '/processes',
  processNew: '/processes/new',
  process: (id: string) => `/processes/${id}`,
  processRules: (id: string) => `/processes/${id}/rules`,
  run: (processId: string, runId: string) => `/processes/${processId}/runs/${runId}`,
  runInstance: (processId: string, runId: string, instanceId: string) =>
    `/processes/${processId}/runs/${runId}?i=${instanceId}`,
  runs: '/runs',
  review: '/review',
  settings: '/settings',
} as const

export function processIdFromPath(pathname: string): string | undefined {
  const match = pathname.match(/\/processes\/([^/]+)/)
  const id = match?.[1]
  if (!id || id === 'new') return undefined
  return id
}
