import type { Decision, InstanceState } from '../api/types'

export type BadgeKind = Decision | 'OCR' | 'EN_CURSO' | 'COMPLETADO'

export function decisionFromState(
  result: Decision | null,
  state: InstanceState,
): BadgeKind {
  if (state === 'OCR') return 'OCR'
  if (result) return result
  return 'OCR'
}
