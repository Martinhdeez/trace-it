import { type ReactNode } from 'react'
import { Link } from 'react-router'
import hackspain from '../../assets/hackspain.svg'
import maisa from '../../assets/maisa.svg'
import { TraceMark } from '../shell/TraceMark'
import { cn } from '../../lib/cn'
import { paths } from '../../lib/paths'

export function Wordmark({ className }: { className?: string }) {
  return (
    <span className={cn('font-medium tracking-[-0.03em]', className)}>
      trace<span className="text-faint">[.]</span>it
    </span>
  )
}

export function Sheet({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={cn('mx-auto w-full max-w-[1120px] px-6 md:px-10', className)}>{children}</div>
  )
}

export function PrimaryAction({
  to,
  children,
  className,
}: {
  to: string
  children: ReactNode
  className?: string
}) {
  return (
    <Link
      to={to}
      className={cn(
        'inline-flex items-center gap-2 rounded-full bg-ink px-5 py-2.5 text-[14px] font-medium text-on-ink hover:bg-ink/90',
        className,
      )}
    >
      {children}
    </Link>
  )
}

export function Masthead() {
  return (
    <header className="sticky top-0 z-40 border-b border-hairline bg-canvas/85 backdrop-blur-md">
      <Sheet>
        <div className="flex h-14 items-center justify-between gap-6">
          <Link to={paths.landing} className="flex items-center gap-2">
            <TraceMark className="h-7 w-7" />
            <Wordmark className="text-[14px]" />
          </Link>
          <PrimaryAction to={paths.processes} className="px-3.5 py-1.5 text-[13px]">
            Abrir la consola
          </PrimaryAction>
        </div>
      </Sheet>
    </header>
  )
}

export function Colophon() {
  return (
    <footer className="border-t border-hairline">
      <Sheet className="flex flex-wrap items-center justify-between gap-x-6 gap-y-3 py-6">
        <Link to={paths.landing} className="flex items-center gap-2">
          <TraceMark className="h-7 w-7" />
          <Wordmark className="text-[15px]" />
        </Link>
        <div className="flex items-center gap-2.5 text-[11px] text-muted sm:gap-3">
          <img src={hackspain} alt="HackSpain" width={928} height={306} className="h-7 w-auto" />
          <span aria-hidden className="text-faint">
            ×
          </span>
          <img src={maisa} alt="Maisa" width={842} height={247} className="h-6 w-auto [html[data-theme=dark]_&]:invert" />
        </div>
      </Sheet>
    </footer>
  )
}
