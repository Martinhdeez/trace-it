import type { BadgeKind } from '../../lib/status'
import { cn } from '../../lib/cn'

const styles: Record<BadgeKind, string> = {
  PAGAR: 'bg-pagar-soft text-pagar',
  NO_PAGAR: 'bg-nopagar-soft text-nopagar',
  ESCALAR: 'bg-escalar-soft text-escalar',
  OCR: 'bg-ocr-soft text-ocr',
  EN_CURSO: 'bg-pagar-soft text-pagar',
  COMPLETADO: 'bg-ocr-soft text-muted',
}

export function StatusBadge({
  kind,
  children,
}: {
  kind: BadgeKind
  children?: string
}) {
  return (
    <span
      className={cn(
        'inline-flex rounded-full px-2 py-0.5 font-mono text-[10px] font-medium tracking-[0.04em]',
        styles[kind],
      )}
    >
      {children ?? kind.replaceAll('_', ' ')}
    </span>
  )
}
