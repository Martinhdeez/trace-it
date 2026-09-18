import type { ButtonHTMLAttributes, ReactNode, SelectHTMLAttributes } from 'react'
import type { InputHTMLAttributes, TextareaHTMLAttributes } from 'react'
import { cn } from '../../lib/cn'

type Tone = 'primary' | 'soft' | 'ghost' | 'danger'

const TONES: Record<Tone, string> = {
  primary: 'bg-ink text-white hover:bg-ink/90 disabled:bg-ink/40',
  soft: 'bg-canvas text-ink ring-1 ring-black/[0.06] hover:bg-well',
  ghost: 'text-muted hover:text-ink',
  danger: 'bg-nopagar-soft text-nopagar ring-1 ring-nopagar/20 hover:bg-nopagar-soft/70',
}

export function Button({
  tone = 'soft',
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { tone?: Tone }) {
  return (
    <button
      type="button"
      {...props}
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-3.5 py-1.5 text-[12px] font-medium',
        'disabled:cursor-not-allowed disabled:opacity-60',
        TONES[tone],
        className,
      )}
    />
  )
}

const FIELD =
  'w-full rounded-[10px] bg-canvas px-3 py-2 text-[13px] text-ink outline-none ring-1 ring-black/[0.06] placeholder:text-faint disabled:opacity-60'

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={cn(FIELD, className)} />
}

export function Textarea({ className, ...props }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea {...props} className={cn(FIELD, 'resize-y leading-6', className)} />
}

export function Select({ className, ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return <select {...props} className={cn(FIELD, 'appearance-none pr-8', className)} />
}

export function Field({
  label,
  hint,
  children,
  className,
}: {
  label: string
  hint?: string
  children: ReactNode
  className?: string
}) {
  return (
    <label className={cn('block', className)}>
      <span className="text-[12px] font-medium text-ink">{label}</span>
      {children}
      {hint ? <span className="mt-1 block text-[11px] text-faint">{hint}</span> : null}
    </label>
  )
}

export function Segmented<T extends string>({
  options,
  value,
  onChange,
}: {
  options: readonly { value: T; label: string; count?: number }[]
  value: T
  onChange: (value: T) => void
}) {
  return (
    <div className="inline-flex items-center gap-0.5 rounded-full bg-canvas p-0.5 ring-1 ring-black/[0.06]">
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          onClick={() => onChange(option.value)}
          className={cn(
            'rounded-full px-3 py-1 text-[12px]',
            option.value === value
              ? 'bg-white text-ink shadow-[0_1px_2px_rgba(19,19,19,0.06)]'
              : 'text-muted hover:text-ink',
          )}
        >
          {option.label}
          {option.count != null ? (
            <span className="ml-1.5 font-mono text-[11px] text-faint">{option.count}</span>
          ) : null}
        </button>
      ))}
    </div>
  )
}
