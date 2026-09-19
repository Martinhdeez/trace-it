import { useEffect, useId, useRef, useState, type KeyboardEvent } from 'react'
import { Check, ChevronDown } from 'lucide-react'
import type { Locale } from '../../i18n'
import { cn } from '../../lib/cn'

const LANGUAGES: readonly { value: Locale; name: string; code: string }[] = [
  { value: 'es', name: 'Español', code: 'ES' },
  { value: 'en', name: 'English', code: 'EN' },
]

function SpainFlag() {
  return (
    <svg viewBox="0 0 3 2" preserveAspectRatio="xMidYMid slice" className="h-full w-full">
      <rect width="3" height="2" fill="#AA151B" />
      <rect y="0.5" width="3" height="1" fill="#F1BF00" />
    </svg>
  )
}

function UkFlag() {
  // Clip ids must be unique on the page: two selects may render at once.
  const id = useId()
  return (
    <svg viewBox="0 0 60 30" preserveAspectRatio="xMidYMid slice" className="h-full w-full">
      <clipPath id={`${id}t`}>
        <path d="M30,15 h30 v15 z v15 h-30 z h-30 v-15 z v-15 h30 z" />
      </clipPath>
      <rect width="60" height="30" fill="#012169" />
      <path d="M0,0 L60,30 M60,0 L0,30" stroke="#fff" strokeWidth="6" />
      <path
        d="M0,0 L60,30 M60,0 L0,30"
        clipPath={`url(#${id}t)`}
        stroke="#C8102E"
        strokeWidth="4"
      />
      <path d="M30,0 v30 M0,15 h60" stroke="#fff" strokeWidth="10" />
      <path d="M30,0 v30 M0,15 h60" stroke="#C8102E" strokeWidth="6" />
    </svg>
  )
}

function Flag({ locale }: { locale: Locale }) {
  return (
    <span className="block h-[14px] w-[20px] shrink-0 overflow-hidden rounded-[3px] ring-1 ring-line">
      {locale === 'es' ? <SpainFlag /> : <UkFlag />}
    </span>
  )
}

/** A listbox with flags: click or keyboard, closes on Escape or outside click. */
export function LanguageSelect({
  value,
  onChange,
}: {
  value: Locale
  onChange: (value: Locale) => void
}) {
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(0)
  const root = useRef<HTMLDivElement>(null)
  const trigger = useRef<HTMLButtonElement>(null)
  const listId = useId()
  const current = LANGUAGES.find((item) => item.value === value) ?? LANGUAGES[0]

  useEffect(() => {
    if (!open) return
    const onDown = (event: PointerEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false)
    }
    document.addEventListener('pointerdown', onDown)
    return () => document.removeEventListener('pointerdown', onDown)
  }, [open])

  const show = () => {
    setActive(LANGUAGES.findIndex((item) => item.value === value))
    setOpen(true)
  }

  const pick = (next: Locale) => {
    setOpen(false)
    trigger.current?.focus()
    if (next !== value) onChange(next)
  }

  const onKeyDown = (event: KeyboardEvent) => {
    if (!open) {
      if (['ArrowDown', 'ArrowUp', 'Enter', ' '].includes(event.key)) {
        event.preventDefault()
        show()
      }
      return
    }
    if (event.key === 'Escape') {
      event.preventDefault()
      setOpen(false)
    } else if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault()
      const step = event.key === 'ArrowDown' ? 1 : -1
      setActive((index) => (index + step + LANGUAGES.length) % LANGUAGES.length)
    } else if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      pick(LANGUAGES[active].value)
    } else if (event.key === 'Tab') {
      setOpen(false)
    }
  }

  return (
    <div ref={root} className="relative w-[220px]" onKeyDown={onKeyDown}>
      <button
        ref={trigger}
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={listId}
        onClick={() => (open ? setOpen(false) : show())}
        className={cn(
          'flex w-full items-center gap-2.5 rounded-[10px] bg-canvas px-3 py-2 text-left text-[13px] text-ink ring-1 ring-line outline-none',
          'hover:bg-well focus-visible:ring-focus',
          open && 'bg-well',
        )}
      >
        <Flag locale={current.value} />
        <span className="flex-1">{current.name}</span>
        <ChevronDown
          size={14}
          strokeWidth={1.75}
          className={cn(
            'text-muted transition-transform duration-200 motion-reduce:transition-none',
            open && 'rotate-180',
          )}
        />
      </button>

      <ul
        id={listId}
        role="listbox"
        aria-activedescendant={open ? `${listId}-${active}` : undefined}
        className={cn(
          'absolute top-full left-0 z-30 mt-1.5 w-full origin-top rounded-[12px] bg-surface p-1 shadow-float ring-1 ring-line',
          'transition-[opacity,transform,visibility] duration-150 motion-reduce:transition-none',
          open ? 'visible scale-100 opacity-100' : 'invisible scale-[0.97] opacity-0',
        )}
      >
        {LANGUAGES.map((item, index) => {
          const selected = item.value === value
          return (
            <li
              key={item.value}
              id={`${listId}-${index}`}
              role="option"
              aria-selected={selected}
              onPointerEnter={() => setActive(index)}
              onClick={() => pick(item.value)}
              className={cn(
                'flex cursor-pointer items-center gap-2.5 rounded-[8px] px-2.5 py-2 text-[13px]',
                index === active ? 'bg-well text-ink' : 'text-ink/85',
              )}
            >
              <Flag locale={item.value} />
              <span className="flex-1">{item.name}</span>
              <span className="font-mono text-[10px] text-faint">{item.code}</span>
              <Check
                size={13}
                strokeWidth={2}
                className={cn('text-ink', selected ? 'opacity-100' : 'opacity-0')}
              />
            </li>
          )
        })}
      </ul>
    </div>
  )
}
