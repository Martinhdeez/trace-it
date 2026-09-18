import type { Process, Run } from '../api/types'
import { PROCESS } from '../lib/paths'
import { catalogCounts, cajaFileCount } from './catalog'
import { processCopy } from '../i18n'

export const processes: Process[] = [
  {
    id: PROCESS.reconcilePayments,
    instanceCount: cajaFileCount,
  },
  {
    id: PROCESS.landRegistry,
    instanceCount: 0,
  },
  {
    id: PROCESS.vendorOnboarding,
    instanceCount: 0,
  },
].map((item) => ({
  ...item,
  ...processCopy(item.id),
}))

const cajaCounts = catalogCounts('run-014')

export const initialRuns: Run[] = [
  {
    id: 'run-014',
    processId: PROCESS.reconcilePayments,
    label: 'Run 014',
    status: 'en_curso',
    normaVersion: 'v3',
    costPerFile: 0.012,
    fileCount: cajaFileCount,
    startedAt: '2026-09-18T11:39:00',
    thumbnail: 'mix',
    counts: cajaCounts,
  },
  {
    id: 'run-013',
    processId: PROCESS.reconcilePayments,
    label: 'Run 013',
    status: 'completado',
    normaVersion: 'v3',
    costPerFile: 0.011,
    fileCount: cajaFileCount,
    startedAt: '2026-09-17T18:02:00',
    thumbnail: 'pagar',
    counts: { pagar: 441, noPagar: 22, escalar: 37, pending: 0 },
  },
]
