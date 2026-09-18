import { useQuery } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { api } from '../../api/client'
import { CommandPalette } from './CommandPalette'
import { Sidebar } from './Sidebar'
import { VersionPanel } from './VersionPanel'

export function AppShell({ children }: { children: ReactNode }) {
  const escalations = useQuery({
    queryKey: ['escalations'],
    queryFn: () => api.listEscalations(),
  })

  return (
    <div className="flex h-full bg-canvas">
      <Sidebar escalationCount={escalations.data?.length ?? 0} />
      <div className="flex min-w-0 flex-1 flex-col py-3 pr-3">
        <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-[20px] bg-shell shadow-[0_1px_2px_rgba(19,19,19,0.04),0_8px_24px_rgba(19,19,19,0.04)] ring-1 ring-black/[0.06]">
          {children}
        </div>
      </div>
      <CommandPalette />
      <VersionPanel />
    </div>
  )
}
