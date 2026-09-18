import { useNavigate } from 'react-router'
import type { Run } from '../../api/types'
import { formatEuro, formatRunDate } from '../../lib/format'
import { cn } from '../../lib/cn'
import { t } from '../../i18n'
import { PreviewWell } from './Well'

export function RunPreview({
  processId,
  run,
}: {
  processId: string
  run: Run
}) {
  const navigate = useNavigate()
  const cells = [
    { label: 'PAGAR', value: run.counts.pagar, tone: 'text-pagar' },
    { label: 'ESCALAR', value: run.counts.escalar, tone: 'text-escalar' },
    { label: 'NO PAGAR', value: run.counts.noPagar, tone: 'text-nopagar' },
    { label: 'OCR', value: run.counts.pending, tone: 'text-ocr' },
  ]

  return (
    <PreviewWell
      name={run.id}
      action={
        <button
          type="button"
          onClick={() => navigate(`/processes/${processId}/runs/${run.id}`)}
          className="rounded-full bg-white px-2.5 py-1 text-[12px] text-muted ring-1 ring-black/[0.06] hover:text-ink"
        >
          {t('process.openRun')}
        </button>
      }
    >
      <div className="text-center">
        <p className="text-[13px] text-muted">
          {run.label}
          <span className="text-faint"> · </span>
          {run.status === 'en_curso' ? 'en curso' : 'hecho'}
          <span className="text-faint"> · </span>
          {run.fileCount} archivos
        </p>
        <div className="mt-6 flex items-end justify-center gap-2">
          {cells.map((cell, index) => (
            <div key={cell.label} className={cn('flex flex-col items-center', index === 3 && 'ml-4')}>
              <div
                className={cn(
                  'grid h-14 min-w-12 place-items-center rounded-[10px] border-2 bg-white px-2 font-mono text-[18px] tabular-nums tracking-tight',
                  cell.value > 0 ? 'border-stone-300 text-ink' : 'border-stone-200 text-faint shadow-[inset_0_1px_2px_rgba(28,25,23,0.07)]',
                )}
              >
                {cell.value}
              </div>
              <span className={cn('mt-2 text-[11px] tracking-[-0.01em]', cell.tone)}>{cell.label}</span>
            </div>
          ))}
        </div>
      </div>
    </PreviewWell>
  )
}

export function RecentCards({
  processId,
  runs,
}: {
  processId: string
  runs: Run[]
}) {
  const navigate = useNavigate()

  return (
    <div>
      {runs.map((run) => {
        const total =
          run.counts.pagar + run.counts.noPagar + run.counts.escalar + run.counts.pending || 1
        return (
          <button
            key={run.id}
            type="button"
            onClick={() => navigate(`/processes/${processId}/runs/${run.id}`)}
            className="flex w-full items-center gap-4 px-3.5 py-3 text-left hover:bg-canvas"
          >
            <span className="w-24 text-[13px] font-medium">{run.label}</span>
            <span className="w-20 font-mono text-[11px] text-muted">
              {run.status === 'en_curso' ? 'en curso' : 'hecho'}
            </span>
            <span className="flex h-1 flex-1 overflow-hidden rounded-full bg-hairline">
              <span className="h-full bg-pagar" style={{ width: `${(run.counts.pagar / total) * 100}%` }} />
              <span className="h-full bg-nopagar" style={{ width: `${(run.counts.noPagar / total) * 100}%` }} />
              <span className="h-full bg-escalar" style={{ width: `${(run.counts.escalar / total) * 100}%` }} />
            </span>
            <span className="w-28 text-right text-[12px] text-muted">{formatRunDate(run.startedAt)}</span>
            <span className="w-16 text-right font-mono text-[12px]">{formatEuro(run.costPerFile, 3)}</span>
          </button>
        )
      })}
    </div>
  )
}
