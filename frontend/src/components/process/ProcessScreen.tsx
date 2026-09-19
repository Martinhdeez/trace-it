import type { ReactNode } from 'react'
import { Link, useLocation } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import { api } from '../../api/client'
import { keys } from '../../api/queries'
import { cn } from '../../lib/cn'
import { PROCESS_TABS, processTabFromPath } from '../../lib/processTabs'
import { countsOf, waitingOnPerson } from '../../lib/process'
import { CountChip } from '../shell/Controls'
import { Topbar, type Crumb } from '../shell/Topbar'

export function ProcessScreen({
  processId,
  crumbs,
  actions,
  children,
}: {
  processId: number
  crumbs: Crumb[]
  actions?: ReactNode
  children: ReactNode
}) {
  return (
    <>
      <Topbar crumbs={crumbs} actions={actions} />
      <ProcessTabs processId={processId} />
      {children}
    </>
  )
}

export function ProcessTabs({ processId }: { processId: number }) {
  const location = useLocation()
  const current = processTabFromPath(location.pathname, processId)

  const process = useQuery({
    queryKey: keys.process(processId),
    queryFn: () => api.getProcess(processId),
  })
  const counts = useQuery({
    queryKey: keys.instances(processId),
    queryFn: () => api.listInstances(processId),
    select: countsOf,
  })
  const waiting = waitingOnPerson(process.data, counts.data)

  return (
    <nav className="flex shrink-0 gap-1 overflow-x-auto border-b border-hairline px-8">
      {PROCESS_TABS.map((tab) => {
        const active = current === tab.id
        const count = tab.id === 'review' ? waiting : undefined
        return (
          <Link
            key={tab.id}
            to={tab.path(processId)}
            aria-current={active ? 'page' : undefined}
            className={cn(
              'relative -mb-px inline-flex shrink-0 items-center gap-1.5 border-b-2 px-3 py-2.5 text-[13px] tracking-[-0.01em]',
              active
                ? 'border-ink text-ink'
                : 'border-transparent text-muted hover:text-ink',
            )}
          >
            {tab.label}
            {count ? <CountChip>{count}</CountChip> : null}
          </Link>
        )
      })}
    </nav>
  )
}
