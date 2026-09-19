import { type ReactNode } from 'react'
import { Link } from 'react-router'
import { motion, useReducedMotion } from 'motion/react'
import hackspain from '../../assets/hackspain.png'
import maisa from '../../assets/maisa.png'
import mark from '../../assets/trace-mark.png'
import { cn } from '../../lib/cn'
import { paths } from '../../lib/paths'

const ease = [0.23, 1, 0.32, 1] as const

export function Wordmark({ className }: { className?: string }) {
  return (
    <span className={cn('font-medium tracking-[-0.03em]', className)}>
      trace<span className="text-faint">[.]</span>it
    </span>
  )
}

/** Every band on the page hangs off this measure, so the rules line up. */
export function Sheet({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={cn('mx-auto w-full max-w-[1120px] px-6 md:px-10', className)}>{children}</div>
  )
}

export function Kicker({ children, className }: { children: ReactNode; className?: string }) {
  return <p className={cn('u-kicker', className)}>{children}</p>
}

export function Band({
  children,
  id,
  tone = 'canvas',
  className,
}: {
  children: ReactNode
  id?: string
  tone?: 'canvas' | 'sheet'
  className?: string
}) {
  return (
    <section
      id={id}
      className={cn('border-t border-hairline', tone === 'sheet' && 'bg-shell', className)}
    >
      {children}
    </section>
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
        'inline-flex items-center gap-2 rounded-full bg-ink px-5 py-2.5 text-[14px] font-medium text-white hover:bg-ink/90',
        className,
      )}
    >
      {children}
    </Link>
  )
}

export function SecondaryAction({
  href,
  to,
  children,
  className,
}: {
  href?: string
  to?: string
  children: ReactNode
  className?: string
}) {
  const classes = cn(
    'inline-flex items-center gap-2 rounded-full bg-white px-5 py-2.5 text-[14px] text-ink ring-1 ring-black/[0.07] hover:bg-well',
    className,
  )

  if (to) {
    return (
      <Link to={to} className={classes}>
        {children}
      </Link>
    )
  }

  return (
    <a href={href} className={classes}>
      {children}
    </a>
  )
}

/**
 * Scroll motion that only moves things. Opacity stays at 1, so a section is
 * readable even if the viewport observer never fires during the demo.
 */
export function Rise({
  children,
  delay = 0,
  className,
}: {
  children: ReactNode
  delay?: number
  className?: string
}) {
  const reduce = useReducedMotion()

  if (reduce) return <div className={className}>{children}</div>

  return (
    <motion.div
      className={className}
      initial={{ y: 14 }}
      whileInView={{ y: 0 }} // unslop-ignore: moves only, never hides content
      viewport={{ once: true, margin: '-8% 0px' }}
      transition={{ duration: 0.6, delay, ease }}
    >
      {children}
    </motion.div>
  )
}

export function SectionHead({
  kicker,
  title,
  lead,
}: {
  kicker: string
  title: ReactNode
  lead?: ReactNode
}) {
  return (
    <header className="grid gap-x-10 gap-y-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,24rem)] lg:items-end">
      <div>
        <Kicker>{kicker}</Kicker>
        <h2 className="u-display mt-4 max-w-[24ch] text-[clamp(28px,3.4vw,40px)]">{title}</h2>
      </div>
      {lead ? <p className="max-w-[46ch] text-[15px] leading-7 text-muted lg:pb-1">{lead}</p> : null}
    </header>
  )
}

const NAV = [
  { href: '#como-funciona', label: 'Cómo funciona' },
  { href: '#bandeja', label: 'Bandeja' },
  { href: '#versiones', label: 'Versiones' },
]

export function Masthead() {
  return (
    <header className="sticky top-0 z-40 border-b border-hairline bg-canvas/85 backdrop-blur-md">
      <Sheet>
        <div className="flex h-14 items-center justify-between gap-6">
          <Link to={paths.landing} className="flex items-center gap-2">
            <img src={mark} alt="" className="h-6 w-6 rounded-[6px] object-cover" draggable={false} />
            <Wordmark className="text-[14px]" />
          </Link>

          <nav className="hidden items-center gap-1 text-[13px] md:flex">
            {NAV.map((item) => (
              <a
                key={item.href}
                href={item.href}
                className="rounded-full px-3 py-1.5 text-muted hover:text-ink"
              >
                {item.label}
              </a>
            ))}
          </nav>

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
      <Sheet className="py-10">
        <div className="flex flex-wrap items-end justify-between gap-8">
          <div>
            <Wordmark className="text-[15px]" />
          </div>

          <div>
            <Kicker className="mb-3">Hecho en</Kicker>
            <div className="flex items-center gap-5">
              <img
                src={hackspain}
                alt="HackSpain"
                className="h-10 w-auto object-contain"
                draggable={false}
              />
              <span className="text-[13px] text-faint">×</span>
              <img
                src={maisa}
                alt="Maisa"
                className="h-[26px] w-auto object-contain"
                draggable={false}
              />
            </div>
          </div>
        </div>

        <p className="mt-8 border-t border-hairline pt-5 text-[11.5px] text-faint">
          HackSpain 26 · reto 500 Sombras de Alberto
        </p>
      </Sheet>
    </footer>
  )
}
