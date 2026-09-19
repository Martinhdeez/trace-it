import { Plus, Search } from 'lucide-react'
import type { ReactNode } from 'react'
import { Link, NavLink, useLocation } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import mark from '../../assets/trace-mark.png'
import { api } from '../../api/client'
import { keys } from '../../api/queries'
import { cn } from '../../lib/cn'
import { t } from '../../i18n'
import { paths, processFromPath } from '../../lib/paths'
import { useAppState } from '../../state/app'
import { useSession } from '../../state/session'

function NavItem({
  to,
  children,
  end,
  active,
}: {
  to: string
  children: ReactNode
  end?: boolean
  active?: boolean
}) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        cn(
          'flex items-center justify-between rounded-[10px] py-[7px] pr-2.5 pl-2.5 text-[13px] tracking-[-0.01em]',
          (active ?? isActive)
            ? 'bg-white text-ink shadow-[0_1px_2px_rgba(19,19,19,0.06)]'
            : 'text-ink/80 hover:bg-white/60 hover:text-ink',
        )
      }
    >
      {children}
    </NavLink>
  )
}

export function Sidebar() {
  const { setPaletteOpen } = useAppState()
  const { user } = useSession()
  const location = useLocation()
  const activeId = processFromPath(location.pathname)

  const processes = useQuery({ queryKey: keys.processes, queryFn: () => api.listProcesses() })

  return (
    <aside className="flex w-[232px] shrink-0 flex-col">
      <Link to={paths.landing} className="flex items-center gap-1.5 px-5 pt-5 pb-4">
        <img
          src={mark}
          alt=""
          draggable={false}
          className="h-6 w-6 select-none rounded-[6px] object-cover"
        />
        <p className="text-[13px] font-medium tracking-[-0.03em] text-ink">
          trace<span className="text-faint">[.]</span>it
        </p>
      </Link>

      <div className="px-3 pb-5">
        <button
          type="button"
          onClick={() => setPaletteOpen(true)}
          className="flex w-full items-center gap-2 rounded-full bg-white px-3 py-1.5 text-left text-[13px] text-muted shadow-[0_1px_2px_rgba(19,19,19,0.05)] ring-1 ring-black/[0.06]"
        >
          <Search size={14} strokeWidth={1.5} />
          <span className="flex-1">{t('nav.filter')}</span>
          <kbd className="grid h-5 min-w-5 place-items-center rounded-[6px] bg-canvas font-mono text-[10px] text-faint ring-1 ring-black/[0.06]">
            ⌘K
          </kbd>
        </button>
      </div>

      <nav className="flex min-h-0 flex-1 flex-col overflow-y-auto px-3">
        <div className="flex items-center justify-between px-2.5 pb-2">
          <p className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted">
            {t('nav.processes')}
          </p>
          <NavLink
            to={paths.newProcess}
            title={t('nav.newProcess')}
            className="grid h-6 w-6 place-items-center rounded-full text-ink/70 ring-1 ring-black/[0.06] hover:bg-white hover:text-ink"
          >
            <Plus size={13} strokeWidth={1.75} />
          </NavLink>
        </div>

        <ul className="flex flex-col gap-0.5">
          {(processes.data ?? []).map((item) => {
            const open = item.id === activeId
            return (
              <li key={item.id}>
                <NavItem to={paths.process(item.id)} active={open}>
                  <span className="min-w-0 truncate">{item.nombre}</span>
                </NavItem>
              </li>
            )
          })}
        </ul>

        <div className="mt-auto pb-4 pt-6">
          <NavItem to={paths.settings} end>
            <span className="min-w-0 truncate">{user?.nombre ?? t('nav.signIn')}</span>
            <span className="shrink-0 font-mono text-[10px] text-faint">
              {user?.rol ?? t('nav.anonymous')}
            </span>
          </NavItem>
        </div>
      </nav>
    </aside>
  )
}
