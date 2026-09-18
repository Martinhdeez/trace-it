import type { Decision, InstanceDetail, QueueItem } from '../api/types'
import { processVersionDiffs } from '../data/versions'

export function applyQueueVersion(
  items: QueueItem[],
  processId: string,
  versionId: string,
): QueueItem[] {
  const diffs = processVersionDiffs[processId]?.[versionId] ?? []
  if (!diffs.length) return items
  return items.map((item) => {
    const diff = diffs.find((entry) => entry.instanceId === item.id)
    if (!diff) return item
    return {
      ...item,
      result: diff.to,
      reason: diff.reason,
      state: diff.to === 'ESCALAR' ? 'PENDIENTE_HUMANO' : 'DECIDIDA',
    }
  })
}

export function applyDetailVersion(
  detail: InstanceDetail | undefined,
  processId: string,
  versionId: string,
): InstanceDetail | undefined {
  if (!detail) return detail
  const diff = (processVersionDiffs[processId]?.[versionId] ?? []).find(
    (entry) => entry.instanceId === detail.id,
  )
  if (!diff) return detail
  return {
    ...detail,
    result: diff.to,
    reason: diff.reason,
    state: diff.to === 'ESCALAR' ? 'PENDIENTE_HUMANO' : 'DECIDIDA',
    meta: { ...detail.meta, norma: `Norma ${versionId}` },
  }
}

export function countsForVersion(
  items: QueueItem[],
  processId: string,
  versionId: string,
): { pagar: number; noPagar: number; escalar: number; pending: number } {
  const applied = applyQueueVersion(items, processId, versionId)
  return applied.reduce(
    (acc, item) => {
      if (item.result === 'PAGAR') acc.pagar += 1
      else if (item.result === 'NO_PAGAR') acc.noPagar += 1
      else if (item.result === 'ESCALAR') acc.escalar += 1
      else acc.pending += 1
      return acc
    },
    { pagar: 0, noPagar: 0, escalar: 0, pending: 0 },
  )
}

export function decisionLabel(value: Decision | null): string {
  if (!value) return 'OCR'
  return value.replaceAll('_', ' ')
}
