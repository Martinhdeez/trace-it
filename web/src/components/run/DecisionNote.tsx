import { useState } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import { ChevronDown } from 'lucide-react'
import type { InstanceDetail } from '../../api/types'
import { formatMs } from '../../lib/format'
import { cn } from '../../lib/cn'
import { decisionFromState } from '../../lib/status'
import { JsonHighlight } from '../../lib/jsonHighlight'
import { t } from '../../i18n'

const ease = [0.23, 1, 0.32, 1] as const

export function DecisionNote({
  instance,
  jsonl,
}: {
  instance: InstanceDetail | undefined
  jsonl: string
}) {
  const [copied, setCopied] = useState(false)
  const [open, setOpen] = useState(false)

  if (!instance) {
    return (
      <aside className="flex w-[300px] shrink-0 flex-col px-5 py-4 text-[13px] text-muted">
        {t('run.decision')}
      </aside>
    )
  }

  const kind = decisionFromState(instance.result, instance.state)
  let parsed: unknown = jsonl
  try {
    parsed = JSON.parse(jsonl)
  } catch {
    parsed = jsonl
  }

  const copy = async () => {
    await navigator.clipboard.writeText(jsonl)
    setCopied(true)
    window.setTimeout(() => setCopied(false), 1200)
  }

  const download = () => {
    const blob = new Blob([jsonl + '\n'], { type: 'application/jsonl' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'outcomes.jsonl'
    link.click()
    URL.revokeObjectURL(url)
  }

  return (
    <aside className="flex w-[300px] shrink-0 flex-col px-2 pb-3">
      <div className="px-3 py-3">
        <h2 className="text-[13px] font-medium">{t('run.decision')}</h2>
      </div>

      <div className="rounded-[16px] bg-well px-4 py-4 ring-1 ring-black/[0.04]">
        <p className="text-[13px] text-muted">{instance.reason}</p>
        <div className="mt-3 flex items-baseline justify-between">
          <p
            className={cn(
              'text-[28px] font-medium tracking-[-0.045em] leading-none',
              kind === 'PAGAR' && 'text-pagar',
              kind === 'ESCALAR' && 'text-escalar',
              kind === 'NO_PAGAR' && 'text-nopagar',
              kind === 'OCR' && 'text-ocr',
            )}
          >
            {kind === 'OCR' ? 'OCR' : kind.replaceAll('_', ' ')}
          </p>
          {instance.confidence != null ? (
            <p className="font-mono text-[13px] text-muted">{instance.confidence}%</p>
          ) : null}
        </div>
      </div>

      <div className="mt-2 overflow-hidden rounded-[16px] ring-1 ring-black/[0.06]">
        <button
          type="button"
          onClick={() => setOpen((value) => !value)}
          className="flex w-full items-center justify-between px-3 py-2 text-left"
        >
          <span className="font-mono text-[11px] text-faint">{t('run.jsonl')}</span>
          <span className="flex items-center gap-2 text-[11px] text-muted">
            {open ? t('run.collapse') : t('run.expand')}
            <motion.span animate={{ rotate: open ? 180 : 0 }} transition={{ duration: 0.18, ease }}>
              <ChevronDown size={14} strokeWidth={1.5} />
            </motion.span>
          </span>
        </button>
        <AnimatePresence initial={false}>
          {open ? (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.22, ease }}
              className="overflow-hidden"
            >
              <div className="flex justify-end gap-2 px-3 pb-2">
                <button type="button" onClick={download} className="text-[11px] text-muted hover:text-ink">
                  {t('run.download')}
                </button>
                <button type="button" onClick={() => void copy()} className="text-[11px] text-muted hover:text-ink">
                  {copied ? t('run.copied') : t('run.copy')}
                </button>
              </div>
              <JsonHighlight value={parsed} />
            </motion.div>
          ) : null}
        </AnimatePresence>
      </div>

      <ul className="min-h-0 flex-1 overflow-y-auto px-3">
        {instance.ruleHits.map((hit) => (
          <li key={hit.id} className="flex gap-3 border-t border-hairline py-2.5 first:border-0">
            <span className={cn('mt-1 h-1.5 w-1.5 shrink-0 rounded-full', hit.ok ? 'bg-pagar' : 'bg-escalar')} />
            <span className="min-w-0 flex-1">
              <span className="block text-[13px]">{hit.title}</span>
              <span className="block text-[12px] text-muted">{hit.detail}</span>
            </span>
            <span className="shrink-0 font-mono text-[10px] text-faint">{formatMs(hit.latencyMs)}</span>
          </li>
        ))}
      </ul>
    </aside>
  )
}
