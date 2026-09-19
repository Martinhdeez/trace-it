import { useEffect, type ReactNode } from 'react'
import { Link } from 'react-router'
import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import { Menu, Search, Settings, X } from 'lucide-react'
import { useAppState } from '../../state/app'
import { paths } from '../../lib/paths'
import { t } from '../../i18n'
import { CommandPalette } from './CommandPalette'
import { Sidebar } from './Sidebar'
import { TraceMark } from './TraceMark'

const drawerEase = [0.32, 0.72, 0, 1] as const

export function AppShell({ children, preview }: { children: ReactNode; preview?: { processId: number } }) {
  const interactive = !preview
  const { setPaletteOpen, navOpen, setNavOpen, sidebarCollapsed, toggleSidebar } = useAppState()
  return (
    <div className={`flex flex-col bg-canvas sm:flex-row ${interactive ? 'h-dvh' : 'h-full'}`}>
      <div className="hidden sm:flex">
        <Sidebar activeProcessId={preview?.processId} collapsed={interactive ? sidebarCollapsed : false} onToggleCollapse={toggleSidebar} />
      </div>
      <header className="flex shrink-0 items-center justify-between gap-3 px-4 py-3 sm:hidden">
        <div className="flex min-w-0 items-center gap-3">
          <button aria-label={t('nav.menu')} onClick={() => setNavOpen(true)}>
            <Menu size={18} strokeWidth={1.75} />
          </button>
          <Link to={paths.processes} className="flex min-w-0 items-center gap-1.5 text-sm font-medium">
            <TraceMark className="h-6 w-6" />
            <span className="truncate">trace<span className="text-faint">[.]</span>it · {t('nav.processes')}</span>
          </Link>
        </div>
        <div className="flex shrink-0 items-center gap-4">
          <button aria-label="Buscar procesos" onClick={() => setPaletteOpen(true)}>
            <Search size={18} />
          </button>
          <Link to="/settings" aria-label="Ajustes de usuario">
            <Settings size={18} />
          </Link>
        </div>
      </header>
      <div className="flex min-h-0 min-w-0 flex-1 flex-col px-2 pb-2 sm:py-3 sm:pl-0 sm:pr-3">
        <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-[20px] bg-shell shadow-shell ring-1 ring-line">
          {children}
        </div>
      </div>
      <AnimatePresence>{interactive && navOpen ? <MobileNav onClose={() => setNavOpen(false)} /> : null}</AnimatePresence>
      {interactive ? <CommandPalette /> : null}
    </div>
  )
}

/** The sidebar as a sheet: slides over the shell, leaves on any tap outside or inside. */
function MobileNav({ onClose }: { onClose: () => void }) {
  const reduceMotion = useReducedMotion()
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div className="fixed inset-0 z-50 sm:hidden">
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: reduceMotion ? 0 : 0.18 }}
        className="absolute inset-0 bg-scrim"
        onClick={onClose}
      />
      <motion.div
        role="dialog"
        aria-modal="true"
        aria-label={t('nav.menu')}
        initial={{ x: '-100%' }}
        animate={{ x: 0 }}
        exit={{ x: '-100%' }}
        transition={{ duration: reduceMotion ? 0 : 0.28, ease: drawerEase }}
        className="absolute inset-y-0 left-0 w-[248px] max-w-[85vw] bg-canvas shadow-pop"
      >
        <Sidebar onNavigate={onClose} />
        <button
          type="button"
          aria-label={t('nav.close')}
          onClick={onClose}
          className="absolute right-3 top-5 grid h-8 w-8 place-items-center rounded-full text-faint hover:bg-surface hover:text-ink"
        >
          <X size={16} strokeWidth={1.75} />
        </button>
      </motion.div>
    </div>
  )
}
