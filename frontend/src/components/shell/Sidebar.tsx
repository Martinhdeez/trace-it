import { PanelLeftClose, PanelLeftOpen, Plus, Search } from 'lucide-react'
import type { ReactNode } from 'react'
import { Link, NavLink, useLocation } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'motion/react'
import mark from '../../assets/trace-mark-clear.png'
import { api } from '../../api/client'
import { keys } from '../../api/queries'
import { cn } from '../../lib/cn'
import { ErrorNotice } from './Notice'
import { SystemStatus } from './SystemStatus'
import { t } from '../../i18n'
import { paths, processFromPath } from '../../lib/paths'
import { useAppState } from '../../state/app'
import { useSession } from '../../state/session'

function NavItem({
  to,
  children,
  end,
  active,
  onNavigate,
}: {
  to: string
  children: ReactNode
  end?: boolean
  active?: boolean
  onNavigate?: () => void
}) {
  return (
    <NavLink
      to={to}
      end={end}
      onClick={onNavigate}
      className={({ isActive }) =>
        cn(
          'flex items-center justify-between rounded-[10px] py-[7px] pr-2.5 pl-2.5 text-[13px] tracking-[-0.01em]',
          (active ?? isActive)
            ? 'bg-surface text-ink shadow-lift'
            : 'text-ink/80 hover:bg-surface/60 hover:text-ink',
        )
      }
    >
      {children}
    </NavLink>
  )
}

/**
 * The rail and the drawer are the same sidebar in three fits: full (232px),
 * rail (64px, icons and initials) and the mobile sheet. `onNavigate` closes the
 * sheet; the rail ignores it.
 */
export function Sidebar({
  collapsed = false,
  onNavigate,
  onToggleCollapse,
}: {
  collapsed?: boolean
  onNavigate?: () => void
  onToggleCollapse?: () => void
}) {
  const { setPaletteOpen } = useAppState()
  const { user } = useSession()
  const location = useLocation()
  const activeId = processFromPath(location.pathname)

  const processes = useQuery({ queryKey: keys.processes, queryFn: () => api.listProcesses() })

  return (
    <aside
      className={cn(
        'relative flex h-full shrink-0 flex-col transition-[width] duration-[280ms] ease-[cubic-bezier(0.32,0.72,0,1)] motion-reduce:transition-none',
        collapsed ? 'w-16' : 'w-[232px]',
      )}
    >
      <div
        className={cn(
          'flex pt-5 pb-4',
          collapsed ? 'flex-col items-center gap-3' : 'items-center justify-between px-5',
        )}
      >
        <Link to={paths.landing} onClick={onNavigate} className="flex items-center gap-1.5">
          <img
            src={mark}
            alt=""
            draggable={false}
            className="h-6 w-6 shrink-0 select-none object-contain"
          />
          {!collapsed ? (
            <motion.p
              initial={{ opacity: 0, x: -6 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.2, delay: 0.08 }}
              className="whitespace-nowrap text-[13px] font-medium tracking-[-0.03em] text-ink"
            >
              trace<span className="text-faint">[.]</span>it
            </motion.p>
          ) : null}
        </Link>
        {onToggleCollapse ? (
          <button
            type="button"
            onClick={onToggleCollapse}
            aria-label={collapsed ? t('nav.expand') : t('nav.collapse')}
            aria-expanded={!collapsed}
            title={collapsed ? t('nav.expand') : t('nav.collapse')}
            className="grid h-7 w-7 shrink-0 place-items-center rounded-[8px] text-faint hover:bg-surface hover:text-ink"
          >
            <motion.span
              key={collapsed ? 'open' : 'close'}
              initial={{ opacity: 0, scale: 0.6, rotate: -60 }}
              animate={{ opacity: 1, scale: 1, rotate: 0 }}
              transition={{ type: 'spring', duration: 0.35, bounce: 0.3 }}
              className="grid place-items-center"
            >
              {collapsed ? (
                <PanelLeftOpen size={15} strokeWidth={1.75} />
              ) : (
                <PanelLeftClose size={15} strokeWidth={1.75} />
              )}
            </motion.span>
          </button>
        ) : null}
      </div>

      <motion.div
        key={collapsed ? 'search-rail' : 'search-full'}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.18, delay: 0.05 }}
        className={cn('pb-5', collapsed ? 'grid place-items-center' : 'px-3')}
      >
        <button
          type="button"
          title={collapsed ? `${t('nav.filter')} · ⌘K` : undefined}
          onClick={() => {
            onNavigate?.()
            setPaletteOpen(true)
          }}
          className={cn(
            'items-center rounded-full bg-surface text-muted shadow-lift ring-1 ring-line hover:text-ink',
            collapsed
              ? 'grid h-9 w-9 place-items-center'
              : 'flex w-full gap-2 px-3 py-1.5 text-left text-[13px]',
          )}
        >
          <Search size={14} strokeWidth={1.5} />
          {collapsed ? null : (
            <>
              <span className="flex-1">{t('nav.filter')}</span>
              <kbd className="grid h-5 min-w-5 place-items-center rounded-[6px] bg-canvas font-mono text-[10px] text-faint ring-1 ring-line">
                ⌘K
              </kbd>
            </>
          )}
        </button>
      </motion.div>

      <nav className="flex min-h-0 flex-1 flex-col">
        <div
          className={cn(
            'flex items-center pb-2',
            collapsed ? 'justify-center' : 'justify-between px-5.5',
          )}
        >
          {collapsed ? null : (
            <p className="whitespace-nowrap text-[11px] font-medium uppercase tracking-[0.14em] text-muted">
              {t('nav.processes')}
            </p>
          )}
          <NavLink
            to={paths.newProcess}
            onClick={onNavigate}
            title={t('nav.newProcess')}
            className="grid h-6 w-6 shrink-0 place-items-center rounded-full text-ink/70 ring-1 ring-line hover:bg-surface hover:text-ink"
          >
            <Plus size={13} strokeWidth={1.75} />
          </NavLink>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto overflow-x-hidden px-3 py-0.5">
          {processes.isError ? (
            <ErrorNotice error={processes.error} />
          ) : (
            <ul className="flex flex-col gap-0.5">
              {(processes.data ?? []).map((item, index) => {
                const open = item.id === activeId
                return (
                  <motion.li
                    key={`${item.id}-${collapsed ? 'rail' : 'full'}`}
                    initial={{ opacity: 0, x: collapsed ? 0 : -6, scale: collapsed ? 0.85 : 1 }}
                    animate={{ opacity: 1, x: 0, scale: 1 }}
                    transition={{
                      delay: Math.min(index, 8) * 0.025,
                      duration: 0.22,
                      ease: [0.23, 1, 0.32, 1],
                    }}
                  >
                    {collapsed ? (
                      <NavLink
                        to={paths.process(item.id)}
                        title={item.name}
                        className={cn(
                          'mx-auto grid h-9 w-9 place-items-center rounded-[10px] text-[12px] font-medium uppercase',
                          open
                            ? 'bg-surface text-ink shadow-lift'
                            : 'text-ink/70 hover:bg-surface/60 hover:text-ink',
                        )}
                      >
                        {item.name.trim().charAt(0)}
                      </NavLink>
                    ) : (
                      <NavItem to={paths.process(item.id)} active={open} onNavigate={onNavigate}>
                        <span className="min-w-0 truncate">{item.name}</span>
                      </NavItem>
                    )}
                  </motion.li>
                )
              })}
            </ul>
          )}
        </div>
      </nav>

      <motion.div
        key={collapsed ? 'foot-rail' : 'foot-full'}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.18, delay: 0.1 }}
        className={cn('space-y-0.5 pb-4 pt-4', collapsed ? '' : 'px-3')}
      >
        {collapsed ? (
          <NavLink
            to={paths.settings}
            title={user?.name ?? t('nav.signIn')}
            className={({ isActive }) =>
              cn(
                'mx-auto grid h-9 w-9 place-items-center rounded-full text-[12px] font-medium uppercase ring-1',
                isActive
                  ? 'bg-surface text-ink shadow-lift ring-line'
                  : 'bg-surface/60 text-ink/80 ring-line hover:bg-surface hover:text-ink',
              )
            }
          >
            {(user?.name ?? '?').trim().charAt(0)}
          </NavLink>
        ) : (
          <NavItem to={paths.settings} end onNavigate={onNavigate}>
            <span className="min-w-0 truncate">{user?.name ?? t('nav.signIn')}</span>
            <span className="shrink-0 font-mono text-[10px] text-faint">
              {user ? t(`roles.${user.role}`) : t('nav.anonymous')}
            </span>
          </NavItem>
        )}
        <SystemStatus compact={collapsed} />
      </motion.div>
    </aside>
  )
}
