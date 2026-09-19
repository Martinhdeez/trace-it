import type { DecisionType, InstanceOut, RuleStatus } from '../api/contracts'

/**
 * Outcome names are defined per process, so colours are a lookup with a neutral
 * fallback rather than a closed enum.
 */
const POSITIVE = 'bg-pagar-soft text-pagar'
const ATTENTION = 'bg-escalar-soft text-escalar'
const NEGATIVE = 'bg-nopagar-soft text-nopagar'

const TONES: Record<string, string> = {
  PAGAR: POSITIVE,
  APROBAR: POSITIVE,
  NO_PAGAR: NEGATIVE,
  RECHAZAR: NEGATIVE,
  ESCALAR: ATTENTION,
  REVISAR: ATTENTION,
  PENDING: 'bg-ocr-soft text-ocr',
  PENDIENTE: 'bg-ocr-soft text-ocr',
  ok: 'bg-pagar-soft text-pagar',
  degraded: 'bg-escalar-soft text-escalar',
  down: 'bg-nopagar-soft text-nopagar',
  active: 'bg-pagar-soft text-pagar',
  compiling: 'bg-ocr-soft text-ocr',
  blocked: 'bg-escalar-soft text-escalar',
  draft: 'bg-ocr-soft text-ocr',
  retired: 'bg-ocr-soft text-muted',
}

export type DecisionMeta = Pick<DecisionType, 'name' | 'is_default' | 'requires_human'>

/**
 * A decision type's tone comes from its metadata: the default is positive, one that
 * waits for a person is attention, anything else is negative. The lookup above only
 * covers what has no metadata (states, or a caller that has no process at hand).
 */
export function tone(value: string, decisionTypes?: DecisionMeta[]): string {
  const type = decisionTypes?.find((item) => item.name === value)
  if (type) return type.is_default ? POSITIVE : type.requires_human ? ATTENTION : NEGATIVE
  return TONES[value] ?? 'bg-ocr-soft text-ocr'
}

/** What the instance shows in a list: its decision, or the internal state. */
export function label(instance: Pick<InstanceOut, 'status' | 'decision'>): string {
  if (instance.status === 'DECIDED' && instance.decision) return instance.decision
  return instance.status
}

export const INSTANCE_STATES = ['PENDING', 'DECIDED'] as const

export const RULE_STATES: RuleStatus[] = ['compiling', 'draft', 'active', 'blocked', 'retired']
