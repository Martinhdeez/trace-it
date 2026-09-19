import type { InstanceDetail, InstanceTrace } from '../../api/contracts'
import { INVOICES, PACK, RULES } from './demo'

/** Display fixtures for the animated walkthrough. No API operations are performed. */
export const DEMO_TIME = '2026-09-19T10:30:00Z'
export const DEMO_PROMPT =
  'Quiero decidir qué facturas pagar. Comprueba el proveedor, el IBAN, el pedido y los importes. Si falta información, que lo revise una persona.'
export const DEMO_RESPONSE =
  'He preparado el proceso de pago de facturas a partir de tu norma. Puedes revisar las reglas, las fuentes y los resultados esperados antes de publicar.'
export const DEMO_FILES = [
  {
    id: 'norm',
    name: 'Norma_Pagos_v3.xlsx',
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  },
  {
    id: 'suppliers',
    name: 'Proveedores.xlsx',
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  },
]
export const CHAPTERS = [
  {
    id: 'describe',
    title: 'Cuéntale qué tiene que decidir.',
    detail: 'Una conversación y tus documentos.',
    label: 'Definir',
    duration: 7000,
  },
  {
    id: 'review',
    title: 'Las reglas se revisan contigo.',
    detail: 'Qué comprueba cada regla y qué fuentes necesita.',
    label: 'Revisar',
    duration: 5000,
  },
  {
    id: 'prepare',
    title: 'Primero se prueba. Después se publica.',
    detail: 'Compilación y ejemplos antes de publicar.',
    label: 'Comprobar',
    duration: 6500,
  },
  {
    id: 'publish',
    title: 'Tú das el visto bueno.',
    detail: 'Una versión publicada. Las mismas reglas para todos.',
    label: 'Publicar',
    duration: 4000,
  },
  {
    id: 'upload',
    title: 'Entran las facturas.',
    detail: 'El documento se convierte en datos con origen.',
    label: 'Recibir',
    duration: 4500,
  },
  {
    id: 'run',
    title: 'Cada factura encuentra su respuesta.',
    detail: 'Pagar, no pagar o escalar. Con un motivo.',
    label: 'Decidir',
    duration: 5500,
  },
  {
    id: 'trace',
    title: 'Y cada respuesta tiene sus pruebas.',
    detail: 'Abre el caso. Sigue las reglas. Llega al dato.',
    label: 'Trazar',
    duration: 8500,
  },
] as const

export const DEMO_PREVIEW = {
  valid: true,
  compilations: RULES.map((rule) => ({ proposal: rule.text, report: { valid: true } })),
  examples: [INVOICES[0], INVOICES[3], INVOICES[2]].map((invoice) => ({
    name: invoice.file,
    expected: invoice.decision,
    actual: invoice.decision,
    passed: true,
  })),
}

export function demoInstance(index: number, decided = true): InstanceDetail {
  const invoice = INVOICES[index]
  return {
    id: index + 1,
    name: invoice.file,
    status: decided ? 'DECIDED' : 'PENDING',
    decision: decided ? invoice.decision : null,
    review_pending: false,
    author: decided ? 'engine' : null,
    reason: decided ? invoice.reason : null,
    file_hash: `demo-${index}`,
    reviews: [],
    events: [],
    symbols: Object.fromEntries(
      invoice.symbols.map((symbol) => [
        symbol.name,
        { value: symbol.value, origin: symbol.source },
      ]),
    ),
    decisions: decided
      ? [
          {
            id: index + 1,
            decision: invoice.decision,
            author: 'engine',
            reason: invoice.reason,
            rules_hash: PACK.hash,
            results: [],
            created_at: DEMO_TIME,
          },
        ]
      : [],
  }
}

export function demoTrace(index: number): InstanceTrace {
  const instance = demoInstance(index)
  return {
    id: instance.id,
    process_id: 1,
    name: instance.name,
    status: instance.status,
    file: null,
    symbols: instance.symbols,
    decisions: [
      {
        ...instance.decisions[0],
        rule_results: INVOICES[index].checks.map((check, i) => ({
          rule_id: i + 1,
          hash: null,
          fires: !check.ok,
          reason: check.reason ?? '',
          rule_text: check.rule,
          rule_summary: check.rule,
          norm_rule_id: null,
        })),
      },
    ],
    exported_decision: instance.decision,
    spans: [],
    sources_read: [],
    version: null,
    pending: { waiting_for_person: false, review_pending: false, proposals: [], alerts: [] },
  }
}
