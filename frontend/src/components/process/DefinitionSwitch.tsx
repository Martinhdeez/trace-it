import { Link, useLocation } from 'react-router'
import { cn } from '../../lib/cn'
import { DEFINITION_TABS, definitionTabFromPath } from '../../lib/definitionTabs'

export function DefinitionSwitch({ processId }: { processId: number }) {
  const location = useLocation()
  const current = definitionTabFromPath(location.pathname)

  return (
    <nav className="flex min-w-0 flex-wrap gap-0.5 rounded-full bg-canvas p-0.5 ring-1 ring-black/[0.06]">
      {DEFINITION_TABS.map((tab) => {
        const active = current === tab.id
        return (
          <Link
            key={tab.id}
            to={tab.path(processId)}
            aria-current={active ? 'page' : undefined}
            className={cn(
              'rounded-full px-3 py-1 text-[12px]',
              active ? 'bg-white text-ink shadow-[0_1px_2px_rgba(19,19,19,0.06)]' : 'text-muted hover:text-ink',
            )}
          >
            {tab.label}
          </Link>
        )
      })}
    </nav>
  )
}
