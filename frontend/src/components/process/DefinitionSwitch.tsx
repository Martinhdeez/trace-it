import { Link, useLocation } from 'react-router'
import { cn } from '../../lib/cn'
import { DEFINITION_TABS, definitionTabFromPath } from '../../lib/definitionTabs'
import { SEGMENT_ITEM, SegmentedRail } from '../shell/Controls'

export function DefinitionSwitch({ processId }: { processId: number }) {
  const location = useLocation()
  const current = definitionTabFromPath(location.pathname)

  return (
    <nav aria-label="Definición">
      <SegmentedRail value={current}>
        {DEFINITION_TABS.map((tab) => {
          const active = current === tab.id
          return (
            <Link
              key={tab.id}
              to={tab.path(processId)}
              aria-current={active ? 'page' : undefined}
              data-active={active || undefined}
              className={cn(SEGMENT_ITEM, active ? 'text-ink' : 'text-muted hover:text-ink')}
            >
              {tab.label}
            </Link>
          )
        })}
      </SegmentedRail>
    </nav>
  )
}
