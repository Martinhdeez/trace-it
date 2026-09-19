import { t } from '../i18n'

// remove when FieldReading.symbol lands
const FIELD_SYMBOL: Record<string, string> = {
  supplier_tax_id: 'issuer_nif',
  payment_iban: 'iban',
  purchase_order_ref: 'purchase_order',
}

/** The symbol an extraction field feeds. Most fields already share the symbol's name. */
export function symbolOfField(field: string): string {
  return FIELD_SYMBOL[field] ?? field
}

/** "NIF del emisor · issuer_nif", or the bare code when it has no label. */
export function symbolLabel(code: string): string {
  const label = t(`symbols.${code}`)
  return label === `symbols.${code}` ? code : `${label} · ${code}`
}
