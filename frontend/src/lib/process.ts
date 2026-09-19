import type { Outcome, ProcessDetail } from '../api/contracts'

export type DecisionTone = 'positive' | 'attention' | 'negative'

/** The default outcome is positive, one that waits for a person is attention, the rest are negative. */
export function decisionTone(process: ProcessDetail | undefined, name: string): DecisionTone {
  const type = process?.tipos_decision.find((item) => item.nombre === name)
  if (type?.por_defecto) return 'positive'
  if (type?.requiere_persona) return 'attention'
  return 'negative'
}

/** Outcomes the process sends to a person. Nothing here is hardcoded per process (P19). */
export function humanOutcomes(process: ProcessDetail | undefined): Outcome[] {
  return (process?.tipos_decision ?? []).filter((outcome) => outcome.requiere_persona)
}

export function byPriority(outcomes: Outcome[]): Outcome[] {
  return [...outcomes].sort((a, b) => b.prioridad - a.prioridad)
}
