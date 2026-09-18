import type { ReactNode } from 'react'

export function PreviewWell({
  children,
  name,
  action,
}: {
  children: ReactNode
  name: string
  action?: ReactNode
}) {
  return (
    <div className="overflow-hidden rounded-[16px] bg-well ring-1 ring-black/[0.05]">
      <div className="grid min-h-[240px] place-items-center px-8 py-12">{children}</div>
      <div className="flex items-center justify-between px-3.5 py-2">
        <span className="font-mono text-[12px] text-muted">{name}</span>
        {action}
      </div>
    </div>
  )
}

export function NestedCard({
  children,
  label,
  action,
}: {
  children: ReactNode
  label?: string
  action?: ReactNode
}) {
  return (
    <div className="overflow-hidden rounded-[16px] bg-white ring-1 ring-black/[0.06]">
      {label || action ? (
        <div className="flex items-center justify-between px-3.5 py-2">
          <span className="font-mono text-[11px] text-faint">{label}</span>
          {action}
        </div>
      ) : null}
      {children}
    </div>
  )
}

export function PageIntro({
  kicker,
  title,
  description,
}: {
  kicker: string
  title: string
  description?: string
}) {
  return (
    <header className="mb-8">
      <p className="text-[13px] text-muted">{kicker}</p>
      <h1 className="mt-1 text-[32px] font-medium leading-[1.1] tracking-[-0.045em]">{title}</h1>
      {description ? <p className="mt-2 max-w-xl text-[14.5px] leading-6 text-muted">{description}</p> : null}
    </header>
  )
}
