/**
 * Seed for the "Pago de facturas" process: outcomes, symbols and the norma v3
 * rules, written as text the way a manager would type them. The backend loads
 * the same thing from `procesos/pago-facturas.json`.
 */
import type { Outcome, ProcessSymbol, RuleKind, RuleState } from '../api/contracts'

export const LLM_ROLES = [
  'compilador_a',
  'compilador_b',
  'extractor_1',
  'extractor_2',
  'asistente',
] as const

export const invoiceOutcomes: Outcome[] = [
  { nombre: 'ESCALAR', prioridad: 3, por_defecto: false, requiere_persona: true },
  { nombre: 'NO_PAGAR', prioridad: 2, por_defecto: false, requiere_persona: false },
  { nombre: 'PAGAR', prioridad: 1, por_defecto: true, requiere_persona: false },
]

export const invoiceSymbols: ProcessSymbol[] = [
  { nombre: 'nif_emisor', tipo: 'texto', descripcion: 'NIF del emisor de la factura' },
  { nombre: 'iban', tipo: 'texto', descripcion: 'IBAN de cobro que figura en la factura' },
  { nombre: 'numero_factura', tipo: 'texto', descripcion: 'Número de factura tal cual' },
  { nombre: 'pedido', tipo: 'texto', descripcion: 'Pedido citado en la factura' },
  { nombre: 'base', tipo: 'numero', descripcion: 'Base imponible' },
  { nombre: 'tipo_iva', tipo: 'numero', descripcion: 'Porcentaje de IVA impreso' },
  { nombre: 'cuota_iva', tipo: 'numero', descripcion: 'Cuota de IVA' },
  { nombre: 'total', tipo: 'numero', descripcion: 'Total de la factura' },
  { nombre: 'fecha', tipo: 'texto', descripcion: 'Fecha de emisión como AAAA-MM-DD' },
]

/** Hints the mock compiler uses to write plausible code and tests. */
export type RuleHints = {
  reason: string
  symbol: string
  body: string
  passing: string
  failing: string
}

export type SeedRule = RuleHints & {
  texto: string
  tipo: RuleKind
  decision: string
  estado: RuleState
}

export const seedRules: SeedRule[] = [
  {
    texto: 'El NIF del emisor está en el maestro de proveedores.',
    tipo: 'requisito',
    decision: 'NO_PAGAR',
    estado: 'activa',
    reason: 'NIF_DESCONOCIDO',
    symbol: 'nif_emisor',
    body: 'salta = valor not in {p["nif"] for p in fuentes["proveedores"]}',
    passing: 'B46102331',
    failing: 'B00000000',
  },
  {
    texto: 'El IBAN de la factura coincide con el IBAN del proveedor en el maestro.',
    tipo: 'requisito',
    decision: 'NO_PAGAR',
    estado: 'activa',
    reason: 'IBAN_DISTINTO',
    symbol: 'iban',
    body: 'salta = normalizar(valor) not in {normalizar(p["iban"]) for p in proveedor}',
    passing: 'ES21 0049 1500 0512 3456 7890',
    failing: 'ES76 2100 0418 4502 0005 1332',
  },
  {
    texto: 'El pedido citado existe en el maestro y pertenece a ese proveedor.',
    tipo: 'requisito',
    decision: 'NO_PAGAR',
    estado: 'activa',
    reason: 'PEDIDO_INEXISTENTE',
    symbol: 'pedido',
    body: 'salta = not any(p["pedido"] == valor for p in fuentes["pedidos"])',
    passing: 'PO-2026-0096',
    failing: 'PO-2026-9999',
  },
  {
    texto: 'El total de la factura coincide con el importe del pedido, con 0,01 € de margen.',
    tipo: 'requisito',
    decision: 'NO_PAGAR',
    estado: 'activa',
    reason: 'IMPORTE_DISTINTO',
    symbol: 'total',
    body: 'salta = abs(centimos(valor) - centimos(pedido["importe_total"])) > 1',
    passing: '6953.04',
    failing: '7100.00',
  },
  {
    texto: 'La base más la cuota de IVA dan el total, con 0,01 € de margen.',
    tipo: 'requisito',
    decision: 'NO_PAGAR',
    estado: 'activa',
    reason: 'TOTAL_INCORRECTO',
    symbol: 'total',
    body:
      'salta = abs(centimos(instancia["base"]) + centimos(instancia["cuota_iva"]) - centimos(valor)) > 1',
    passing: '6953.04',
    failing: '6900.00',
  },
  {
    texto: 'La fecha de la factura es una fecha real del calendario.',
    tipo: 'requisito',
    decision: 'NO_PAGAR',
    estado: 'activa',
    reason: 'FECHA_IMPOSIBLE',
    symbol: 'fecha',
    body: 'salta = not es_fecha(valor)',
    passing: '2026-01-08',
    failing: '2026-02-31',
  },
  {
    texto: 'El ERP marca ese pedido como PAGADA.',
    tipo: 'prohibicion',
    decision: 'NO_PAGAR',
    estado: 'activa',
    reason: 'PEDIDO_PAGADO',
    symbol: 'pedido',
    body: 'salta = asiento["estado"] != "PENDIENTE"',
    passing: 'PO-2026-0096',
    failing: 'PO-2026-0471',
  },
  {
    texto: 'Varias instancias del proceso citan el mismo pedido.',
    tipo: 'prohibicion',
    decision: 'ESCALAR',
    estado: 'activa',
    reason: 'PEDIDO_DUPLICADO',
    symbol: 'pedido',
    body: 'salta = any(normalizar(o.get("pedido")) == normalizar(valor) for o in otras)',
    passing: 'PO-2026-0096',
    failing: 'PO-2026-0007',
  },
  {
    texto: 'El tipo de IVA impreso es distinto de 21.',
    tipo: 'prohibicion',
    decision: 'ESCALAR',
    estado: 'borrador',
    reason: 'IVA_NO_ESTANDAR',
    symbol: 'tipo_iva',
    body: 'salta = Decimal(str(valor)) != Decimal("21")',
    passing: '21',
    failing: '10',
  },
]
