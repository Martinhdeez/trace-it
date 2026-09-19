import { useEffect, useRef, useState, type DragEvent } from 'react'
import { Link } from 'react-router'
import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import { ArrowRight, Check, Circle, LoaderCircle, Play, Upload, X } from 'lucide-react'
import type { ProcessDetail, RunSummary, UploadProgress } from '../../api/contracts'
import { FileChip, type FilePreview } from '../process/FileChip'
import { ErrorNotice, Notice } from '../shell/Notice'
import { TerminalLoader } from '../shell/TerminalLoader'
import { cn } from '../../lib/cn'
import { paths } from '../../lib/paths'
import { decisionTone, type DecisionTone } from '../../lib/process'

const ease = [0.23, 1, 0.32, 1] as const

/** More files than this and the queue shows a count instead of every chip. */
const CHIPS = 24

export function BatchRunPanel({
  processId,
  process,
  runId,
  queue,
  running,
  uploading,
  finished,
  rulesCount,
  startBlocked,
  error,
  progress,
  result,
  onFiles,
  onRemove,
  onClear,
  onStart,
  onClose,
}: {
  processId: number
  process: ProcessDetail | undefined
  /** The run this batch produced, once it is in the history. */
  runId: number | undefined
  queue: FilePreview[]
  running: boolean
  uploading: boolean
  finished: boolean
  rulesCount: number
  startBlocked?: string
  error?: unknown
  /** Files uploaded so far, reported by the client after each one. */
  progress: UploadProgress[]
  result: RunSummary | undefined
  onFiles: (files: File[]) => void
  onRemove: (id: string) => void
  onClear: () => void
  onStart: () => void
  onClose: () => void
}) {
  const collect = !running && !uploading && !finished

  return (
    <section className="overflow-hidden rounded-[16px] bg-surface shadow-pop ring-1 ring-line">
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
          onClear={onClear}
          onStart={onStart}
        />
      ) : finished && result ? (
        <Outcome processId={processId} process={process} runId={runId} result={result} />
      ) : (
        <Progress
          queue={queue}
          uploading={uploading}
          running={running}
          rulesCount={rulesCount}
          events={progress}
        />
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
  onClear,
  onStart,
}: {
  queue: FilePreview[]
  startBlocked?: string
  error?: unknown
  onFiles: (files: File[]) => void
  onRemove: (id: string) => void
  onClear: () => void
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
          'flex w-full flex-col items-center justify-center gap-2 rounded-[12px] px-4 py-8 text-center ring-1 ring-dashed transition-colors',
          queue.length ? 'min-h-[88px]' : 'min-h-[140px]',
          over ? 'bg-surface ring-ink/30' : 'bg-canvas ring-line hover:bg-surface',
        )}
      >
        <Upload size={18} strokeWidth={1.5} className="text-faint" />
        <span className="text-[13px] text-ink">
          {queue.length ? 'Añadir más documentos' : 'Arrastra aquí el lote'}
        </span>
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
        <div className="mt-3 rounded-[12px] ring-1 ring-line">
          <div className="flex items-center justify-between gap-3 px-3 py-2">
            <span className="text-[12.5px] text-ink">
              {queue.length} documento{queue.length === 1 ? '' : 's'} en cola
            </span>
            <button
              type="button"
              onClick={onClear}
              className="text-[12px] text-muted hover:text-ink"
            >
              Quitar todos
            </button>
          </div>
          <ul className="flex max-h-[168px] flex-wrap gap-2 overflow-y-auto border-t border-hairline p-3">
            {queue.slice(0, CHIPS).map((file) => (
              <li key={file.id}>
                <FileChip file={file} onRemove={() => onRemove(file.id)} />
              </li>
            ))}
            {queue.length > CHIPS ? (
              <li className="self-center px-1 text-[12px] text-muted">
                y {queue.length - CHIPS} más
              </li>
            ) : null}
          </ul>
        </div>
      ) : null}

      {error ? (
        <div className="mt-3">
          <ErrorNotice error={error} />
        </div>
      ) : null}

      <div className="mt-4 flex items-center justify-between gap-3">
        <p className="text-[11px] text-faint">
          {startBlocked
            ? startBlocked
            : queue.length
              ? 'Se leen y se deciden con la versión publicada'
              : 'Hace falta al menos un documento'}
        </p>
        <button
          type="button"
          disabled={blocked}
          onClick={onStart}
          className="inline-flex items-center gap-1.5 rounded-full bg-ink px-3.5 py-1.5 text-[12px] font-medium text-on-ink hover:bg-ink/90 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <Play size={12} strokeWidth={2} />
          {queue.length ? `Ejecutar ${queue.length.toLocaleString('es-ES')}` : 'Ejecutar'}
        </button>
      </div>
    </div>
  )
}

/** Output lines kept on screen; a 500-file batch writes a thousand. */
const LOG_LINES = 200

type FileState =
  | { phase: 'queued' }
  | { phase: 'reading' }
  | { phase: 'read'; read?: number; expected?: number }

/**
 * A batch on its way: every file with its state on the left, the output as it arrives
 * on the right. Reading reports per file; deciding is one call, so it shows as one step.
 */
function Progress({
  queue,
  uploading,
  running,
  rulesCount,
  events,
}: {
  queue: FilePreview[]
  uploading: boolean
  running: boolean
  rulesCount: number
  events: UploadProgress[]
}) {
  const reduceMotion = useReducedMotion()
  const log = useRef<HTMLOListElement>(null)
  const files = useRef<HTMLUListElement>(null)

  const states = new Map<number, FileState>()
  for (const event of events) {
    states.set(
      event.index,
      event.phase === 'read'
        ? { phase: 'read', read: event.read, expected: event.expected }
        : { phase: 'reading' },
    )
  }
  const done = events.filter((event) => event.phase === 'read').length
  const percent = queue.length ? Math.round((done / queue.length) * 100) : 100

  // Big batches: keep the file being read in view, and the newest output line.
  useEffect(() => {
    log.current?.scrollTo({ top: log.current.scrollHeight })
    const list = files.current
    const row = list?.querySelector<HTMLElement>('[data-reading]')
    if (list && row && (row.offsetTop < list.scrollTop || row.offsetTop > list.scrollTop + list.clientHeight - row.offsetHeight)) {
      list.scrollTop = row.offsetTop - list.clientHeight / 2
    }
  }, [events.length, running])
  const shown = events.slice(-LOG_LINES)

  return (
    <div className="grid lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
      <div className="min-w-0 px-5 py-4">
        <div className="mb-3 flex items-center justify-between font-mono text-[10px] text-faint">
          <span>{running ? 'DECIDIENDO' : `LEÍDOS ${done} DE ${queue.length}`}</span>
          <span>{running ? `${rulesCount} reglas` : `${percent}%`}</span>
        </div>
        <div className="relative mb-4 h-[3px] overflow-hidden rounded-full bg-rule">
          <motion.div
            className="absolute inset-y-0 left-0 w-full origin-left rounded-full bg-pagar"
            initial={false}
            animate={{ transform: `scaleX(${running ? 1 : percent / 100})` }}
            transition={reduceMotion ? { duration: 0 } : { duration: 0.35, ease }}
          />
          {running && !reduceMotion ? (
            <motion.div
              className="absolute inset-y-0 w-1/3 bg-gradient-to-r from-transparent via-white/70 to-transparent"
              initial={{ left: '-33%' }}
              animate={{ left: '100%' }}
              transition={{ duration: 1.1, ease: 'easeInOut', repeat: Infinity }}
            />
          ) : null}
        </div>

        <ul ref={files} className="relative max-h-[300px] space-y-0.5 overflow-y-auto">
          {queue.map((item, index) => {
            const state = states.get(index) ?? { phase: 'queued' as const }
            return (
              <li
                key={item.id}
                data-reading={state.phase === 'reading' ? '' : undefined}
                className={cn(
                  'flex min-w-0 items-center gap-2.5 rounded-[10px] px-2.5 py-1.5 transition-colors',
                  state.phase === 'reading' && 'bg-canvas',
                )}
              >
                <FileStatus state={state} deciding={running} reduceMotion={Boolean(reduceMotion)} />
                <span
                  className={cn(
                    'min-w-0 flex-1 truncate font-mono text-[11px] transition-opacity',
                    state.phase === 'queued' && !running && 'opacity-40',
                  )}
                >
                  {item.name}
                </span>
                <span className="shrink-0 font-mono text-[10px] text-faint">
                  {running
                    ? 'decidiendo'
                    : state.phase === 'read'
                      ? state.expected
                        ? `${state.read}/${state.expected} datos`
                        : 'leído'
                      : state.phase === 'reading'
                        ? 'leyendo'
                        : 'en cola'}
                </span>
              </li>
            )
          })}
        </ul>
      </div>

      <aside className="flex min-h-[280px] flex-col border-t border-hairline bg-canvas lg:border-l lg:border-t-0">
        <p className="px-5 pb-2 pt-4 font-mono text-[10px] text-faint">SALIDA</p>
        <ol
          ref={log}
          className="max-h-[300px] min-h-0 flex-1 space-y-1 overflow-y-auto px-5 pb-4 font-mono text-[11px] leading-5"
        >
          <AnimatePresence initial={false}>
            {shown.map((event, index) => (
              <motion.li
                key={events.length - shown.length + index}
                initial={reduceMotion ? false : { opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.18, ease }}
                className="flex min-w-0 gap-2"
              >
                <span className={event.phase === 'read' ? 'text-pagar' : 'text-faint'}>
                  {event.phase === 'read' ? '✓' : '›'}
                </span>
                <span className="min-w-0 flex-1 truncate text-ink">{event.name}</span>
                <span className="shrink-0 text-faint">
                  {event.phase === 'read'
                    ? event.expected
                      ? `${event.read}/${event.expected} datos`
                      : 'leído'
                    : 'leyendo'}
                </span>
              </motion.li>
            ))}
          </AnimatePresence>
          {running ? (
            <li className="pt-1">
              <TerminalLoader
                verbs={[
                  `aplicando ${rulesCount} reglas`,
                  'cruzando con las fuentes',
                  'decidiendo cada documento',
                ]}
              />
            </li>
          ) : uploading && events.length === 0 ? (
            <li>
              <TerminalLoader verbs={['subiendo el lote']} />
            </li>
          ) : null}
        </ol>
      </aside>
    </div>
  )
}

function FileStatus({
  state,
  deciding,
  reduceMotion,
}: {
  state: FileState
  deciding: boolean
  reduceMotion: boolean
}) {
  if (deciding) {
    return (
      <span className="grid h-[13px] w-[13px] shrink-0 place-items-center">
        <span className={cn('h-1.5 w-1.5 rounded-full bg-ink/60', !reduceMotion && 'animate-pulse')} />
      </span>
    )
  }
  if (state.phase === 'read') {
    return (
      <motion.span
        initial={reduceMotion ? false : { scale: 0.4, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ type: 'spring', stiffness: 500, damping: 28 }}
        className="shrink-0"
      >
        <Check size={13} strokeWidth={2} className="text-pagar" />
      </motion.span>
    )
  }
  if (state.phase === 'reading') {
    return (
      <LoaderCircle
        size={13}
        strokeWidth={1.8}
        className={cn('shrink-0 text-ink', !reduceMotion && 'animate-spin')}
      />
    )
  }
  return <Circle size={11} strokeWidth={1.5} className="mx-px shrink-0 text-faint" />
}

const TONE_BAR: Record<DecisionTone, string> = {
  positive: 'bg-pagar',
  negative: 'bg-nopagar',
  attention: 'bg-escalar',
}

/** What the batch decided: one bar, one line per outcome, and the way to its documents. */
function Outcome({
  processId,
  process,
  runId,
  result,
}: {
  processId: number
  process: ProcessDetail | undefined
  runId: number | undefined
  result: RunSummary
}) {
  const outcomes = Object.entries(result.by_decision)
    .filter(([, value]) => value > 0)
    .sort(([, a], [, b]) => b - a)
    .map(([name, value]) => ({ name, value, tone: decisionTone(process, name) }))
  const total = outcomes.reduce((sum, item) => sum + item.value, 0)
  const down = Object.entries(result.down_sources ?? {})
  const share = (value: number) => (total ? Math.round((value / total) * 100) : 0)

  return (
    <div className="px-5 py-5">
      <p className="text-[28px] font-medium leading-none tracking-[-0.04em] tabular-nums">
        {result.decided.toLocaleString('es-ES')}
        <span className="ml-2 text-[13px] font-normal tracking-normal text-muted">
          documento{result.decided === 1 ? '' : 's'} decidido{result.decided === 1 ? '' : 's'}
        </span>
      </p>

      {total ? (
        <>
          <div className="mt-5 flex h-2 overflow-hidden rounded-full bg-rule">
            {outcomes.map((item) => (
              <span
                key={item.name}
                title={`${item.name.replaceAll('_', ' ')}: ${item.value}`}
                className={TONE_BAR[item.tone]}
                style={{ width: `${(item.value / total) * 100}%` }}
              />
            ))}
          </div>
          <ul className="mt-4 divide-y divide-hairline">
            {outcomes.map((item) => (
              <li key={item.name} className="flex items-center gap-3 py-2">
                <span className={cn('h-2.5 w-2.5 shrink-0 rounded-[3px]', TONE_BAR[item.tone])} />
                <span className="min-w-0 flex-1 text-[13px] text-ink">
                  {item.name.replaceAll('_', ' ')}
                </span>
                <span className="font-mono text-[12px] text-faint">{share(item.value)}%</span>
                <span className="w-14 text-right font-mono text-[15px] tabular-nums">
                  {item.value.toLocaleString('es-ES')}
                </span>
              </li>
            ))}
          </ul>
        </>
      ) : (
        <p className="mt-3 text-[13px] text-muted">El motor no dejó ninguna decisión.</p>
      )}

      {down.length ? (
        <div className="mt-4">
          <Notice
            tone="warning"
            title={`Fuentes caídas: ${down.map(([name, why]) => `${name} (${why})`).join(', ')}`}
          >
            Esos casos se escalan.
          </Notice>
        </div>
      ) : null}

      <div className="mt-5 flex justify-end">
        <Link
          to={paths.instances(processId, runId)}
          className="inline-flex items-center gap-1.5 rounded-full bg-ink px-3.5 py-1.5 text-[12px] font-medium text-on-ink hover:bg-ink/90"
        >
          Ver documentos
          <ArrowRight size={12} strokeWidth={2} />
        </Link>
      </div>
    </div>
  )
}
