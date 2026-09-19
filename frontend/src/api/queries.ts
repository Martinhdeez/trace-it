import type { InstanceFilters, RuleStatus } from './contracts'

/** One place for the cache keys, so a mutation knows what to invalidate. */
export const keys = {
  users: ['users'] as const,
  processes: ['processes'] as const,
  process: (id: number) => ['process', id] as const,
  rules: (processId: number, status?: RuleStatus) => ['rules', processId, status ?? 'all'] as const,
  norm: (processId: number) => ['norm', processId] as const,
  rule: (id: number) => ['rule', id] as const,
  instances: (processId: number, filters?: InstanceFilters) =>
    ['instances', processId, filters ?? 'all'] as const,
  instance: (id: number) => ['instance', id] as const,
  document: (instanceId: number) => ['document', instanceId] as const,
  trace: (instanceId: number) => ['trace', instanceId] as const,
  runs: (processId: number) => ['runs', processId] as const,
  alerts: (processId: number, status: string) => ['alerts', processId, status] as const,
  run: (id: number) => ['run', id] as const,
  queue: (processId: number, outcome: string) => ['queue', processId, outcome] as const,
  suggestion: (instanceId: number) => ['suggestion', instanceId] as const,
  /** The open escalation proposal of one case. */
  caseProposal: (instanceId: number) => ['proposals', 'case', instanceId] as const,
  proposals: (processId: number, status: string) => ['proposals', processId, status] as const,
  findings: (processId: number) => ['findings', processId] as const,
  sources: (processId: number) => ['sources', processId] as const,
  source: (processId: number, name: string) => ['sources', processId, name] as const,
  useCases: ['use-cases'] as const,
  useCase: (id: number) => ['use-case', id] as const,
  summary: (processId: number) => ['summary', processId] as const,
  planeMetrics: (processId: number, plane: string) => ['metrics', processId, plane] as const,
  processMetrics: (processId: number) => ['metrics', processId, 'providers'] as const,
  planesHealth: ['health', 'planes'] as const,
  draft: (processId: number) => ['draft', processId] as const,
  versions: (processId: number) => ['versions', processId] as const,
  execution: (processId: number) => ['execution', processId] as const,
}

/** After a decision moves, everything that counts instances is stale. */
export const families = {
  decisions: ['instances', 'instance', 'queue', 'findings', 'summary', 'alerts', 'trace'],
  rules: ['rules', 'rule'],
  /** Settling a proposal can resolve a case or change the draft. */
  proposals: ['proposals', 'summary', 'draft', 'execution', 'queue', 'instance', 'instances', 'alerts', 'trace'],
}
