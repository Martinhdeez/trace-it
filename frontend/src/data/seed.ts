/**
 * The invoice-payment template of "Nuevo proceso": the decision types and symbols of
 * `processes/invoice-payment.json`, with the pack's own names.
 */
import type { DecisionType, SymbolIO } from '../api/contracts'

export const invoiceDecisionTypes: DecisionType[] = [
  { name: 'ESCALAR', priority: 3, is_default: false, requires_human: true },
  { name: 'NO_PAGAR', priority: 2, is_default: false, requires_human: false },
  { name: 'PAGAR', priority: 1, is_default: true, requires_human: false },
]

export const invoiceSymbols: SymbolIO[] = [
  { name: 'issuer_nif', type: 'text', description: 'NIF del emisor de la factura', required: true },
  { name: 'iban', type: 'text', description: 'IBAN de cobro que figura en la factura', required: true },
  { name: 'invoice_number', type: 'text', description: 'Número de factura tal cual', required: true },
  { name: 'date', type: 'date', description: 'Fecha de emisión como AAAA-MM-DD', required: true },
  { name: 'purchase_order', type: 'text', description: 'Pedido citado en la factura', required: true },
  { name: 'base', type: 'number', description: 'Base imponible', required: true },
  { name: 'vat_rate', type: 'number', description: 'Porcentaje de IVA impreso', required: true },
  { name: 'vat_amount', type: 'number', description: 'Cuota de IVA', required: true },
  { name: 'total', type: 'number', description: 'Total de la factura', required: true },
]
