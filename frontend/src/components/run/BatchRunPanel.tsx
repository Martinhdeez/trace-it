import { useEffect, useRef, useState, type DragEvent } from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import { Check, Circle, FileText, LoaderCircle, Play, Upload, X } from 'lucide-react'
import { FileChip, type FilePreview } from '../process/FileChip'
import { cn } from '../../lib/cn'

const stages = ['Lectura', 'Símbolos', 'Reglas', 'Decisión'] as const
const ease = [0.23, 1, 0.32, 1] as const

export function BatchRunPanel({
  queue,
  running,
  uploading,
  finished,
  rulesCount,
  startBlocked,
  error,
  onFiles,
  onRemove,
  onStart,
  onClose,
}: {
  queue: FilePreview[]
  running: boolean
  uploading: boolean
  finished: boolean
  rulesCount: number
  startBlocked?: string
  error?: unknown
  onFiles: (files: File[]) => void
  onRemove: (id: string) => void
  onStart: () => void
  onClose: () => void
}) {
  const collect = !running && !uploading && !finished

  return (
    <section className="overflow-hidden rounded-[16px] bg-white shadow-[0_16px_50px_rgba(19,19,19,0.12)] ring-1 ring-black/[0.06]">
      <header className="flex items-start justify-between gap-4 border-b border-hairline px-5 py-4">
        <div>
          <div className="flex items-center gap-2">
            {uploading || running ? (
              <LoaderCircle size={15} strokeWidth={1.8} className="animate-spin text-ink" />
            ) : finished ? (
              <Check size={15} strokeWidth={2} className="text-pagar" />
            ) : (
              <Play size={15} strokeWidth={2} className="text-muted" />
            )}
            <h2 className="text-[14px] font-medium">
              {uploading
                ? 'En cola…'
                : running
                  ? 'Procesando lote'
                  : finished
                    ? 'Lote completado'
                    : 'Nueva ejecución'}
            </h2>
          </div>
          <p className="mt-1 text-[12px] text-muted">
            {collect
              ? 'Suelta los documentos que quieres decidir. Entran a la cola de este proceso.'
              : `${queue.length} documento${queue.length === 1 ? '' : 's'}${
                  rulesCount ? `, ${rulesCount} reglas activas` : ''
                }`}
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          disabled={running || uploading}
          aria-label="Cerrar"
          className="grid h-7 w-7 place-items-center rounded-full text-muted hover:bg-canvas hover:text-ink disabled:opacity-30"
        >
          <X size={14} strokeWidth={1.75} />
        </button>
      </header>

      {collect ? (
        <Collect
          queue={queue}
          startBlocked={startBlocked}
          error={error}
          onFiles={onFiles}
          onRemove={onRemove}
          onStart={onStart}
        />
      ) : (
        <Progress queue={queue} running={running || uploading} finished={finished} />
      )}
    </section>
  )
}

function Collect({
  queue,
  startBlocked,
  error,
  onFiles,
  onRemove,
  onStart,
}: {
  queue: FilePreview[]
  startBlocked?: string
  error?: unknown
  onFiles: (files: File[]) => void
  onRemove: (id: string) => void
  onStart: () => void
}) {
  const input = useRef<HTMLInputElement>(null)
  const [over, setOver] = useState(false)
  const blocked = Boolean(startBlocked) || queue.length === 0

  const drop = (event: DragEvent<HTMLElement>) => {
    event.preventDefault()
    setOver(false)
    const files = [...event.dataTransfer.files]
    if (files.length) onFiles(files)
  }

  return (
    <div className="px-5 py-4">
      <button
        type="button"
        onClick={() => input.current?.click()}
        onDragOver={(event) => {
          event.preventDefault()
          setOver(true)
        }}
        onDragLeave={() => setOver(false)}
        onDrop={drop}
        className={cn(
          'flex min-h-[140px] w-full flex-col items-center justify-center gap-2 rounded-[12px] px-4 py-8 text-center ring-1 ring-dashed transition-colors',
          over ? 'bg-white ring-ink/30' : 'bg-canvas ring-black/[0.08] hover:bg-white',
        )}
      >
        <Upload size={18} strokeWidth={1.5} className="text-faint" />
        <span className="text-[13px] text-ink">Arrastra aquí el lote</span>
        <span className="text-[11px] text-faint">
          PDF, imágenes, Excel. Clic para elegir.
        </span>
      </button>
      <input
        ref={input}
        type="file"
        multiple
        hidden
        accept="application/pdf,image/*,.xlsx,.xls,.csv"
        onChange={(event) => {
          const files = [...(event.target.files ?? [])]
          if (files.length) onFiles(files)
          event.target.value = ''
        }}
      />

      {queue.length ? (
        <ul className="mt-3 flex flex-wrap gap-2">
          {queue.map((file) => (
            <li key={file.id}>
              <FileChip file={file} onRemove={() => onRemove(file.id)} />
            </li>
          ))}
        </ul>
      ) : null}

      {error ? (
        <p className="mt-3 text-[12px] text-nopagar">
          {error instanceof Error ? error.message : 'No se pudo encolar el lote.'}
        </p>
      ) : null}

      <div className="mt-4 flex items-center justify-between gap-3">
        <p className="text-[11px] text-faint">
          {startBlocked
            ? startBlocked
            : queue.length
              ? `${queue.length} en cola`
              : 'Hace falta al menos un documento'}
        </p>
        <button
          type="button"
          disabled={blocked}
          onClick={onStart}
          className="inline-flex items-center gap-1.5 rounded-full bg-ink px-3.5 py-1.5 text-[12px] font-medium text-white hover:bg-ink/90 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <Play size={12} strokeWidth={2} />
          {queue.length ? `Ejecutar ${queue.length}` : 'Ejecutar'}
        </button>
      </div>
    </div>
  )
}

function Progress({
  queue,
  running,
  finished,
}: {
  queue: FilePreview[]
  running: boolean
  finished: boolean
}) {
  const reduceMotion = useReducedMotion()
  const [tick, setTick] = useState(0)

  useEffect(() => {
    if (!running) return
    const timer = window.setInterval(() => setTick((value) => value + 1), 190)
    return () => window.clearInterval(timer)
  }, [running])

  const activeIndex = finished
    ? queue.length
    : Math.min(Math.max(queue.length - 1, 0), Math.floor(tick / stages.length))
  const activeStage = finished ? stages.length : tick % stages.length
  const completed = finished ? queue.length : Math.max(0, activeIndex)
  const progress = queue.length === 0 ? 100 : Math.round((completed / queue.length) * 100)
  const start = Math.max(0, activeIndex - 2)
  const visible = queue.slice(start, start + 7)

  return (
    <div className="grid min-h-[284px] lg:grid-cols-[minmax(0,1fr)_250px]">
      <div className="min-w-0 px-5 py-4">
        <div className="mb-4 flex items-center justify-between font-mono text-[10px] text-faint">
          <span>PROGRESO</span>
          <span>{progress}%</span>
        </div>
        <div className="mb-5 h-px overflow-hidden bg-black/[0.06]">
          <motion.div
            className="h-full origin-left bg-pagar"
            initial={false}
            animate={{ transform: `scaleX(${progress / 100})` }}
            transition={reduceMotion ? { duration: 0 } : { duration: 0.3, ease }}
          />
        </div>

        <div className="space-y-1">
          <AnimatePresence mode="popLayout" initial={false}>
            {visible.map((item, visibleIndex) => {
              const index = start + visibleIndex
              const done = finished || index < activeIndex
              const active = !finished && index === activeIndex
              return (
                <motion.div
                  layout
                  key={item.id}
                  initial={reduceMotion ? false : { opacity: 0 }}
                  animate={{ opacity: done || active ? 1 : 0.38 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.16 }}
                  className={cn(
                    'flex min-w-0 items-center gap-3 rounded-[10px] px-3 py-2',
                    active && 'bg-canvas',
                  )}
                >
                  {done ? (
                    <Check size={13} strokeWidth={2} className="shrink-0 text-pagar" />
                  ) : active ? (
                    <LoaderCircle
                      size={13}
                      strokeWidth={1.8}
                      className={cn('shrink-0 text-ink', !reduceMotion && 'animate-spin')}
                    />
                  ) : (
                    <Circle size={11} strokeWidth={1.5} className="shrink-0 text-faint" />
                  )}
                  <FileText size={13} strokeWidth={1.5} className="shrink-0 text-faint" />
                  <span className="min-w-0 flex-1 truncate font-mono text-[11px]">
                    {item.name}
                  </span>
                  <span className="shrink-0 font-mono text-[10px] text-faint">
                    {done ? 'terminado' : active ? stages[activeStage] : 'en espera'}
                  </span>
                </motion.div>
              )
            })}
          </AnimatePresence>
        </div>
      </div>

      <aside className="border-t border-hairline bg-canvas px-5 py-4 lg:border-l lg:border-t-0">
        <p className="mb-4 font-mono text-[10px] text-faint">DOCUMENTO ACTUAL</p>
        <ol className="space-y-3">
          {stages.map((stage, index) => {
            const done = finished || activeIndex >= queue.length || index < activeStage
            const active = running && index === activeStage
            return (
              <li key={stage} className="flex items-center gap-3">
                <span
                  className={cn(
                    'grid h-5 w-5 place-items-center rounded-full ring-1',
                    done
                      ? 'bg-pagar text-white ring-pagar'
                      : active
                        ? 'text-ink ring-ink/40'
                        : 'text-faint ring-black/[0.08]',
                  )}
                >
                  {done ? (
                    <Check size={11} strokeWidth={2.5} />
                  ) : active ? (
                    <LoaderCircle
                      size={11}
                      strokeWidth={1.8}
                      className={cn(!reduceMotion && 'animate-spin')}
                    />
                  ) : (
                    <span className="font-mono text-[9px]">{index + 1}</span>
                  )}
                </span>
                <span className={cn('text-[12px]', active ? 'text-ink' : 'text-muted')}>
                  {stage}
                </span>
              </li>
            )
          })}
        </ol>
      </aside>
    </div>
  )
}
