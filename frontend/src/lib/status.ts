import type { Instance, InstanceState, RuleState } from '../api/contracts'

/**
 * Outcome names are defined per process, so colours are a lookup with a neutral
 * fallback rather than a closed enum.
 */
const TONES: Record<string, string> = {
  PAGAR: 'bg-pagar-soft text-pagar',
  APROBAR: 'bg-pagar-soft text-pagar',
  NO_PAGAR: 'bg-nopagar-soft text-nopagar',
  RECHAZAR: 'bg-nopagar-soft text-nopagar',
  ESCALAR: 'bg-escalar-soft text-escalar',
  REVISAR: 'bg-escalar-soft text-escalar',
  REVISION: 'bg-escalar-soft text-escalar',
  PENDIENTE: 'bg-ocr-soft text-ocr',
  activa: 'bg-pagar-soft text-pagar',
  borrador: 'bg-ocr-soft text-ocr',
  rechazada: 'bg-nopagar-soft text-nopagar',
  retirada: 'bg-ocr-soft text-muted',
}

export function tone(value: string): string {
  return TONES[value] ?? 'bg-ocr-soft text-ocr'
}

/** What the instance shows in a list: its decision, or the internal state. */
export function label(instance: Pick<Instance, 'estado' | 'decision'>): string {
  if (instance.estado === 'DECIDIDA' && instance.decision) return instance.decision
  return instance.estado
}

export const INSTANCE_STATES: InstanceState[] = ['PENDIENTE', 'REVISION', 'DECIDIDA']

export const RULE_STATES: RuleState[] = ['borrador', 'activa', 'rechazada', 'retirada']
