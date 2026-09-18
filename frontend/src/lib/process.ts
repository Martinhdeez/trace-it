import type { Instance, Outcome, ProcessDetail } from '../api/contracts'

/**
 * The counts every screen shows. The backend has no endpoint for them: an
 * instance is four small fields, so the list is the source and this derives
 * from it. One query, one cache entry.
 */
export type Counts = {
  total: number
  pending: number
  review: number
  decided: number
  byOutcome: Record<string, number>
}

export function countsOf(instances: Instance[]): Counts {
  const counts: Counts = { total: instances.length, pending: 0, review: 0, decided: 0, byOutcome: {} }
  for (const instance of instances) {
    if (instance.estado === 'PENDIENTE') counts.pending += 1
    if (instance.estado === 'REVISION') counts.review += 1
    if (instance.estado === 'DECIDIDA') counts.decided += 1
    if (instance.decision) {
      counts.byOutcome[instance.decision] = (counts.byOutcome[instance.decision] ?? 0) + 1
    }
  }
  return counts
}

/** Outcomes the process sends to a person. Nothing here is hardcoded per process (P19). */
export function humanOutcomes(process: ProcessDetail | undefined): Outcome[] {
  return (process?.tipos_decision ?? []).filter((outcome) => outcome.requiere_persona)
}

export function byPriority(outcomes: Outcome[]): Outcome[] {
  return [...outcomes].sort((a, b) => b.prioridad - a.prioridad)
}

/** Everything a person still has to look at: the human outcomes plus REVISION (P21). */
export function waitingOnPerson(
  process: ProcessDetail | undefined,
  counts: Counts | undefined,
): number {
  if (!counts) return 0
  const human = humanOutcomes(process).reduce(
    (total, outcome) => total + (counts.byOutcome[outcome.nombre] ?? 0),
    0,
  )
  return human + counts.review
}
