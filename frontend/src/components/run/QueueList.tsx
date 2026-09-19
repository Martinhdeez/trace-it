import { FileText } from 'lucide-react'
import type { DecisionMeta } from '../../lib/status'
import type { InstanceOut } from '../../api/contracts'
import { t } from '../../i18n'
import { cn } from '../../lib/cn'
import { label } from '../../lib/status'
import { StatusBadge } from '../shell/StatusBadge'

export function QueueList({
  items,
  total,
  selectedId,
  onSelect,
  header,
  decisionTypes,
}: {
  items: InstanceOut[]
  total: number
  selectedId?: number
  onSelect: (item: InstanceOut) => void
  header?: React.ReactNode
  decisionTypes?: DecisionMeta[]
}) {
  return (
    <section className="flex max-h-[320px] min-h-0 w-full shrink-0 flex-col px-2 pb-3 lg:h-full lg:max-h-none lg:w-[300px]">
      <div className="flex items-baseline justify-between px-2.5 py-3">
        <h2 className="text-[13px] font-medium tracking-[-0.02em]">Instancias</h2>
        <span className="font-mono text-[11px] text-muted">
          {items.length === total ? total : `${items.length} / ${total}`}
        </span>
      </div>
      {header ? <div className="px-1 pb-2">{header}</div> : null}
      <ul className="min-h-0 flex-1 overflow-y-auto rounded-[16px] bg-surface p-1 ring-1 ring-line">
        {items.length === 0 ? (
          <li className="px-3 py-6 text-center text-[12.5px] text-muted">Nada coincide.</li>
        ) : null}
        {items.map((item) => (
          <li key={item.id}>
            <button
              type="button"
              onClick={() => onSelect(item)}
              className={cn(
                'mb-0.5 flex w-full items-center gap-2.5 rounded-[12px] px-2.5 py-2 text-left',
                item.id === selectedId
                  ? 'bg-canvas'
                  : 'hover:bg-canvas/70',
              )}
            >
              <FileText size={13} strokeWidth={1.5} className="shrink-0 text-faint" />
              <span className="min-w-0 flex-1 truncate font-mono text-[12px]">{item.name}</span>
              <StatusBadge value={label(item)} decisionTypes={decisionTypes} className="shrink-0">
                {item.decision && item.status === 'DECIDED'
                  ? undefined
                  : t(`instanceStatus.${item.status}`)}
              </StatusBadge>
            </button>
          </li>
        ))}
      </ul>
    </section>
  )
}
