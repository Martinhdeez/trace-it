import { useRef, useState, type DragEvent } from 'react'
import { Upload } from 'lucide-react'
import { cn } from '../../lib/cn'

export function DropZone({
  label,
  hint,
  accept,
  multiple,
  disabled,
  onFiles,
}: {
  label: string
  hint: string
  accept?: string
  multiple?: boolean
  disabled?: boolean
  onFiles: (files: File[]) => void
}) {
  const input = useRef<HTMLInputElement>(null)
  const [over, setOver] = useState(false)

  const drop = (event: DragEvent<HTMLButtonElement>) => {
    event.preventDefault()
    setOver(false)
    if (disabled) return
    const files = [...event.dataTransfer.files]
    if (files.length > 0) onFiles(multiple ? files : files.slice(0, 1))
  }

  return (
    <>
      <button
        type="button"
        disabled={disabled}
        onClick={() => input.current?.click()}
        onDragOver={(event) => {
          event.preventDefault()
          setOver(true)
        }}
        onDragLeave={() => setOver(false)}
        onDrop={drop}
        className={cn(
          'flex w-full items-center gap-3 rounded-[12px] px-3 py-3 text-left ring-1 transition-colors',
          over ? 'bg-white ring-focus' : 'bg-well ring-black/[0.04] hover:bg-white/70',
          disabled && 'cursor-not-allowed opacity-60',
        )}
      >
        <Upload size={15} strokeWidth={1.5} className="shrink-0 text-faint" />
        <span className="min-w-0">
          <span className="block text-[13px] text-ink">{label}</span>
          <span className="block truncate text-[11px] text-muted">{hint}</span>
        </span>
      </button>
      <input
        ref={input}
        type="file"
        accept={accept}
        multiple={multiple}
        hidden
        onChange={(event) => {
          const files = [...(event.target.files ?? [])]
          if (files.length > 0) onFiles(files)
          event.target.value = ''
        }}
      />
    </>
  )
}
