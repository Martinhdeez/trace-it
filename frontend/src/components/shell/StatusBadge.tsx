import { cn } from '../../lib/cn'
import { tone } from '../../lib/status'

export function StatusBadge({
  value,
  children,
  className,
}: {
  value: string
  children?: string
  className?: string
}) {
  return (
    <span
      className={cn(
        'inline-flex rounded-full px-2 py-0.5 font-mono text-[10px] font-medium tracking-[0.04em]',
        tone(value),
        className,
      )}
    >
      {children ?? value.replaceAll('_', ' ')}
    </span>
  )
}
