import { FileText } from 'lucide-react'
import type { QueueItem } from '../../api/types'
import { cn } from '../../lib/cn'
import { formatMs } from '../../lib/format'
import { decisionFromState } from '../../lib/status'
import { StatusBadge } from '../shell/StatusBadge'

export function QueueList({
  items,
  selectedId,
  onSelect,
  fileCount,
}: {
  items: QueueItem[]
  selectedId?: string
  onSelect: (item: QueueItem) => void
  fileCount: number
}) {
  return (
    <section className="flex h-full min-h-0 w-[280px] shrink-0 flex-col px-2 pb-3">
      <div className="flex items-baseline justify-between px-2.5 py-3">
        <h2 className="text-[13px] font-medium tracking-[-0.02em]">Cola</h2>
        <span className="font-mono text-[11px] text-muted">{fileCount}</span>
      </div>
      <ul className="min-h-0 flex-1 overflow-y-auto rounded-[16px] bg-well p-1 ring-1 ring-black/[0.04]">
        {items.map((item) => {
          const kind = decisionFromState(item.result, item.state)
          const selected = item.id === selectedId
          return (
            <li key={item.id}>
              <button
                type="button"
                onClick={() => onSelect(item)}
                className={cn(
                  'mb-0.5 flex w-full items-start gap-2.5 rounded-[12px] px-2.5 py-2 text-left',
                  selected
                    ? 'bg-white shadow-[0_1px_2px_rgba(19,19,19,0.06)]'
                    : 'hover:bg-white/70',
                )}
              >
                <span className="min-w-0 flex-1">
                  <span className="flex items-center gap-2">
                    <FileText size={13} strokeWidth={1.5} className="shrink-0 text-faint" />
                    <span className="truncate font-mono text-[12px]">{item.fileId}</span>
                  </span>
                  <span className="mt-0.5 flex items-center gap-2 pl-5">
                    <StatusBadge kind={kind} />
                    <span className="truncate text-[12px] text-muted">{item.reason}</span>
                  </span>
                </span>
                <span className="shrink-0 font-mono text-[10px] text-faint">
                  {formatMs(item.latencyMs)}
                </span>
              </button>
            </li>
          )
        })}
      </ul>
    </section>
  )
}
