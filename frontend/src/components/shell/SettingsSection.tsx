import type { ReactNode } from 'react'

/** One row of a settings page: what it is on the left, the control on the right. */
export function SettingsSection({
  title,
  description,
  children,
}: {
  title: string
  description: string
  children: ReactNode
}) {
  return (
    <section className="grid gap-4 py-6 md:grid-cols-[220px_1fr] md:gap-8">
      <div>
        <h2 className="text-[14px] font-medium tracking-[-0.02em] text-ink">{title}</h2>
        <p className="mt-1 text-[12.5px] leading-5 text-muted">{description}</p>
      </div>
      <div className="min-w-0">{children}</div>
    </section>
  )
}
