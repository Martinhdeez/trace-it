import { useEffect, useMemo, useRef, useState, type RefObject } from 'react'
import {
  animate,
  AnimatePresence,
  motion,
  MotionConfig,
  useInView,
  motionValue,
  useTransform,
  type MotionValue,
  useReducedMotion,
} from 'motion/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  ArrowUp,
  Check,
  ChevronLeft,
  ChevronRight,
  FileText,
  Paperclip,
  Pause,
  Play,
  RotateCcw,
} from 'lucide-react'
import { AppShell } from '../shell/AppShell'
import { Button, Segmented, Textarea } from '../shell/Controls'
import { StatusBadge } from '../shell/StatusBadge'
import { TerminalLoader } from '../shell/TerminalLoader'
import { NestedCard } from '../shell/Well'
import { EmptyState } from '../shell/Notice'
import { ProcessScreen } from '../process/ProcessScreen'
import {
  ProcessDraftMessage,
  ProcessDraftPreview,
  ProcessDraftReviewItem,
} from '../process/ProcessDraftChat'
import { FileChip } from '../process/FileChip'
import { DropZone } from '../process/DropZone'
import { QueueList } from '../run/QueueList'
import { TracePane } from '../run/TracePane'
import { cn } from '../../lib/cn'
import { t } from '../../i18n'
import { keys } from '../../api/queries'
import {
  CHAPTERS,
  DEMO_FILES,
  DEMO_PREVIEW,
  DEMO_PROMPT,
  DEMO_RESPONSE,
  demoInstance,
  demoTrace,
} from './walkthroughData'
import { INVOICES, PACK, RULES } from './demo'
import { WalkthroughCursor } from './WalkthroughCursor'
import { useBeat, useStep } from './walkthroughMotion'
import './walkthrough.css'

const noop = () => {}
const EASE = [0.22, 1, 0.36, 1] as const

/** Only the isolated cache below feeds the native shell. Queries cannot hit the API. */
function createPreviewClient() {
  const client = new QueryClient({
    defaultOptions: { queries: { enabled: false, staleTime: Infinity, retry: false } },
  })
  client.setQueryData(keys.processes, [{ id: 1, name: PACK.name }])
  client.setQueryData(keys.process(1), { id: 1, name: PACK.name })
  client.setQueryData(keys.summary(1), { queue: 1 })
  client.setQueryData(keys.planesHealth, [])
  return client
}

function usePlayer(frame: RefObject<HTMLDivElement | null>) {
  const reduce = useReducedMotion()
  const visible = useInView(frame, { amount: 0.25 })
  const [selection, setSelection] = useState(() => ({
    index: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 6 : 0,
    take: 0,
  }))
  const [playing, setPlaying] = useState(!reduce)
  const [finished, setFinished] = useState(false)
  const [pageVisible, setPageVisible] = useState(!document.hidden)
  const running = playing && visible && pageVisible
  const key = `${selection.index}:${selection.take}`
  // Each chapter owns one clock: cursor, content and progress stop at the same instant.
  const clock = useMemo(() => ({ key, elapsed: motionValue(0) }), [key])
  const { elapsed } = clock
  const duration = CHAPTERS[selection.index].duration
  const progress = useTransform(elapsed, (time) => time / duration)

  useEffect(() => {
    const onVisibility = () => setPageVisible(!document.hidden)
    document.addEventListener('visibilitychange', onVisibility)
    return () => document.removeEventListener('visibilitychange', onVisibility)
  }, [])

  useEffect(() => {
    if (!running) return
    const playback = animate(elapsed, duration, {
      duration: Math.max(0, duration - elapsed.get()) / 1000,
      ease: 'linear',
      onComplete: () => {
        if (selection.index === CHAPTERS.length - 1) {
          setPlaying(false)
          setFinished(true)
        } else setSelection((value) => ({ index: value.index + 1, take: value.take + 1 }))
      },
    })
    return () => playback.stop()
  }, [elapsed, duration, selection.index, running])

  const seek = (index: number) => {
    setFinished(false)
    setSelection((value) => ({ index, take: value.take + 1 }))
  }
  return {
    index: selection.index,
    sceneKey: clock.key,
    elapsed,
    progress,
    playing,
    finished,
    running,
    reduce: Boolean(reduce),
    seek,
    setPlaying,
  }
}

export function Story() {
  const frame = useRef<HTMLDivElement>(null)
  const player = usePlayer(frame)
  const [client] = useState(createPreviewClient)
  const chapter = CHAPTERS[player.index]
  const route = player.index < 4 ? '/processes/1/chat' : '/processes/1/instances'
  const [selectedInvoice, setSelectedInvoice] = useState(3)

  return (
    <MotionConfig reducedMotion="user">
      <section
        className="walkthrough mx-auto flex w-full max-w-[1500px] flex-col px-3 pt-6 pb-8 sm:px-6 lg:px-8"
        aria-label="Demostración animada de trace.it"
      >
        <div className="mb-5 flex min-h-[63px] items-end justify-between gap-4 px-1 sm:px-2">
          <AnimatePresence mode="wait" initial={false}>
            <motion.div
              key={chapter.id}
              initial={player.reduce ? false : { opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -3, transition: { duration: 0.12 } }}
              transition={{ duration: 0.22, ease: EASE }}
            >
              <h1 className="text-[23px] font-medium leading-tight tracking-[-0.045em] sm:text-[29px]">
                {chapter.title}
              </h1>
              <p className="mt-1.5 text-[12px] text-muted sm:text-[13px]">{chapter.detail}</p>
            </motion.div>
          </AnimatePresence>
          <span className="hidden shrink-0 pb-1 font-mono text-[10px] text-faint sm:block">
            DEMO ANIMADA · 41 s
          </span>
        </div>

        <div
          ref={frame}
          className="walkthrough-frame relative overflow-hidden rounded-[18px] bg-canvas shadow-pop ring-1 ring-line"
          role="img"
          aria-label={`${chapter.title} ${chapter.detail}`}
        >
          <div className="flex h-9 items-center justify-between border-b border-line bg-surface px-4">
            <div className="flex gap-1.5" aria-hidden>
              <span className="size-2 rounded-full bg-faint/30" />
              <span className="size-2 rounded-full bg-faint/25" />
              <span className="size-2 rounded-full bg-faint/20" />
            </div>
            <span className="font-mono text-[10px] text-faint">trace.it{route}</span>
            <span className="w-9" />
          </div>
          <div className="walkthrough-app" data-playing={player.running} inert>
            <QueryClientProvider client={client}>
              <AppShell preview={{ processId: 1 }}>
                <ProcessScreen
                  activeTab={player.index < 4 ? 'definition' : 'runs'}
                  processId={1}
                  crumbs={[{ label: 'Procesos' }, { label: PACK.name }]}
                  actions={
                    player.index >= 4 ? (
                      <StatusBadge value="activa">v3 publicada</StatusBadge>
                    ) : undefined
                  }
                >
                  <AnimatePresence mode="wait" initial={false}>
                    <motion.div
                      key={player.index < 4 ? 'definition' : 'instances'}
                      className="flex min-h-0 flex-1 flex-col"
                      initial={player.reduce ? false : { opacity: 0, y: 6 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, transition: { duration: 0.12 } }}
                      transition={{ duration: 0.24, ease: EASE }}
                    >
                      {player.index < 4 ? (
                        <DefinitionScene
                          key={player.sceneKey}
                          chapter={player.index}
                          running={player.running}
                          elapsed={player.elapsed}
                          reduce={player.reduce}
                        />
                      ) : (
                        <ExecutionScene
                          key={player.sceneKey}
                          chapter={player.index}
                          elapsed={player.elapsed}
                          reduce={player.reduce}
                          selectedInvoice={selectedInvoice}
                        />
                      )}
                    </motion.div>
                  </AnimatePresence>
                </ProcessScreen>
              </AppShell>
            </QueryClientProvider>
          </div>
          <WalkthroughCursor
            key={player.sceneKey}
            frame={frame}
            elapsed={player.elapsed}
            chapter={player.index}
            reduce={player.reduce}
          />
        </div>

        <div className="mt-5 flex items-center gap-3 sm:gap-5">
          <div className="flex shrink-0 items-center gap-1">
            <Button
              tone="primary"
              className="grid size-9 place-items-center p-0"
              aria-label={player.playing ? 'Pausar demostración' : 'Reproducir demostración'}
              onClick={() => {
                if (player.finished) player.seek(0)
                player.setPlaying(!player.playing)
              }}
            >
              {player.playing ? (
                <Pause size={13} fill="currentColor" />
              ) : (
                <Play size={13} fill="currentColor" />
              )}
            </Button>
            <Button
              tone="ghost"
              className="p-2"
              aria-label="Capítulo anterior"
              disabled={player.index === 0}
              onClick={() => player.seek(player.index - 1)}
            >
              <ChevronLeft size={15} />
            </Button>
            <Button
              tone="ghost"
              className="p-2"
              aria-label="Capítulo siguiente"
              disabled={player.index === 6}
              onClick={() => player.seek(player.index + 1)}
            >
              <ChevronRight size={15} />
            </Button>
          </div>
          <div
            className="grid min-w-0 flex-1 grid-cols-7 gap-2 sm:gap-3"
            aria-label="Capítulos de la demostración"
          >
            {CHAPTERS.map((item, index) => (
              <button
                key={item.id}
                type="button"
                className="group min-w-0 text-left"
                aria-label={item.label}
                aria-current={index === player.index ? 'step' : undefined}
                onClick={() => player.seek(index)}
              >
                <span className="relative mb-2 block h-[3px] overflow-hidden rounded-full bg-ink/10">
                  {index < player.index ? <span className="absolute inset-0 bg-ink" /> : null}
                  {index === player.index ? (
                    <motion.span
                      className="absolute inset-0 origin-left bg-ink"
                      style={{ scaleX: player.reduce ? 1 : player.progress }}
                    />
                  ) : null}
                </span>
                <span
                  className={cn(
                    'hidden truncate text-[11px] sm:block',
                    index === player.index
                      ? 'font-medium text-ink'
                      : 'text-faint group-hover:text-muted',
                  )}
                >
                  {item.label}
                </span>
              </button>
            ))}
          </div>
          <Button
            tone="ghost"
            className="p-2"
            aria-label="Reiniciar demostración"
            onClick={() => {
              player.seek(0)
              player.setPlaying(true)
            }}
          >
            <RotateCcw size={14} />
          </Button>
        </div>
        <div className="mt-4 flex min-h-[30px] flex-wrap items-center justify-between gap-3 px-1">
          <p className="text-[11px] text-faint">Demostración con datos de ejemplo.</p>
          {player.index === 6 ? (
            <Segmented
              value={String(selectedInvoice)}
              onChange={(value) => {
                setSelectedInvoice(Number(value))
                player.setPlaying(false)
              }}
              options={[
                { value: '3', label: 'Importe' },
                { value: '1', label: 'Fecha' },
                { value: '2', label: 'Escaneo' },
              ]}
            />
          ) : (
            <span className="font-mono text-[10px] text-faint">
              {String(player.index + 1).padStart(2, '0')} / 07
            </span>
          )}
        </div>
      </section>
    </MotionConfig>
  )
}

const reviewItems = [
  {
    key: 'suppliers',
    title: 'Proveedor e IBAN',
    description: 'El NIF existe y el IBAN coincide con el maestro.',
    detail: 'Proveedores.xlsx',
    evidence: [],
  },
  {
    key: 'orders',
    title: 'Pedido e importe',
    description: 'El pedido pertenece al proveedor. El total coincide, con tolerancia de 0,01 €.',
    detail: 'Pedidos_2026',
    evidence: [],
  },
  {
    key: 'erp',
    title: 'Estado del pedido',
    description: 'Solo pagar pedidos pendientes. Nunca pagar el mismo pedido dos veces.',
    detail: 'ERP · snapshot',
    evidence: [],
  },
]

function DefinitionScene({
  chapter,
  running,
  elapsed,
  reduce,
}: {
  chapter: number
  running: boolean
  elapsed: MotionValue<number>
  reduce: boolean
}) {
  const beat = useBeat(elapsed, chapter === 0 ? 420 : 480, 14)
  const reviewed = useBeat(elapsed, 800, 3, 350)
  const scrollStep = useStep(elapsed, chapter === 1 ? [3200] : [960])
  const sent = chapter > 0 || beat >= 9 || reduce
  const response = chapter > 0 || beat >= 12 || reduce
  const ready = chapter >= 3 || (chapter === 2 && (beat >= 10 || reduce))
  const conversation = useRef<HTMLDivElement>(null)
  const reviewPane = useRef<HTMLElement>(null)
  useEffect(() => {
    if (response && conversation.current) {
      conversation.current.scrollTo({
        top: conversation.current.scrollHeight,
        behavior: reduce ? 'instant' : 'smooth',
      })
    }
  }, [response, reduce])
  useEffect(() => {
    if ((chapter === 1 || chapter === 3) && scrollStep === 1) {
      reviewPane.current?.scrollTo({
        top: reviewPane.current.scrollHeight,
        behavior: reduce ? 'instant' : 'smooth',
      })
    }
  }, [chapter, scrollStep, reduce])
  const letters = useBeat(elapsed, 32, Math.ceil(DEMO_PROMPT.length / 2), 500)
  const typed = reduce ? DEMO_PROMPT : DEMO_PROMPT.slice(0, letters * 2)

  return (
    <div className="walkthrough-definition grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-[1.05fr_1fr]">
      <section
        className={cn(
          'flex min-h-0 flex-col border-r border-hairline',
          chapter > 0 && 'hidden lg:flex',
        )}
      >
        <header className="flex items-center justify-between border-b border-hairline px-5 py-3">
          <span className="text-[13px] font-medium">Conversación</span>
          <span className="font-mono text-[10px] text-faint">borrador de proceso</span>
        </header>
        <div ref={conversation} className="min-h-0 flex-1 space-y-4 overflow-y-auto px-5 py-5">
          {!sent ? (
            <EmptyState title="Cuéntame qué tiene que decidir" className="py-2">
              Puedes pegar la política o adjuntar XLSX, CSV y JSON como evidencia.
            </EmptyState>
          ) : (
            <motion.div
              initial={reduce || chapter > 0 ? false : { opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.24, ease: EASE }}
              className="flex justify-end"
            >
              <ProcessDraftMessage message={{ role: 'user', text: DEMO_PROMPT }} />
            </motion.div>
          )}
          {response ? (
            <motion.div
              initial={reduce || chapter > 0 ? false : { opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.24, ease: EASE }}
            >
              <ProcessDraftMessage message={{ role: 'assistant', text: DEMO_RESPONSE }} />
            </motion.div>
          ) : sent ? (
            <TerminalLoader
              paused={!running}
              verbs={['leyendo los documentos', 'preparando el proceso']}
            />
          ) : null}
          {chapter >= 2 ? (
            <div className="pt-2">
              <TerminalLoader
                paused={!running}
                verbs={
                  ready
                    ? ['comprobaciones terminadas']
                    : ['normalizando las reglas', 'compilando y probando']
                }
              />
            </div>
          ) : null}
        </div>
        <div className="border-t border-hairline px-5 py-4" data-demo="compose">
          {!sent ? (
            <div className="mb-3 flex flex-wrap gap-2">
              {DEMO_FILES.map((file) => (
                <FileChip key={file.id} file={file} />
              ))}
            </div>
          ) : null}
          <Textarea
            rows={3}
            readOnly
            value={sent ? '' : typed}
            placeholder="Pregunta algo o pide un cambio en el proceso."
          />
          <div className="mt-2 flex items-center justify-between">
            <Paperclip size={15} className="text-muted" />
            <div data-demo="send">
              <Button tone="primary">
                <ArrowUp size={13} />
                Enviar
              </Button>
            </div>
          </div>
        </div>
      </section>
      <aside
        ref={reviewPane}
        className={cn('min-h-0 overflow-y-auto px-5 py-5', chapter === 0 && 'hidden lg:block')}
      >
        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            key={
              chapter === 0 ? 'empty' : ready ? 'preview' : chapter === 2 ? 'compilation' : 'review'
            }
            className="h-full"
            initial={reduce ? false : { opacity: 0, y: 5 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, transition: { duration: 0.1 } }}
            transition={{ duration: 0.22, ease: EASE }}
          >
            {chapter === 0 ? (
              <div className="grid h-full place-content-center text-center">
                <div className="mx-auto mb-4 grid size-10 place-items-center rounded-[12px] bg-canvas ring-1 ring-line">
                  <FileText size={18} className="text-muted" />
                </div>
                <p className="text-[14px] font-medium">La definición aparece aquí</p>
                <p className="mt-2 max-w-[270px] text-[12px] leading-5 text-muted">
                  Revisa las propuestas antes de preparar la versión.
                </p>
              </div>
            ) : ready ? (
              <div data-demo="publish">
                <ProcessDraftPreview
                  preview={DEMO_PREVIEW}
                  publishing={chapter === 3 && beat >= 6}
                  onPrepare={noop}
                  onPublish={noop}
                />
              </div>
            ) : chapter === 2 ? (
              <CompilationScene beat={beat} running={running} />
            ) : (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-[15px] font-medium">Revisión</h2>
                    <p className="mt-1 text-[11px] text-faint">
                      {reduce ? 3 : reviewed} de 3 aprobadas
                    </p>
                  </div>
                  <div data-demo="approve">
                    <Button tone="primary">
                      <Check size={12} />
                      Aprobar pendientes
                    </Button>
                  </div>
                </div>
                <ul className="walkthrough-review space-y-2" data-demo="review">
                  {reviewItems.map((item, index) => (
                    <ProcessDraftReviewItem
                      key={item.key}
                      item={item}
                      disposition={reduce || reviewed > index ? 'accepted' : undefined}
                      reviewing={false}
                      onReview={noop}
                    />
                  ))}
                </ul>
                <NestedCard label="preparar versión">
                  <div className="space-y-3 px-3.5 py-3">
                    <p className="text-[12px] leading-5 text-muted">
                      Compila las reglas, ejecuta los ejemplos y compara el resultado con las
                      decisiones anteriores.
                    </p>
                    <div data-demo="prepare">
                      <Button tone="primary">Preparar y comprobar</Button>
                    </div>
                  </div>
                </NestedCard>
              </div>
            )}
          </motion.div>
        </AnimatePresence>
      </aside>
    </div>
  )
}

function CompilationScene({ beat, running }: { beat: number; running: boolean }) {
  const count = Math.min(beat + 1, RULES.length)
  return (
    <div className="space-y-4" data-demo="checks">
      <div className="flex items-center justify-between">
        <h2 className="text-[15px] font-medium">Preparando la versión</h2>
        <span className="font-mono text-[11px] text-muted">
          {count} / {RULES.length}
        </span>
      </div>
      <NestedCard label="compilación y pruebas">
        <ul className="divide-y divide-hairline">
          {RULES.slice(0, 6).map((rule, index) => (
            <li key={rule.id} className="flex items-center gap-3 px-3.5 py-3">
              <span
                className={cn('font-mono text-[10px]', index < count ? 'text-pagar' : 'text-faint')}
              >
                {index < count ? <Check size={13} /> : String(index + 1).padStart(2, '0')}
              </span>
              <span className="min-w-0 flex-1 text-[12px]">{rule.text}</span>
              {index < count ? (
                <StatusBadge value="activa">válida</StatusBadge>
              ) : (
                <span className="text-[10px] text-faint">en cola</span>
              )}
            </li>
          ))}
        </ul>
      </NestedCard>
      <TerminalLoader
        paused={!running}
        verbs={['probando los ejemplos', 'comprobando el resultado']}
      />
    </div>
  )
}

function ExecutionScene({
  chapter,
  elapsed,
  reduce,
  selectedInvoice,
}: {
  chapter: number
  elapsed: MotionValue<number>
  reduce: boolean
  selectedInvoice: number
}) {
  const beat = useBeat(elapsed, 550, 14)
  const uploaded = useBeat(elapsed, 400, INVOICES.length, 900)
  const traceStep = useStep(elapsed, [1000, 2200, 3500, 4600, 6800])
  const count = reduce ? INVOICES.length : chapter === 4 ? uploaded : INVOICES.length
  const done =
    chapter === 6 || (chapter === 5 && reduce)
      ? INVOICES.length
      : chapter === 5
        ? Math.min(beat, INVOICES.length)
        : 0
  const selected =
    chapter === 6 ? selectedInvoice : Math.max(0, Math.min(done - 1, INVOICES.length - 1))
  const traceRoot = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const list = traceRoot.current?.parentElement?.querySelector('section ul')
    const item = list?.children[selected]
    if (list && item) {
      list.scrollTo({
        top: item.getBoundingClientRect().top - list.getBoundingClientRect().top + list.scrollTop,
        behavior: reduce ? 'instant' : 'smooth',
      })
    }
  }, [selected, reduce])

  useEffect(() => {
    if (chapter !== 6 || traceStep === 0) return
    const root = traceRoot.current
    const pane = root?.querySelector('aside')
    if (traceStep === 5) {
      pane?.scrollTo({ top: 0, behavior: reduce ? 'instant' : 'smooth' })
      return
    }
    const title = traceStep >= 3 ? t('trace.symbols') : t('trace.rules')
    const button = [
      ...(root?.querySelectorAll<HTMLButtonElement>('button[aria-expanded]') ?? []),
    ].find((item) => item.textContent?.includes(title))
    if (!button) return
    if (traceStep === 2 || traceStep === 4) {
      if (button.getAttribute('aria-expanded') === 'false') button.click()
    } else if (pane) {
      pane.scrollTo({
        top:
          button.getBoundingClientRect().top -
          pane.getBoundingClientRect().top +
          pane.scrollTop -
          24,
        behavior: reduce ? 'instant' : 'smooth',
      })
    }
  }, [chapter, traceStep, reduce, selectedInvoice])

  if (chapter === 4)
    return (
      <div className="grid min-h-0 flex-1 grid-cols-1 gap-5 overflow-y-auto p-5 lg:grid-cols-[1fr_0.8fr]">
        <section>
          <div className="mb-5">
            <h2 className="text-[22px] font-medium tracking-[-0.04em]">Añadir documentos</h2>
            <p className="mt-2 text-[12px] text-muted">
              Las facturas se leen con la versión publicada del proceso.
            </p>
          </div>
          <div data-demo="drop">
            <DropZone
              label="Suelta PDF o una carpeta"
              hint="PDF con texto y documentos escaneados"
              accept=".pdf"
              multiple
              onFiles={noop}
            />
          </div>
          <div className="mt-5 space-y-2">
            {INVOICES.slice(0, count).map((invoice, index) => (
              <motion.div
                key={invoice.file}
                initial={reduce ? false : { opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.24, ease: EASE }}
                className="flex items-center gap-3 rounded-[12px] bg-surface px-4 py-3 ring-1 ring-line"
              >
                <FileText size={15} className="text-faint" />
                <span className="min-w-0 flex-1 truncate font-mono text-[11px]">
                  {invoice.file}
                </span>
                <StatusBadge value={index < count - 1 ? 'activa' : 'PENDING'}>
                  {index < count - 1 ? 'leída' : 'leyendo'}
                </StatusBadge>
              </motion.div>
            ))}
          </div>
        </section>
        <div className="hidden lg:block">
          <NestedCard label="versión publicada">
            <div className="space-y-4 px-4 py-4">
              <StatusBadge value="activa">v3 activa</StatusBadge>
              <p className="text-[14px]">Invoice payment</p>
              <p className="text-[12px] leading-6 text-muted">
                {RULES.length} reglas aprobadas. Cada documento conserva su archivo original y el
                origen de los datos extraídos.
              </p>
              <div className="flex gap-2">
                {DEMO_FILES.map((file) => (
                  <FileChip key={file.id} file={file} />
                ))}
              </div>
            </div>
          </NestedCard>
          <div className="mt-4" data-demo="execute">
            <Button tone="primary">
              <Play size={12} />
              Ejecutar
            </Button>
          </div>
        </div>
      </div>
    )

  const items = INVOICES.map((_, index) => demoInstance(index, index < done))
  return (
    <div
      data-demo="execution"
      className="flex min-h-0 flex-1 flex-col bg-canvas/40 pt-3 lg:flex-row"
    >
      <QueueList
        items={items}
        total={items.length}
        selectedId={selected + 1}
        onSelect={noop}
        header={
          <div className="flex items-center gap-2 px-2 py-2">
            <StatusBadge value={done === INVOICES.length ? 'activa' : 'PENDING'}>
              {done === INVOICES.length ? 'Finalizada' : 'En ejecución'}
            </StatusBadge>
            <span className="font-mono text-[10px] text-faint">
              {done} / {items.length}
            </span>
          </div>
        }
      />
      <div className="min-h-0 min-w-0 flex-1 overflow-y-auto" ref={traceRoot} data-demo="trace">
        <motion.div
          key={selected}
          className="walkthrough-trace-content h-full"
          initial={reduce ? false : { opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2, ease: EASE }}
        >
          <TracePane
            instance={done ? demoInstance(selected) : undefined}
            trace={done ? demoTrace(selected) : undefined}
          />
        </motion.div>
      </div>
    </div>
  )
}
