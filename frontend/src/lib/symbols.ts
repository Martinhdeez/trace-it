import { t } from '../i18n'

/** "NIF del emisor · issuer_nif", or the bare code when it has no label. */
export function symbolLabel(code: string): string {
  const label = t(`symbols.${code}`)
  return label === `symbols.${code}` ? code : `${label} · ${code}`
}
