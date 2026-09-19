import type { ReactNode } from 'react'
import { mode } from '../../api/client'
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
      {mode === 'mock' ? (
        <span className="pointer-events-none fixed top-4 left-1/2 z-50 -translate-x-1/2 rounded-full bg-escalar-soft px-3 py-1 font-mono text-[11px] font-medium text-escalar ring-1 ring-escalar/30">
          MOCK DATA
        </span>
      ) : null}
    </div>
  )
}
