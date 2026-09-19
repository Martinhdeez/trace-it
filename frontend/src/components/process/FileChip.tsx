import type { LucideIcon } from 'lucide-react'
import {
  File,
  FileArchive,
  FileCode,
  FileJson,
  FileSpreadsheet,
  FileText,
  FileType,
  X,
} from 'lucide-react'
import { cn } from '../../lib/cn'

export type FilePreview = {
  id: string
  name: string
  type: string
  previewUrl?: string
}

export function FileChip({
  file,
  onRemove,
  tone = 'light',
}: {
  file: FilePreview
  onRemove?: () => void
  tone?: 'light' | 'dark'
}) {
  const dark = tone === 'dark'

  if (isImage(file) && file.previewUrl) {
    return (
      <div className="group relative h-14 w-14 overflow-hidden rounded-[10px] bg-canvas ring-1 ring-line">
        <img src={file.previewUrl} alt="" className="h-full w-full object-cover" />
        {onRemove ? <RemoveButton onRemove={onRemove} inset /> : null}
      </div>
    )
  }

  const kind = fileKind(file.name)
  const Icon = kind.icon

  return (
    <div
      className={cn(
        'group relative flex max-w-[11rem] items-center gap-2 rounded-[10px] py-1.5 pl-1.5 pr-2 ring-1',
        dark ? 'bg-white/8 ring-white/10' : 'bg-canvas ring-line',
      )}
    >
      <span
        className={cn(
          'grid h-8 w-8 shrink-0 place-items-center rounded-[7px] ring-1',
          dark ? 'bg-white/10 text-white/70 ring-white/10' : 'bg-surface text-muted ring-line',
        )}
      >
        <Icon size={14} strokeWidth={1.6} />
      </span>
      <span className="min-w-0">
        <span
          className={cn(
            'block truncate font-mono text-[11px]',
            dark ? 'text-white' : 'text-ink',
          )}
        >
          {shortFileName(file.name)}
        </span>
        <span
          className={cn(
            'block font-mono text-[9px] uppercase tracking-[0.08em]',
            dark ? 'text-white/40' : 'text-faint',
          )}
        >
          {kind.label}
        </span>
      </span>
      {onRemove ? <RemoveButton onRemove={onRemove} /> : null}
    </div>
  )
}

function RemoveButton({ onRemove, inset }: { onRemove: () => void; inset?: boolean }) {
  return (
    <button
      type="button"
      onClick={onRemove}
      className={cn(
        'absolute grid h-4 w-4 place-items-center rounded-full bg-ink text-on-ink opacity-0 transition-opacity group-hover:opacity-100',
        inset ? 'right-1 top-1 bg-ink/80' : '-right-1 -top-1',
      )}
      title="Quitar"
    >
      <X size={9} strokeWidth={2.4} />
    </button>
  )
}

export function isImage(file: { name: string; type?: string }): boolean {
  if (file.type?.startsWith('image/')) return true
  return /\.(png|jpe?g|gif|webp|heic|heif|bmp|svg)$/i.test(file.name)
}

export function shortFileName(name: string, max = 12): string {
  const lastDot = name.lastIndexOf('.')
  const stem = lastDot > 0 ? name.slice(0, lastDot) : name
  const ext = lastDot > 0 ? name.slice(lastDot) : ''
  if (stem.length <= max) return name
  return `${stem.slice(0, max)}…${ext}`
}

export function fileKind(name: string): { label: string; icon: LucideIcon } {
  const ext = name.split('.').pop()?.toLowerCase() ?? ''
  if (ext === 'pdf') return { label: 'PDF', icon: FileText }
  if (['xls', 'xlsx', 'csv', 'ods'].includes(ext)) return { label: ext.toUpperCase(), icon: FileSpreadsheet }
  if (['doc', 'docx', 'odt', 'rtf'].includes(ext)) return { label: ext.toUpperCase(), icon: FileType }
  if (['ppt', 'pptx', 'odp'].includes(ext)) return { label: ext.toUpperCase(), icon: File }
  if (ext === 'json') return { label: 'JSON', icon: FileJson }
  if (['xml', 'html', 'yml', 'yaml'].includes(ext)) return { label: ext.toUpperCase(), icon: FileCode }
  if (['zip', 'rar', '7z', 'gz', 'tgz'].includes(ext)) return { label: ext.toUpperCase(), icon: FileArchive }
  if (['txt', 'md'].includes(ext)) return { label: ext.toUpperCase(), icon: FileText }
  return { label: ext ? ext.toUpperCase() : 'FILE', icon: File }
}

export function toPreview(file: File): FilePreview & { file: File } {
  return {
    id: crypto.randomUUID(),
    name: file.name,
    type: file.type,
    file,
    previewUrl: isImage(file) ? URL.createObjectURL(file) : undefined,
  }
}

export function revokePreview(file: FilePreview) {
  if (file.previewUrl) URL.revokeObjectURL(file.previewUrl)
}
