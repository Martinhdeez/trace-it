/**
 * Shapes the UI owns, not the backend: the invoice facsimile the console draws
 * from the text stored at ingest. The backend contract lives in `contracts.ts`.
 */

export type Decision = 'PAGAR' | 'NO_PAGAR' | 'ESCALAR'

/** States of the generated catalog of lote 1. Kept for `data/*.generated.ts`. */
export type InstanceState =
  | 'RECIBIDA'
  | 'EXTRAIDA'
  | 'VALIDADA'
  | 'CRUZADA'
  | 'DECIDIDA'
  | 'EXPORTADA'
  | 'PENDIENTE_HUMANO'
  | 'REINTENTO'
  | 'OCR'

export type LineItem = {
  description: string
  qty: number
  unitPrice: number
  base: number
}

export type InvoiceDocument = {
  supplierName: string
  supplierActivity?: string
  address: string
  phone?: string
  email?: string
  nif: string
  iban: string
  invoiceNumber: string
  date: string
  clientName: string
  clientNif: string
  pedido: string
  albaran?: string
  paymentMethod?: string
  lines: LineItem[]
  base: number
  ivaRate: number
  ivaAmount: number
  total: number
  conditions?: string
  signature?: string
  page: string
  inputKind: string
  sizeKb: number
}
