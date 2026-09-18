import { Plus, Search } from 'lucide-react'
import type { ReactNode } from 'react'
import { NavLink } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import mark from '../../assets/trace-mark.png'
import { cn } from '../../lib/cn'
import { t } from '../../i18n'
import { paths, PROCESS } from '../../lib/paths'
import { api } from '../../api/client'
import { useAppState } from '../../state/app'

function NavItem({
  to,
  children,
  end,
}: {
  to: string
  children: ReactNode
  end?: boolean
}) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        cn(
          'flex items-center justify-between rounded-[10px] px-2.5 py-[7px] text-[13px] tracking-[-0.01em]',
          isActive
            ? 'bg-white text-ink shadow-[0_1px_2px_rgba(19,19,19,0.06)]'
            : 'text-ink/80 hover:bg-white/60 hover:text-ink',
        )
      }
    >
      {children}
    </NavLink>
  )
}

export function Sidebar({ escalationCount }: { escalationCount: number }) {
  const { setPaletteOpen } = useAppState()
  const processes = useQuery({
    queryKey: ['processes'],
    queryFn: () => api.listProcesses(),
  })

  const items = processes.data ?? [
    { id: PROCESS.reconcilePayments, name: t('processes.reconcile-payments.name') },
    { id: PROCESS.landRegistry, name: t('processes.land-registry.name') },
    { id: PROCESS.vendorOnboarding, name: t('processes.vendor-onboarding.name') },
  ]

  return (
    <aside className="flex w-[232px] shrink-0 flex-col">
      <div className="flex items-center gap-1.5 px-5 pt-5 pb-4">
        <img src={mark} alt="" draggable={false} className="h-6 w-6 rounded-[6px] object-cover select-none" />
        <p className="text-[13px] font-medium tracking-[-0.03em] text-ink">
          trace<span className="text-faint">[.]</span>it
        </p>
      </div>

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

      <nav className="flex min-h-0 flex-1 flex-col px-3">
        <div className="flex items-center justify-between px-2.5 pb-2">
          <p className="text-[11px] font-medium tracking-[0.14em] text-muted uppercase">
            {t('nav.processes')}
          </p>
          <NavLink
            to={paths.processNew}
            title={t('nav.newProcess')}
            className="grid h-6 w-6 place-items-center rounded-full text-ink/70 ring-1 ring-black/[0.06] hover:bg-white hover:text-ink"
          >
            <Plus size={13} strokeWidth={1.75} />
          </NavLink>
        </div>
        <ul className="flex flex-col gap-0.5">
          {items.map((item) => (
            <li key={item.id}>
              <NavItem to={paths.process(item.id)}>{item.name}</NavItem>
            </li>
          ))}
        </ul>

        <p className="mt-7 px-2.5 pb-2 text-[11px] font-medium tracking-[0.14em] text-muted uppercase">
          {t('nav.runs')}
        </p>
        <ul className="flex flex-col gap-0.5">
          <li>
            <NavItem to={paths.review}>
              {t('nav.review')}
              {escalationCount > 0 ? (
                <span className="font-mono text-[11px] text-ink">{escalationCount}</span>
              ) : null}
            </NavItem>
          </li>
          <li>
            <NavItem to={paths.runs}>{t('nav.runs')}</NavItem>
          </li>
        </ul>

        <div className="mt-auto pb-4 pt-6">
          <NavItem to={paths.settings}>{t('nav.settings')}</NavItem>
        </div>
      </nav>
    </aside>
  )
}
