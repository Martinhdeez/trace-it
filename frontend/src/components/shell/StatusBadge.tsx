import { cn } from '../../lib/cn'
import { tone, type DecisionMeta } from '../../lib/status'

export function StatusBadge({
  value,
  children,
  className,
  decisionTypes,
}: {
  value: string
  children?: string
  className?: string
  /** The process's decision types, so the tone follows their metadata. */
  decisionTypes?: DecisionMeta[]
}) {
  return (
    <span
      className={cn(
        'inline-flex rounded-full px-2 py-0.5 font-mono text-[10px] font-medium tracking-[0.04em]',
        tone(value, decisionTypes),
        className,
      )}
    >
      {children ?? value.replaceAll('_', ' ')}
    </span>
  )
}
