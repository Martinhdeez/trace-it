import type { ReactNode } from 'react'
import { Link, useLocation } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import { api } from '../../api/client'
import { keys } from '../../api/queries'
import { ArrowLeft } from 'lucide-react'
import { cn } from '../../lib/cn'
import { paths } from '../../lib/paths'
import { PROCESS_TABS, processTabFromPath, type ProcessTabId } from '../../lib/processTabs'
import { CountChip } from '../shell/Controls'
import { ErrorNotice } from '../shell/Notice'
import { Topbar, type Crumb } from '../shell/Topbar'

export function ProcessScreen({
  processId,
  crumbs,
  actions,
  activeTab,
  children,
}: {
  processId: number
  crumbs: Crumb[]
  actions?: ReactNode
  activeTab?: ProcessTabId
  children: ReactNode
}) {
  return (
    <>
      <Topbar crumbs={crumbs} actions={actions} />
      <ProcessTabs processId={processId} activeTab={activeTab} />
      {children}
    </>
  )
}

export function ProcessTabs({ processId, activeTab }: { processId: number; activeTab?: ProcessTabId }) {
  const location = useLocation()
  const current = activeTab ?? processTabFromPath(location.pathname, processId)

  const process = useQuery({
    queryKey: keys.process(processId),
    queryFn: () => api.getProcess(processId),
  })
  const summary = useQuery({
    queryKey: keys.summary(processId),
    queryFn: () => api.summary(processId),
  })
  const waiting = summary.data?.queue ?? 0
  const error = process.error ?? summary.error

  return (
    <nav className="flex shrink-0 gap-1 overflow-x-auto border-b border-hairline px-4 sm:px-6">
      {error ? (
        <ErrorNotice error={error} />
      ) : (
        <>
          <Link
            to={paths.process(processId)}
            className="-mb-px mr-2 inline-flex shrink-0 items-center gap-1 border-b-2 border-transparent py-2.5 pr-3 text-[13px] text-muted hover:text-ink"
          >
            <ArrowLeft size={13} strokeWidth={1.6} />
            Bandeja
          </Link>
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
        </>
      )}
    </nav>
  )
}
