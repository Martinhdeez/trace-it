import type { DecisionType, ProcessDetail } from '../api/contracts'

export type DecisionTone = 'positive' | 'attention' | 'negative'

/** The default outcome is positive, one that waits for a person is attention, the rest are negative. */
export function decisionTone(process: ProcessDetail | undefined, name: string): DecisionTone {
  const type = process?.decision_types.find((item) => item.name === name)
  if (type?.is_default) return 'positive'
  if (type?.requires_human) return 'attention'
  return 'negative'
}

/** Outcomes the process sends to a person. Nothing here is hardcoded per process (P19). */
export function humanOutcomes(process: ProcessDetail | undefined): DecisionType[] {
  return (process?.decision_types ?? []).filter((outcome) => outcome.requires_human)
}

export function byPriority(outcomes: DecisionType[]): DecisionType[] {
  return [...outcomes].sort((a, b) => b.priority - a.priority)
}
