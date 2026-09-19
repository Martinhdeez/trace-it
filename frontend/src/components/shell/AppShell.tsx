import type { ReactNode } from 'react'
import { CommandPalette } from './CommandPalette'
import { Sidebar } from './Sidebar'

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex h-dvh bg-canvas">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col py-3 pr-3">
        <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-[20px] bg-shell shadow-shell ring-1 ring-line">
          {children}
        </div>
      </div>
      <CommandPalette />
    </div>
  )
}
