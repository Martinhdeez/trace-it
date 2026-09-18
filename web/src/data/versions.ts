import type { Decision } from '../api/types'
import { PROCESS } from '../lib/paths'
import { instanceId } from '../lib/ids'

export type RuleVersion = {
  id: string
  label: string
  status: 'activa' | 'borrador'
  date: string
  notes: string
  clauses: string[]
}

export type VersionDiff = {
  instanceId: string
  fileId: string
  from: Decision
  to: Decision
  reason: string
}

const reconcileV3: RuleVersion = {
  id: 'v3',
  label: 'Norma v3',
  status: 'activa',
  date: '2026-09-12',
  notes: 'Caja lote 1. Seis cláusulas. Ante duda, ESCALAR.',
  clauses: [
    'NIF en maestro e IBAN igual al maestro',
    'Pedido existe, es del proveedor, importe ±0,01 €',
    'IVA y total cierran ±0,01 €',
    'Fecha válida y no futura',
    'ERP PENDIENTE; no pagar un pedido dos veces',
    'Anomalía que debe ver un humano: ESCALAR',
  ],
}

const reconcileV4: RuleVersion = {
  id: 'v4',
  label: 'Norma v4',
  status: 'borrador',
  date: '2026-09-19',
  notes: 'Lote 2. Importe distinto deja de escalar: es NO_PAGAR.',
  clauses: [
    'NIF en maestro e IBAN igual al maestro',
    'Pedido existe, es del proveedor',
    'Importe ≠ pedido ±0,01 € → NO_PAGAR',
    'IVA y total cierran ±0,01 €',
    'Fecha válida y no futura',
    'ERP PENDIENTE; no pagar un pedido dos veces',
    'Resto de anomalías: ESCALAR',
  ],
}

export const processRules: Record<string, RuleVersion[]> = {
  [PROCESS.reconcilePayments]: [reconcileV3, reconcileV4],
  [PROCESS.landRegistry]: [
    {
      id: 'v1',
      label: 'Norma v1',
      status: 'activa',
      date: '2026-09-01',
      notes: 'Lectura de finca, titular y cargas. Ante duda, ESCALAR.',
      clauses: [
        'Finca existe en el maestro',
        'Titular coincide o se marca divergencia',
        'Cargas se copian literales',
      ],
    },
  ],
  [PROCESS.vendorOnboarding]: [
    {
      id: 'v1',
      label: 'Norma v1',
      status: 'activa',
      date: '2026-09-01',
      notes: 'Alta si NIF y IBAN son coherentes.',
      clauses: [
        'NIF de la tarjeta fiscal es válido',
        'IBAN del certificado pertenece al mismo titular',
        'No duplicar un proveedor ya maestro',
      ],
    },
  ],
}

export const processVersionDiffs: Record<string, Record<string, VersionDiff[]>> = {
  [PROCESS.reconcilePayments]: {
    v3: [],
    v4: [
      {
        instanceId: instanceId('2026-01-08_P001.pdf'),
        fileId: '2026-01-08_P001.pdf',
        from: 'ESCALAR',
        to: 'NO_PAGAR',
        reason: 'Importe distinto pasa a NO_PAGAR',
      },
    ],
  },
}

export function rulesFor(processId: string): RuleVersion[] {
  return processRules[processId] ?? []
}

export function defaultVersionId(processId: string): string {
  const versions = rulesFor(processId)
  return versions.find((item) => item.status === 'activa')?.id ?? versions[0]?.id ?? 'v1'
}
