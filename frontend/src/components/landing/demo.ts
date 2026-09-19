/** Real Norma_Pagos_v3, the checks the normalizer emitted, and three traces from the run. */

export const NORM = `1. Pagar solo si el NIF está en el maestro y el IBAN de la factura coincide con el maestro.
2. El pedido debe existir, pertenecer al proveedor y el importe de la factura debe ser igual al del pedido (tolerancia 0,01 EUR).
3. El IVA debe estar bien calculado y el total debe ser base + IVA, con la misma tolerancia de 0,01 EUR.
4. La fecha debe ser válida y no futura.
5. Estado ERP del pedido: PENDIENTE. Nunca pagar dos veces el mismo pedido.
6. Cualquier anomalía que un humano deba ver: ESCALAR con motivo. Ante duda razonable, escalar antes que pagar.`

export type Sample = { name: string; pass: boolean }

export type RuleSpec = {
  id: string
  text: string
  decision: 'NO_PAGAR' | 'ESCALAR'
  tests: number
  from: number
  samples: Sample[]
}

export const RULES: RuleSpec[] = [
  {
    id: '50',
    text: 'El NIF está en el maestro',
    decision: 'NO_PAGAR',
    tests: 10,
    from: 1,
    samples: [
      { name: 'B46102331 en maestro', pass: true },
      { name: 'B87654321 desconocido', pass: false },
    ],
  },
  {
    id: '51',
    text: 'El IBAN coincide con el maestro',
    decision: 'NO_PAGAR',
    tests: 8,
    from: 1,
    samples: [
      { name: 'IBAN = maestro', pass: true },
      { name: 'IBAN de otro proveedor', pass: false },
    ],
  },
  {
    id: '52',
    text: 'El pedido existe',
    decision: 'NO_PAGAR',
    tests: 9,
    from: 2,
    samples: [
      { name: 'PO-2026-0096', pass: true },
      { name: 'PO-2026-9999', pass: false },
    ],
  },
  {
    id: '53',
    text: 'El pedido es de este proveedor',
    decision: 'NO_PAGAR',
    tests: 10,
    from: 2,
    samples: [
      { name: 'mismo NIF que el pedido', pass: true },
      { name: 'pedido de otro NIF', pass: false },
    ],
  },
  {
    id: '54',
    text: 'Total = pedido (±0,01 €)',
    decision: 'NO_PAGAR',
    tests: 12,
    from: 2,
    samples: [
      { name: '3.012,89 = 3.012,89', pass: true },
      { name: '12.874,40 ≠ 12.847,40', pass: false },
    ],
  },
  {
    id: '55',
    text: 'IVA = base × tipo',
    decision: 'NO_PAGAR',
    tests: 10,
    from: 3,
    samples: [
      { name: '21% sobre base', pass: true },
      { name: 'IVA redondeado mal', pass: false },
    ],
  },
  {
    id: '56',
    text: 'Total = base + IVA',
    decision: 'NO_PAGAR',
    tests: 8,
    from: 3,
    samples: [
      { name: 'base + IVA', pass: true },
      { name: 'falta 0,10 €', pass: false },
    ],
  },
  {
    id: '57',
    text: 'La fecha existe en el calendario',
    decision: 'NO_PAGAR',
    tests: 10,
    from: 4,
    samples: [
      { name: '2026-01-08', pass: true },
      { name: '2026-02-31', pass: false },
    ],
  },
  {
    id: '58',
    text: 'La fecha no es futura',
    decision: 'NO_PAGAR',
    tests: 7,
    from: 4,
    samples: [
      { name: 'fecha de factura ≤ hoy', pass: true },
      { name: '2027-01-01', pass: false },
    ],
  },
  {
    id: '59',
    text: 'El pedido sigue PENDIENTE en el ERP',
    decision: 'NO_PAGAR',
    tests: 9,
    from: 5,
    samples: [
      { name: 'erp.status = PENDIENTE', pass: true },
      { name: 'erp.status = PAGADA', pass: false },
    ],
  },
  {
    id: '60',
    text: 'El pedido no está ya pagado',
    decision: 'NO_PAGAR',
    tests: 11,
    from: 5,
    samples: [
      { name: 'sin pago previo', pass: true },
      { name: 'pedido duplicado', pass: false },
    ],
  },
]

export const PACK = {
  name: 'Invoice payment',
  version: 'v3',
  hash: '847e81a7fc67',
  origin: 'Norma_Pagos_v3',
}

export type Check = {
  rule: string
  ok: boolean
  reason?: string
}

export type Invoice = {
  file: string
  who: string
  amount: string
  decision: 'PAGAR' | 'NO_PAGAR' | 'ESCALAR'
  reason: string
  origin?: string
  symbols: { name: string; value: string; source: string }[]
  checks: Check[]
  delay: number
}

const ALL_OK: Check[] = RULES.map((rule) => ({ rule: rule.text, ok: true }))

export const INVOICES: Invoice[] = [
  {
    file: '2026-01-08_P001.pdf',
    who: 'PO-2026-0096',
    amount: '3.012,89 €',
    decision: 'PAGAR',
    reason: 'Ninguna regla dispara. PAGAR es el defecto.',
    origin: 'pdf-text',
    delay: 0,
    symbols: [
      { name: 'issuer_nif', value: 'B46102331', source: 'pdf-text' },
      { name: 'total', value: '3.012,89', source: 'pdf-text' },
      { name: 'purchase_order', value: 'PO-2026-0096', source: 'pdf-text' },
      { name: 'date', value: '2026-01-08', source: 'pdf-text' },
    ],
    checks: ALL_OK,
  },
  {
    file: '2026-03-19_P008.pdf',
    who: 'Seguridad Alcores',
    amount: '1.137,40 €',
    decision: 'NO_PAGAR',
    reason: 'IMPOSSIBLE_DATE 2026-02-31',
    origin: 'pdf-text',
    delay: 0,
    symbols: [
      { name: 'issuer_nif', value: 'B91455230', source: 'pdf-text' },
      { name: 'total', value: '1.137,40', source: 'pdf-text' },
      { name: 'purchase_order', value: 'PO-2026-0495', source: 'pdf-text' },
      { name: 'date', value: '2026-02-31', source: 'pdf-text' },
    ],
    checks: RULES.map((rule) =>
      rule.id === '57'
        ? { rule: rule.text, ok: false, reason: 'IMPOSSIBLE_DATE 2026-02-31' }
        : { rule: rule.text, ok: true },
    ),
  },
  {
    file: 'copia_2026_0518.pdf',
    who: 'escaneo',
    amount: '',
    decision: 'ESCALAR',
    reason: 'MISSING_DATA: base, date, iban, issuer_nif, purchase_order, total, vat_amount, vat_rate',
    origin: 'ocr',
    delay: 1,
    symbols: [],
    checks: [{ rule: 'Símbolos obligatorios presentes', ok: false, reason: 'MISSING_DATA' }],
  },
  {
    file: 'FA-5077.pdf',
    who: 'Talleres Guadaira',
    amount: '12.874,40 €',
    decision: 'NO_PAGAR',
    reason: 'total 12.874,40 ≠ pedido 12.847,40',
    origin: 'pdf-text',
    delay: 1,
    symbols: [
      { name: 'total', value: '12.874,40', source: 'pdf-text' },
      { name: 'orders.total_amount', value: '12.847,40', source: 'Excel, Pedidos_2026' },
      { name: 'purchase_order', value: 'PO-2026-0018', source: 'pdf-text' },
    ],
    checks: RULES.map((rule) =>
      rule.id === '54'
        ? { rule: rule.text, ok: false, reason: '12.874,40 ≠ 12.847,40' }
        : { rule: rule.text, ok: true },
    ),
  },
  {
    file: '2026-03-28_P002.pdf',
    who: 'PO-2026-0144',
    amount: '890,15 €',
    decision: 'NO_PAGAR',
    reason: 'erp.status = PAGADA',
    origin: 'pdf-text',
    delay: 2,
    symbols: [
      { name: 'purchase_order', value: 'PO-2026-0144', source: 'pdf-text' },
      { name: 'erp.status', value: 'PAGADA', source: 'ERP 2009' },
    ],
    checks: RULES.map((rule) =>
      rule.id === '59'
        ? { rule: rule.text, ok: false, reason: 'PAGADA' }
        : { rule: rule.text, ok: true },
    ),
  },
  {
    file: 'FA-2508.pdf',
    who: 'B87654321',
    amount: '2.140,00 €',
    decision: 'NO_PAGAR',
    reason: 'NIF B87654321 no está en el maestro',
    origin: 'pdf-text',
    delay: 2,
    symbols: [
      { name: 'issuer_nif', value: 'B87654321', source: 'pdf-text' },
      { name: 'purchase_order', value: 'PO-2026-9999', source: 'pdf-text' },
    ],
    checks: RULES.map((rule) =>
      rule.id === '50'
        ? { rule: rule.text, ok: false, reason: 'NIF desconocido' }
        : { rule: rule.text, ok: true },
    ),
  },
]

export const DROP_FILES = [
  ...INVOICES.map((item) => item.file),
  'scan_017.pdf',
  '2026-01-12_P010.pdf',
]

export const RESULT = {
  pagar: 433,
  nopagar: 36,
  escalar: 31,
  match: '471/471',
  engine: '0,63 s',
  compile: '84,7 s',
  trace: '01a0b790db2a9a3b',
}

export const STAGES = ['Lectura', 'Símbolos', 'Reglas', 'Decisión'] as const
