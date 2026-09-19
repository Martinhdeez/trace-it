import type { InstanceState, RuleState } from './contracts'

/** One place for the cache keys, so a mutation knows what to invalidate. */
export const keys = {
  users: ['users'] as const,
  processes: ['processes'] as const,
  process: (id: number) => ['process', id] as const,
  rules: (processId: number, state?: RuleState) => ['rules', processId, state ?? 'all'] as const,
  norm: (processId: number) => ['norm', processId] as const,
  rule: (id: number) => ['rule', id] as const,
  instances: (processId: number, state?: InstanceState) =>
    ['instances', processId, state ?? 'all'] as const,
  instance: (id: number) => ['instance', id] as const,
  document: (instanceId: number) => ['document', instanceId] as const,
  queue: (processId: number, outcome: string) => ['queue', processId, outcome] as const,
  suggestion: (instanceId: number) => ['suggestion', instanceId] as const,
  findings: (processId: number) => ['findings', processId] as const,
  files: (processId: number) => ['files', processId] as const,
  sources: (processId: number) => ['sources', processId] as const,
  llm: ['llm'] as const,
}

/** After a decision moves, everything that counts instances is stale. */
export const families = {
  decisions: ['instances', 'instance', 'queue', 'findings'],
  rules: ['rules', 'rule'],
}
