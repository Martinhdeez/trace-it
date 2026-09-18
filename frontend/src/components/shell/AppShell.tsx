import type { ReactNode } from 'react'
import { CommandPalette } from './CommandPalette'
import { Sidebar } from './Sidebar'

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex h-dvh bg-canvas">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col py-3 pr-3">
        <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-[20px] bg-shell shadow-[0_1px_2px_rgba(19,19,19,0.04),0_8px_24px_rgba(19,19,19,0.04)] ring-1 ring-black/[0.06]">
          {children}
        </div>
      </div>
      <CommandPalette />
    </div>
  )
}
