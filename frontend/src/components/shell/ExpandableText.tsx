import { useState } from 'react'
import { ChevronDown } from 'lucide-react'
import { cn } from '../../lib/cn'

/**
 * Long text read as its first paragraph, two lines at most; the rest is one click away.
 * Agents write a plain lead sentence first, so the lead is what a manager needs.
 */
export function ExpandableText({ text, className }: { text: string; className?: string }) {
  const [open, setOpen] = useState(false)
  const full = text.trim()
  if (!full) return null
  const lead = full.split(/\n\s*\n/)[0]
  const more = lead !== full || lead.length > 160

  return (
    <div className={className}>
      <p className={cn('whitespace-pre-line', !open && 'line-clamp-2')}>{open ? full : lead}</p>
      {more ? (
        <button
          type="button"
          aria-expanded={open}
          onClick={() => setOpen((next) => !next)}
          className="mt-1 inline-flex items-center gap-1 text-[12.5px] text-faint hover:text-ink"
        >
          {open ? 'Ver menos' : 'Leer más'}
          <ChevronDown
            size={12}
            strokeWidth={1.75}
            className={cn('transition-transform', open && 'rotate-180')}
          />
        </button>
      ) : null}
    </div>
  )
}
