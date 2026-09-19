import type { Plane, UsageGroup, UsageTotals } from '../../api/contracts'
import { getLocale, t } from '../../i18n'
import { humanize } from '../../lib/format'

export type Measure = 'cost' | 'tokens' | 'time'
export const measures: Measure[] = ['cost', 'tokens', 'time']
export const planes: Plane[] = ['ingestion', 'agents', 'execution']
export const colors: Record<Plane, string> = {
  ingestion: 'var(--color-ocr)',
  agents: 'var(--color-escalar)',
  execution: 'var(--color-pagar)',
}
export const label = (key: string) => t(`metrics.${key}`)
export const number = (value: number) => value.toLocaleString(getLocale())
export function duration(value: number | null): string {
  if (value === null) return '—'
  const [amount, unit] =
    value >= 3_600_000
      ? [value / 3_600_000, 'h']
      : value >= 60_000
        ? [value / 60_000, 'min']
        : value >= 1000
          ? [value / 1000, 's']
          : [value, 'ms']
  return `${amount.toLocaleString(getLocale(), { maximumFractionDigits: 2 })} ${unit}`
}
export function money(value: number): string {
  return new Intl.NumberFormat(getLocale(), {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: Math.abs(value) >= 1 ? 2 : 6,
  }).format(value)
}
export function value(row: UsageTotals, measure: Measure) {
  return measure === 'cost'
    ? row.known_cost_usd
    : measure === 'tokens'
      ? row.input_tokens + row.output_tokens
      : row.self_ms
}
export function formatted(row: UsageTotals, measure: Measure) {
  if (measure === 'cost') {
    if (!row.known_cost_usd && row.unpriced_requests) return label('unknownOnly')
    return `${money(row.known_cost_usd)}${row.unpriced_requests ? ` (${label('partial')})` : ''}`
  }
  if (measure === 'time') return row.timed_spans ? duration(row.self_ms) : '—'
  return number(value(row, measure))
}
export function moduleName(key: string) {
  const name = key.replace(/^(agent|provider):/, '')
  const translated = t(`metrics.modules.${name}`)
  return translated.startsWith('metrics.modules.') ? humanize(name) : translated
}
export function groupName(row: UsageGroup, level: 'plane' | 'module' | 'model') {
  return level === 'plane'
    ? t(`planes.${row.plane}`)
    : level === 'module'
      ? moduleName(row.module ?? row.key)
      : [row.model, row.provider].filter(Boolean).join(' / ') || label('local')
}
export function dateTime(iso: string) {
  return new Date(iso).toLocaleString(getLocale(), {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}
