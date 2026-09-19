import type { ReactNode } from 'react'
import { Link } from 'react-router'

export type Crumb = { label: string; to?: string }

export function Topbar({
  crumbs,
  actions,
}: {
  crumbs: Crumb[]
  actions?: ReactNode
}) {
  return (
    // Actions sit as far from the top edge as from the right one: the page gutter.
    <header className="flex min-h-[54px] shrink-0 items-center justify-between gap-4 px-4 pt-4 sm:px-6 sm:pt-6">
      <nav className="flex min-w-0 items-center gap-2 text-[13px] text-muted">
        {crumbs.map((crumb, index) => (
          <span key={`${crumb.label}-${index}`} className="flex min-w-0 items-center gap-2">
            {index > 0 ? <span className="text-faint">·</span> : null}
            {crumb.to && index !== crumbs.length - 1 ? (
              <Link to={crumb.to} className="truncate hover:text-ink">
                {crumb.label}
              </Link>
            ) : (
              <span className={index === crumbs.length - 1 ? 'truncate text-ink' : 'truncate'}>
                {crumb.label}
              </span>
            )}
          </span>
        ))}
      </nav>
      {actions ? <div className="flex shrink-0 items-center gap-2">{actions}</div> : null}
    </header>
  )
}
