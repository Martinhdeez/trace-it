import type { ReactNode } from 'react'
import { Link } from 'react-router'
import { Search, Settings } from 'lucide-react'
import { useAppState } from '../../state/app'
import { paths } from '../../lib/paths'
import { CommandPalette } from './CommandPalette'
import { Sidebar } from './Sidebar'

export function AppShell({ children }: { children: ReactNode }) {
  const { setPaletteOpen } = useAppState()
  return (
    <div className="flex h-dvh flex-col bg-canvas sm:flex-row">
      <div className="hidden sm:flex"><Sidebar /></div>
      <header className="flex shrink-0 items-center justify-between px-4 py-3 sm:hidden">
        <Link to={paths.processes} className="text-sm font-medium">trace[.]it · Procesos</Link>
        <div className="flex items-center gap-4">
          <button aria-label="Buscar procesos" onClick={() => setPaletteOpen(true)}><Search size={18} /></button>
          <Link to="/settings" aria-label="Ajustes de usuario"><Settings size={18} /></Link>
        </div>
      </header>
      <div className="flex min-h-0 min-w-0 flex-1 flex-col px-2 pb-2 sm:py-3 sm:pl-0 sm:pr-3">
        <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-[20px] bg-shell shadow-shell ring-1 ring-line">
          {children}
        </div>
      </div>
      <CommandPalette />
    </div>
  )
}
