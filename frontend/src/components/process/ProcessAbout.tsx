import { useState } from 'react'
import { Info, X } from 'lucide-react'
import { Overlay } from '../shell/Overlay'

/** Agents open the description with one plain sentence; everything after it is for rules. */
function leadOf(description: string): { lead: string; more: boolean } {
  const full = description.trim()
  const paragraph = full.split(/\n\s*\n/)[0] ?? ''
  // An older description in one block: its first sentence stands in for the lead.
  const lead = paragraph.length > 160 ? (paragraph.match(/^.+?[.!?](?=\s|$)/)?.[0] ?? paragraph) : paragraph
  return { lead, more: lead.length < full.length }
}

/**
 * The process in one sentence, and the rest (sources, conventions) one click away.
 */
export function ProcessAbout({ name, description }: { name: string; description: string }) {
  const [open, setOpen] = useState(false)
  const { lead, more } = leadOf(description)
  if (!lead) return null

  return (
    <div className="mt-2 flex max-w-2xl items-start gap-1.5">
      <p className="line-clamp-2 text-[14.5px] leading-6 text-muted">{lead}</p>
      {more ? (
        <button
          type="button"
          onClick={() => setOpen(true)}
          aria-label="Sobre este proceso"
          title="Sobre este proceso"
          className="mt-[3px] grid h-[18px] w-[18px] shrink-0 place-items-center rounded-full text-faint hover:bg-canvas hover:text-ink"
        >
          <Info size={15} strokeWidth={1.6} />
        </button>
      ) : null}
      {open ? (
        <Overlay onClose={() => setOpen(false)} size="lg">
          <section className="overflow-hidden rounded-[16px] bg-surface shadow-pop ring-1 ring-line">
            <header className="flex items-start justify-between gap-4 border-b border-hairline px-5 py-4">
              <div>
                <p className="font-mono text-[10px] tracking-[0.12em] text-faint">SOBRE EL PROCESO</p>
                <h2 className="mt-1 text-[16px] font-medium tracking-[-0.02em]">{name}</h2>
              </div>
              <button
                type="button"
                onClick={() => setOpen(false)}
                aria-label="Cerrar"
                className="grid h-7 w-7 place-items-center rounded-full text-muted hover:bg-canvas hover:text-ink"
              >
                <X size={14} strokeWidth={1.75} />
              </button>
            </header>
            <div className="max-h-[70vh] space-y-4 overflow-y-auto px-5 py-4">
              {description
                .trim()
                .split(/\n\s*\n/)
                .map((block, index) => (
                  <Block key={index} text={block} first={index === 0} />
                ))}
            </div>
          </section>
        </Overlay>
      ) : null}
    </div>
  )
}

/** A paragraph, or a heading line followed by numbered items "(1) …". */
function Block({ text, first }: { text: string; first: boolean }) {
  const lines = text.split('\n').map((line) => line.trim()).filter(Boolean)
  const items = lines.filter((line) => /^\(\d+\)\s/.test(line))
  if (items.length > 1) {
    const heading = lines.filter((line) => !items.includes(line))
    return (
      <div>
        {heading.map((line) => (
          <p key={line} className="mb-2 text-[12px] font-medium text-ink">
            {line}
          </p>
        ))}
        <ol className="space-y-2">
          {items.map((item) => {
            const [, number, body] = item.match(/^\((\d+)\)\s(.*)$/) ?? []
            return (
              <li key={item} className="flex gap-2.5 text-[12.5px] leading-5 text-muted">
                <span className="mt-px grid h-[18px] w-[18px] shrink-0 place-items-center rounded-full bg-canvas font-mono text-[10px] text-ink ring-1 ring-line">
                  {number}
                </span>
                <span>{body}</span>
              </li>
            )
          })}
        </ol>
      </div>
    )
  }
  return (
    <p className={first ? 'text-[14px] leading-6 text-ink' : 'text-[12.5px] leading-5 text-muted'}>
      {text}
    </p>
  )
}
