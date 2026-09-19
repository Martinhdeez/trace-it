import type { Instance, InstanceOut, Outcome, RuleState } from '../api/contracts'

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
  activa: 'bg-pagar-soft text-pagar',
  compilando: 'bg-ocr-soft text-ocr',
  bloqueada: 'bg-escalar-soft text-escalar',
  borrador: 'bg-ocr-soft text-ocr',
  rechazada: 'bg-nopagar-soft text-nopagar',
  retirada: 'bg-ocr-soft text-muted',
}

export type DecisionMeta = Pick<Outcome, 'nombre' | 'por_defecto' | 'requiere_persona'>

/**
 * A decision type's tone comes from its metadata: the default is positive, one that
 * waits for a person is attention, anything else is negative. The lookup above only
 * covers what has no metadata (states, or a caller that has no process at hand).
 */
export function tone(value: string, decisionTypes?: DecisionMeta[]): string {
  const type = decisionTypes?.find((item) => item.nombre === value)
  if (type) return type.por_defecto ? POSITIVE : type.requiere_persona ? ATTENTION : NEGATIVE
  return TONES[value] ?? 'bg-ocr-soft text-ocr'
}

/** What the instance shows in a list: its decision, or the internal state. */
export function label(instance: Pick<InstanceOut, 'status' | 'decision'>): string {
  if (instance.status === 'DECIDED' && instance.decision) return instance.decision
  return instance.status
}

/** Same, for the trace view, which still reads the Spanish instance detail. */
export function detailLabel(instance: Pick<Instance, 'estado' | 'decision'>): string {
  if (instance.estado === 'DECIDIDA' && instance.decision) return instance.decision
  return instance.estado
}

export const INSTANCE_STATES = ['PENDING', 'DECIDED'] as const

export const RULE_STATES: RuleState[] = ['borrador', 'activa', 'rechazada', 'retirada']
