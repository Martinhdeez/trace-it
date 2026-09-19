import { useEffect, useRef, useState } from 'react'
import { motion, useReducedMotion } from 'motion/react'
import { FileText, LoaderCircle, Play, Search } from 'lucide-react'
import hackspain from '../../assets/hackspain.png'
import maisa from '../../assets/maisa.png'
import mark from '../../assets/trace-mark.png'
import { cn } from '../../lib/cn'
import { StatusBadge } from '../shell/StatusBadge'
import {
  INVOICES,
  NORM,
  PACK,
  RESULT,
  RULES,
  STAGES,
  type Invoice,
} from './demo'

const sleep = (ms: number) => new Promise<void>((resolve) => window.setTimeout(resolve, ms))

type Phase = 'write' | 'compile' | 'drop' | 'run'
type RuleLive = { status: 'queued' | 'tester' | 'compiler' | 'activa'; cases: number; attempt: number }
type DocLive = { landed: boolean; stage: number; checkAt: number; hold: number }
type Pt = { x: number; y: number }
type Mood = 'soft' | 'flick' | 'heavy'
type Cursor = {
  x: number
  y: number
  aX: number
  aY: number
  bX: number
  bY: number
  down: boolean
  show: boolean
  tap: number
  hop: boolean
  mood: Mood
  dur: number
}

const OUT: [number, number, number, number] = [0.23, 1, 0.32, 1]
const idle: Cursor = {
  x: 0,
  y: 0,
  aX: 0,
  aY: 0,
  bX: 0,
  bY: 0,
  down: false,
  show: false,
  tap: 0,
  hop: true,
  mood: 'soft',
  dur: 0.5,
}

const SPAWN: Pt[] = [
  { x: -22, y: 16 },
  { x: 18, y: 20 },
  { x: -10, y: -18 },
  { x: 24, y: 8 },
  { x: -16, y: 22 },
  { x: 12, y: -14 },
]

const MOOD: Record<
  Mood,
  {
    timesX: number[]
    timesY: number[]
    yMul: number
    easeX: [number, number, number, number][]
    easeY: [number, number, number, number][]
  }
> = {
  soft: {
    timesX: [0, 0.3, 0.62, 1],
    timesY: [0, 0.36, 0.68, 1],
    yMul: 1.16,
    easeX: [
      [0.22, 0.08, 0.36, 1],
      [0.2, 0.1, 0.18, 1],
      [0.16, 0.08, 0.14, 1],
    ],
    easeY: [
      [0.18, 0.12, 0.3, 1],
      [0.24, 0.08, 0.16, 1],
      [0.2, 0.1, 0.12, 1],
    ],
  },
  flick: {
    timesX: [0, 0.2, 0.52, 1],
    timesY: [0, 0.28, 0.7, 1],
    yMul: 1.04,
    easeX: [
      [0.3, 0, 0.4, 1],
      [0.16, 0.04, 0.12, 1],
      [0.12, 0.06, 0.1, 1],
    ],
    easeY: [
      [0.24, 0.06, 0.34, 1],
      [0.2, 0.08, 0.14, 1],
      [0.18, 0.1, 0.12, 1],
    ],
  },
  heavy: {
    timesX: [0, 0.4, 0.72, 1],
    timesY: [0, 0.46, 0.78, 1],
    yMul: 1.22,
    easeX: [
      [0.36, 0.1, 0.42, 1],
      [0.28, 0.12, 0.2, 1],
      [0.2, 0.1, 0.16, 1],
    ],
    easeY: [
      [0.32, 0.14, 0.38, 1],
      [0.26, 0.1, 0.18, 1],
      [0.22, 0.12, 0.14, 1],
    ],
  },
}

function perp(from: Pt, to: Pt, along: number, bulge: number): Pt {
  const dx = to.x - from.x
  const dy = to.y - from.y
  const len = Math.hypot(dx, dy) || 1
  return {
    x: from.x + dx * along - (dy / len) * bulge,
    y: from.y + dy * along + (dx / len) * bulge,
  }
}

function mix(a: Pt, b: Pt, t: number): Pt {
  return { x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t }
}

function stroke(from: Pt, to: Pt, i: number): { a: Pt; b: Pt; dur: number; hesitate: number; mood: Mood } {
  const len = Math.hypot(to.x - from.x, to.y - from.y)
  if (len < 28) {
    const fidget = [
      { a: { x: from.x + 8, y: from.y - 12 }, b: { x: to.x - 5, y: to.y - 2 }, dur: 0.4, hesitate: 50, mood: 'soft' as const },
      { a: { x: from.x + 13, y: from.y + 3 }, b: { x: to.x - 3, y: to.y + 11 }, dur: 0.46, hesitate: 20, mood: 'flick' as const },
      { a: { x: from.x - 10, y: from.y + 7 }, b: mix(from, to, 0.45), dur: 0.42, hesitate: 80, mood: 'heavy' as const },
    ]
    return fidget[i % fidget.length]
  }
  const nx = (to.x - from.x) / (len || 1)
  const ny = (to.y - from.y) / (len || 1)
  const long = [
    () => ({ a: perp(from, to, 0.34, len * 0.26), b: perp(from, to, 0.7, len * 0.07), dur: 0.64, hesitate: 30, mood: 'soft' as const }),
    () => ({ a: perp(from, to, 0.28, -len * 0.22), b: perp(from, to, 0.68, len * 0.18), dur: 0.76, hesitate: 45, mood: 'soft' as const }),
    () => ({
      a: perp(from, to, 0.48, len * 0.12),
      b: { x: to.x + nx * 16, y: to.y + ny * 12 },
      dur: 0.56,
      hesitate: 12,
      mood: 'flick' as const,
    }),
    () => ({
      a: { x: from.x + (to.x - from.x) * 0.18, y: from.y + (to.y - from.y) * 0.52 + 30 },
      b: perp(from, to, 0.78, -len * 0.1),
      dur: 0.72,
      hesitate: 36,
      mood: 'heavy' as const,
    }),
    () => ({ a: perp(from, to, 0.22, -len * 0.34), b: perp(from, to, 0.54, -len * 0.12), dur: 0.82, hesitate: 22, mood: 'heavy' as const }),
    () => ({ a: perp(from, to, 0.6, len * 0.09), b: mix(from, to, 0.88), dur: 0.48, hesitate: 70, mood: 'flick' as const }),
  ]
  return long[i % long.length]()
}

function scatter(at: Pt, i: number): Pt {
  return { x: at.x + ((i * 17) % 9) - 4, y: at.y + ((i * 11) % 7) - 3 }
}

const emptyRules = (): RuleLive[] => RULES.map(() => ({ status: 'queued', cases: 0, attempt: 0 }))
const emptyDocs = (): DocLive[] => INVOICES.map(() => ({ landed: false, stage: 0, checkAt: 0, hold: 0 }))

export function Story() {
  const reduce = useReducedMotion() ?? false
  const play = usePlay(reduce)

  return (
    <>
      <p className="sr-only">
        La consola escribe la norma, la compila a once reglas, suelta el lote y decide en paralelo.
        En HackSpain: 433 PAGAR, 36 NO_PAGAR, 31 ESCALAR.
      </p>
      <Desk play={play} reduce={reduce} />
      <Notes />
    </>
  )
}

function usePlay(reduce: boolean) {
  const frame = useRef<HTMLDivElement>(null)
  const action = useRef<HTMLButtonElement>(null)
  const runBtn = useRef<HTMLButtonElement>(null)
  const invoice = useRef<HTMLButtonElement>(null)
  const stop = useRef(false)

  const [phase, setPhase] = useState<Phase>('write')
  const [typed, setTyped] = useState(reduce ? NORM : '')
  const [rules, setRules] = useState<RuleLive[]>(emptyRules)
  const [docs, setDocs] = useState<DocLive[]>(emptyDocs)
  const [openDoc, setOpenDoc] = useState(1)
  const [cursor, setCursor] = useState<Cursor>(idle)
  const armed = useRef(false)
  const last = useRef<Pt | null>(null)
  const strokeN = useRef(0)

  const snap = useRef({ phase, rules, docs })
  snap.current = { phase, rules, docs }

  const point = (el: HTMLElement | null) => {
    const root = frame.current
    if (!el || !root) return null
    const a = root.getBoundingClientRect()
    const b = el.getBoundingClientRect()
    return { x: b.left - a.left + b.width / 2, y: b.top - a.top + b.height / 2 }
  }

  const click = async (el: HTMLElement | null) => {
    const raw = point(el)
    if (!raw || stop.current) return
    const i = strokeN.current++
    const at = scatter(raw, i)
    const from = last.current
    if (!from || !armed.current) {
      const spawnOff = SPAWN[i % SPAWN.length]
      const spawn = { x: at.x + spawnOff.x, y: at.y + spawnOff.y }
      setCursor((prev) => ({
        ...prev,
        ...spawn,
        aX: spawn.x,
        aY: spawn.y,
        bX: spawn.x,
        bY: spawn.y,
        hop: true,
        down: false,
        show: false,
      }))
      await sleep(reduce ? 0 : 48)
      if (stop.current) return
      setCursor((prev) => ({ ...prev, show: true, hop: true }))
      await sleep(reduce ? 50 : 140)
      if (stop.current) return
      const drift = stroke(spawn, at, i)
      setCursor((prev) => ({
        ...prev,
        ...at,
        aX: drift.a.x,
        aY: drift.a.y,
        bX: drift.b.x,
        bY: drift.b.y,
        hop: false,
        show: true,
        mood: drift.mood,
        dur: reduce ? 0 : drift.dur,
      }))
      armed.current = true
      last.current = at
      await sleep(reduce ? 80 : Math.round(drift.dur * 1000 + drift.hesitate))
    } else {
      const move = stroke(from, at, i)
      setCursor((prev) => ({
        ...prev,
        ...at,
        aX: move.a.x,
        aY: move.a.y,
        bX: move.b.x,
        bY: move.b.y,
        hop: false,
        down: false,
        show: true,
        mood: move.mood,
        dur: reduce ? 0 : move.dur,
      }))
      last.current = at
      await sleep(reduce ? 80 : Math.round(move.dur * 1000 + move.hesitate))
    }
    if (stop.current) return
    setCursor((prev) => ({ ...prev, down: true, tap: prev.tap + 1, hop: true }))
    await sleep(reduce ? 40 : 130)
    if (stop.current) return
    setCursor((prev) => ({ ...prev, down: false }))
    await sleep(reduce ? 40 : 140)
    if (stop.current) return
    setCursor((prev) => ({ ...prev, show: false }))
  }

  useEffect(() => {
    stop.current = false
    let timer = 0

    const until = async (ok: () => boolean) => {
      while (!stop.current && !ok()) await sleep(60)
    }

    const loop = async () => {
      while (!stop.current) {
        setPhase('write')
        setTyped(reduce ? NORM : '')
        setRules(emptyRules())
        setDocs(emptyDocs())
        setOpenDoc(1)
        armed.current = false
        last.current = null
        setCursor((prev) => ({ ...prev, show: false, down: false, hop: true }))
        await sleep(reduce ? 200 : 700)

        if (!reduce) {
          for (let i = 0; i < NORM.length && !stop.current; i += 4) {
            setTyped(NORM.slice(0, i))
            await sleep(14)
          }
        }
        setTyped(NORM)
        await sleep(reduce ? 120 : 380)
        await click(action.current)

        setPhase('compile')
        await until(
          () =>
            snap.current.rules.every((rule) => rule.status === 'activa') &&
            snap.current.phase === 'compile',
        )
        await sleep(reduce ? 120 : 500)
        await click(action.current)

        setPhase('drop')
        await until(() => snap.current.docs.every((doc) => doc.landed))
        await sleep(reduce ? 120 : 400)
        await click(runBtn.current)

        setPhase('run')
        await until(
          () =>
            snap.current.docs.every((doc) => !doc.landed || doc.stage > STAGES.length) &&
            snap.current.phase === 'run',
        )
        await sleep(reduce ? 120 : 360)
        await click(invoice.current)
        setOpenDoc(1)
        armed.current = false
        await sleep(reduce ? 900 : 4200)
      }
    }

    timer = window.setTimeout(() => {
      void loop()
    }, 240)

    return () => {
      stop.current = true
      window.clearTimeout(timer)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reduce])

  useEffect(() => {
    if (phase !== 'compile') return
    const id = window.setInterval(() => {
      setRules((current) => {
        if (current.every((rule) => rule.status === 'activa')) return current
        return stepCompile(current)
      })
    }, reduce ? 40 : 150)
    return () => window.clearInterval(id)
  }, [phase, reduce])

  useEffect(() => {
    if (phase !== 'drop') return
    let i = 0
    const id = window.setInterval(() => {
      setDocs((current) => {
        const next = current.map((doc) => ({ ...doc }))
        const slot = next.findIndex((doc) => !doc.landed)
        if (slot >= 0) next[slot].landed = true
        return next
      })
      i += 1
      if (i >= INVOICES.length) window.clearInterval(id)
    }, reduce ? 30 : 110)
    return () => window.clearInterval(id)
  }, [phase, reduce])

  useEffect(() => {
    if (phase !== 'run') return
    const id = window.setInterval(() => {
      setDocs((current) => {
        if (current.every((doc) => !doc.landed || doc.stage > STAGES.length)) return current
        return stepRun(current)
      })
    }, reduce ? 40 : 170)
    return () => window.clearInterval(id)
  }, [phase, reduce])

  const activa = rules.filter((rule) => rule.status === 'activa').length
  const compiling = rules.filter((rule) => rule.status === 'tester' || rule.status === 'compiler').length
  const landed = docs.filter((doc) => doc.landed).length
  const decided = docs.filter((doc) => doc.landed && doc.stage > STAGES.length).length

  return {
    frame,
    action,
    runBtn,
    invoice,
    phase,
    typed,
    rules,
    docs,
    openDoc,
    cursor,
    activa,
    compiling,
    landed,
    decided,
  }
}

function stepCompile(current: RuleLive[]): RuleLive[] {
  const next = current.map((rule) => ({ ...rule }))
  const inflight = next.filter((rule) => rule.status === 'tester' || rule.status === 'compiler').length
  if (inflight < 2) {
    const queued = next.findIndex((rule) => rule.status === 'queued')
    if (queued >= 0) next[queued].status = 'tester'
  }
  next.forEach((rule, index) => {
    const spec = RULES[index]
    if (rule.status === 'tester') {
      rule.cases = Math.min(spec.tests, rule.cases + 2)
      if (rule.cases >= spec.tests) {
        rule.status = 'compiler'
        rule.attempt = 1
      }
    } else if (rule.status === 'compiler') {
      rule.attempt += 1
      if (rule.attempt >= 2) rule.status = 'activa'
    }
  })
  return next
}

function stepRun(current: DocLive[]): DocLive[] {
  return current.map((doc, index) => {
    if (!doc.landed || doc.stage > STAGES.length) return doc
    if (doc.stage === 0) return { ...doc, stage: 1, checkAt: 0, hold: 0 }
    if (doc.stage === 3) {
      const total = Math.max(1, INVOICES[index].checks.length)
      const checkAt = Math.min(total, doc.checkAt + 1)
      if (checkAt >= total) return { ...doc, stage: 4, checkAt, hold: 0 }
      return { ...doc, checkAt }
    }
    if (doc.hold < 1) return { ...doc, hold: doc.hold + 1 }
    return { ...doc, stage: doc.stage + 1, hold: 0 }
  })
}

type Play = ReturnType<typeof usePlay>

function Desk({ play, reduce }: { play: Play; reduce: boolean }) {
  return (
    <section className="flex min-h-[calc(100dvh-3.5rem)] items-center px-3 py-5 sm:px-6 md:px-8">
      <div
        ref={play.frame}
        className="relative mx-auto w-full max-w-[1120px] overflow-hidden rounded-[14px] bg-canvas shadow-[0_24px_80px_rgba(19,19,19,0.10)] ring-1 ring-black/[0.08] sm:rounded-[18px]"
      >
        <Titlebar phase={play.phase} />
        <div className="pointer-events-none flex h-[min(70dvh,720px)] w-full min-w-0 sm:h-[min(78vh,720px)]">
          <MiniSidebar phase={play.phase} />
          <div className="flex min-w-0 flex-1 flex-col p-2">
            <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden rounded-[16px] bg-shell shadow-[0_1px_2px_rgba(19,19,19,0.04),0_8px_24px_rgba(19,19,19,0.04)] ring-1 ring-black/[0.06]">
              <Screen play={play} />
            </div>
          </div>
        </div>
        <Ghost cursor={play.cursor} reduce={reduce} />
      </div>
    </section>
  )
}

function Titlebar({ phase }: { phase: Phase }) {
  const path = phase === 'write' || phase === 'compile' ? 'procesos/1/reglas' : 'procesos/1'
  return (
    <div className="flex h-10 items-center gap-3 border-b border-black/[0.06] bg-white px-3">
      <span className="flex gap-1.5">
        <span className="h-2.5 w-2.5 rounded-full bg-[#ff5f57]" />
        <span className="h-2.5 w-2.5 rounded-full bg-[#febc2e]" />
        <span className="h-2.5 w-2.5 rounded-full bg-[#28c840]" />
      </span>
      <p className="min-w-0 truncate font-mono text-[11px] text-faint">trace.it/{path}</p>
    </div>
  )
}

function MiniSidebar({ phase }: { phase: Phase }) {
  const onRules = phase === 'write' || phase === 'compile'
  return (
    <aside className="hidden w-[168px] shrink-0 flex-col md:flex lg:w-[196px]">
      <div className="flex items-center gap-1.5 px-4 pt-3 pb-3">
        <img src={mark} alt="" className="h-5 w-5 rounded-[5px] object-cover" draggable={false} />
        <p className="text-[12px] font-medium tracking-[-0.03em]">
          trace<span className="text-faint">[.]</span>it
        </p>
      </div>
      <div className="px-3 pb-3">
        <div className="flex items-center gap-2 rounded-full bg-white px-2.5 py-1 text-[12px] text-muted ring-1 ring-black/[0.06]">
          <Search size={12} strokeWidth={1.5} />
          Filtrar
          <kbd className="ml-auto grid h-4 min-w-4 place-items-center rounded-[5px] bg-canvas font-mono text-[9px] text-faint ring-1 ring-black/[0.06]">
            ⌘K
          </kbd>
        </div>
      </div>
      <div className="px-3">
        <p className="px-2.5 pb-1.5 text-[10px] font-medium tracking-[0.14em] text-muted uppercase">
          Procesos
        </p>
        <div className="rounded-[10px] bg-white px-2.5 py-1.5 text-[12px] shadow-[0_1px_2px_rgba(19,19,19,0.06)]">
          Invoice payment
        </div>
        <div className="ml-2 mt-2 border-l border-black/[0.08] pl-2">
          <p className="px-2 pb-1 font-mono text-[8px] tracking-[0.12em] text-faint">PREPARAR</p>
          <SideLink active={onRules}>Reglas y versiones</SideLink>
          <p className="mt-2 px-2 pb-1 font-mono text-[8px] tracking-[0.12em] text-faint">OPERAR</p>
          <SideLink active={!onRules}>Ejecuciones</SideLink>
        </div>
      </div>
    </aside>
  )
}

function SideLink({ active, children }: { active?: boolean; children: string }) {
  return (
    <div
      className={cn(
        'rounded-[8px] px-2 py-[5px] text-[12px]',
        active ? 'bg-white text-ink shadow-[0_1px_2px_rgba(19,19,19,0.06)]' : 'text-ink/70',
      )}
    >
      {children}
    </div>
  )
}

function Screen({ play }: { play: Play }) {
  const onRules = play.phase === 'write' || play.phase === 'compile'
  return (
    <>
      <header className="flex h-11 shrink-0 items-center justify-between gap-3 px-5">
        <p className="min-w-0 truncate text-[12px] text-muted">
          Procesos <span className="text-faint">·</span>{' '}
          <span className="text-ink">Invoice payment</span>
          {onRules ? (
            <>
              <span className="text-faint"> · </span>
              <span className="text-ink">Reglas y versiones</span>
            </>
          ) : null}
        </p>
        {onRules ? (
          <button
            ref={play.action}
            type="button"
            tabIndex={-1}
            className="inline-flex items-center gap-1.5 rounded-full bg-ink px-3 py-1 text-[12px] font-medium text-white"
          >
            {play.phase === 'write' ? (
              'Compilar'
            ) : play.activa < RULES.length ? (
              <>
                <Spin />
                Compilando ({play.compiling})
              </>
            ) : (
              `Activar ${PACK.version}`
            )}
          </button>
        ) : (
          <button
            ref={play.runBtn}
            type="button"
            tabIndex={-1}
            className="inline-flex items-center gap-1.5 rounded-full bg-canvas px-3 py-1 text-[12px] font-medium ring-1 ring-black/[0.06]"
          >
            <Play size={11} strokeWidth={2} />
            {play.phase === 'run' ? 'Ejecutando…' : 'Ejecutar'}
          </button>
        )}
      </header>
      <div className="min-h-0 min-w-0 flex-1 overflow-y-auto px-3 pt-1 pb-3 sm:px-5 sm:pt-1.5 sm:pb-4">
        {onRules ? <RulesScreen play={play} /> : <RunScreen play={play} />}
      </div>
    </>
  )
}

function RulesScreen({ play }: { play: Play }) {
  return (
    <div className="grid h-full min-w-0 grid-cols-1 gap-3 p-px lg:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)]">
      <div className="min-w-0 overflow-hidden rounded-[14px] bg-white ring-1 ring-black/[0.06]">
        <div className="flex items-center justify-between px-3 py-1.5">
          <span className="font-mono text-[11px] text-faint">Norma_Pagos_v3</span>
          <span className="font-mono text-[10px] text-faint">
            {play.phase === 'write' && play.typed !== NORM ? 'escribiendo' : 'listo'}
          </span>
        </div>
        <p className="px-3.5 pb-3.5 text-[13px] leading-6 break-words whitespace-pre-wrap">
          {play.typed}
          {play.phase === 'write' && play.typed !== NORM ? <span className="caret" aria-hidden /> : null}
        </p>
      </div>
      <div className="flex min-h-0 min-w-0 flex-col overflow-hidden">
        <p className="mb-2 shrink-0 font-mono text-[10px] text-faint">
          {play.activa} / {RULES.length}
        </p>
        <ol className="min-h-0 flex-1 space-y-1 overflow-y-auto p-px">
          {RULES.map((rule, index) => {
            const live = play.rules[index]
            if (live.status === 'queued') return null
            return (
              <li
                key={rule.id}
                className="flex items-center gap-2 rounded-[10px] bg-white px-2.5 py-1.5 ring-1 ring-black/[0.06]"
              >
                <span className="w-4 shrink-0 font-mono text-[10px] text-faint">
                  {String(index + 1).padStart(2, '0')}
                </span>
                <span className="min-w-0 flex-1 truncate text-[12px]">{rule.text}</span>
                {live.status === 'activa' ? (
                  <span className="shrink-0 font-mono text-[10px] text-pagar">activa</span>
                ) : (
                  <span className="flex shrink-0 items-center gap-1 font-mono text-[10px] text-faint">
                    <Spin />
                    {live.status === 'tester' ? `${live.cases}/${rule.tests}` : `intento ${live.attempt}`}
                  </span>
                )}
              </li>
            )
          })}
        </ol>
      </div>
    </div>
  )
}

function RunScreen({ play }: { play: Play }) {
  const current = INVOICES[play.openDoc] ?? INVOICES[0]
  const live = play.docs[play.openDoc] ?? play.docs[0]
  return (
    <div className="grid h-full min-w-0 grid-cols-1 gap-3 p-px lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
      <div className="flex min-h-0 min-w-0 flex-col gap-3">
        <div className="flex items-center justify-between rounded-[14px] bg-white px-3.5 py-2.5 ring-1 ring-black/[0.06]">
          <div>
            <p className="text-[13px] font-medium tracking-[-0.03em]">{PACK.name}</p>
            <p className="font-mono text-[10px] text-faint">
              {PACK.origin} · {RULES.length} reglas · {PACK.hash}
            </p>
          </div>
          <StatusBadge value="activa">{PACK.version}</StatusBadge>
        </div>
        <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden rounded-[14px] bg-well/80 ring-1 ring-black/[0.04]">
          <p className="shrink-0 px-3 py-2 text-[12px] text-muted">
            {play.landed === 0 ? 'Suelta PDF o una carpeta' : `${play.landed} documentos`}
          </p>
          <ul className="min-h-0 flex-1 space-y-1 overflow-y-auto px-2 pt-0.5 pb-2">
            {INVOICES.map((item, index) => {
              const doc = play.docs[index]
              if (!doc.landed) return null
              const done = doc.stage > STAGES.length
              const running = play.phase === 'run' && doc.stage > 0 && !done
              return (
                <li key={item.file}>
                  <button
                    ref={index === 1 ? play.invoice : undefined}
                    type="button"
                    tabIndex={-1}
                    className={cn(
                      'flex w-full min-w-0 items-center gap-2 rounded-[10px] bg-white px-2.5 py-1.5 text-left ring-1 ring-black/[0.05]',
                      play.openDoc === index && play.phase === 'run' && 'ring-ink/20',
                    )}
                  >
                    <FileText size={12} strokeWidth={1.5} className="shrink-0 text-faint" />
                    <span className="min-w-0 flex-1 truncate font-mono text-[11px]">{item.file}</span>
                    {done ? (
                      <StatusBadge value={item.decision}>{item.decision.replace('_', ' ')}</StatusBadge>
                    ) : running ? (
                      <span className="flex shrink-0 items-center gap-1 font-mono text-[10px] text-faint">
                        <Spin />
                        {doc.stage === 3 ? `${doc.checkAt}/${item.checks.length}` : STAGES[doc.stage - 1]}
                      </span>
                    ) : (
                      <span className="shrink-0 font-mono text-[10px] text-faint">en cola</span>
                    )}
                  </button>
                </li>
              )
            })}
          </ul>
        </div>
      </div>
      <Inspect invoice={current} live={live} running={play.phase === 'run'} />
    </div>
  )
}

function Inspect({
  invoice,
  live,
  running,
}: {
  invoice: Invoice
  live: DocLive
  running: boolean
}) {
  const done = live.stage > STAGES.length
  const shown = running || done ? invoice.checks.slice(0, Math.max(0, live.checkAt)) : []
  return (
    <aside className="min-h-0 min-w-0 overflow-y-auto rounded-[14px] bg-white ring-1 ring-black/[0.06]">
      <div className="px-3.5 py-3">
        <p className="truncate font-mono text-[11px]">{invoice.file}</p>
        <p
          className={cn(
            'mt-1 text-[22px] font-medium tracking-[-0.04em]',
            done && invoice.decision === 'PAGAR' && 'text-pagar',
            done && invoice.decision === 'NO_PAGAR' && 'text-nopagar',
            done && invoice.decision === 'ESCALAR' && 'text-escalar',
            !done && 'text-faint',
          )}
        >
          {done
            ? invoice.decision.replace('_', ' ')
            : running && live.stage > 0
              ? STAGES[Math.min(live.stage, STAGES.length) - 1]
              : '—'}
        </p>
        <p className="mt-1 text-[11px] leading-4 text-muted">
          {done ? invoice.reason : running ? 'evaluando' : 'Sin ejecutar.'}
        </p>
      </div>
      <ul className="border-t border-hairline">
        {shown.map((check) => (
          <li key={check.rule} className="flex items-start gap-2 px-3.5 py-1">
            <span className={cn('mt-0.5 font-mono text-[9px]', check.ok ? 'text-pagar' : 'text-nopagar')}>
              {check.ok ? 'ok' : '×'}
            </span>
            <span className="min-w-0 flex-1 truncate text-[11px]">{check.rule}</span>
          </li>
        ))}
      </ul>
    </aside>
  )
}

function Ghost({ cursor, reduce }: { cursor: Cursor; reduce: boolean }) {
  const placed = useRef({ x: cursor.x, y: cursor.y })
  const from = placed.current
  const moved = from.x !== cursor.x || from.y !== cursor.y
  useEffect(() => {
    placed.current = { x: cursor.x, y: cursor.y }
  }, [cursor.x, cursor.y])

  const snap = reduce || cursor.hop || !moved
  const mood = MOOD[cursor.mood]

  return (
    <motion.div
      aria-hidden
      className="pointer-events-none absolute top-0 left-0 z-40"
      initial={false}
      animate={{
        x: snap ? cursor.x : [from.x, cursor.aX, cursor.bX, cursor.x],
        y: snap ? cursor.y : [from.y, cursor.aY, cursor.bY, cursor.y],
        opacity: cursor.show ? 1 : 0,
      }}
      transition={
        reduce
          ? { duration: 0 }
          : {
              x: snap
                ? { duration: 0 }
                : { duration: cursor.dur, times: mood.timesX, ease: mood.easeX },
              y: snap
                ? { duration: 0 }
                : { duration: cursor.dur * mood.yMul, times: mood.timesY, ease: mood.easeY },
              opacity: { duration: cursor.show ? 0.2 : 0.42, ease: OUT },
            }
      }
      style={{ willChange: 'transform, opacity' }}
    >
      <span className="relative block size-5 -translate-x-1/2 -translate-y-1/2">
        <motion.span
          className="absolute inset-0 rounded-full bg-ink/60 shadow-[0_0_0_1px_rgba(255,255,255,0.42),0_1px_4px_rgba(19,19,19,0.14)]"
          animate={{ scale: cursor.down ? 0.82 : 1 }}
          transition={reduce ? { duration: 0 } : { duration: 0.14, ease: OUT }}
        />
        {cursor.tap > 0 ? (
          <motion.span
            key={cursor.tap}
            className="absolute inset-0 rounded-full border-[1.5px] border-ink/40"
            initial={reduce ? false : { scale: 0.9, opacity: 0.4 }}
            animate={{ scale: 2.35, opacity: 0 }}
            transition={reduce ? { duration: 0 } : { duration: 0.5, ease: OUT }}
          />
        ) : null}
      </span>
    </motion.div>
  )
}

function Notes() {
  return (
    <section className="mx-auto w-full max-w-[640px] space-y-14 px-6 py-24 md:px-0">
      <p className="text-[17px] leading-7">
        Escribes la norma en castellano. Un tester ciego escribe los casos. Un compilador escribe el
        código hasta pasarlos. Once reglas, una versión, un hash.
      </p>
      <p className="text-[17px] leading-7">
        Suelto los PDF. El motor las corre en paralelo. Cada factura deja la traza de cada regla:
        de dónde salió el NIF, por qué no pagó, qué símbolo faltaba.
      </p>
      <div className="flex gap-10">
        <NoteFigure n={RESULT.pagar} label="PAGAR" className="text-pagar" />
        <NoteFigure n={RESULT.nopagar} label="NO PAGAR" className="text-nopagar" />
        <NoteFigure n={RESULT.escalar} label="ESCALAR" className="text-escalar" />
      </div>
      <p className="text-[15px] leading-7 text-muted">
        {RESULT.match} con el lote de HackSpain, iguales a la referencia. Motor {RESULT.engine}.
        Compilación {RESULT.compile}.
      </p>
      <div className="flex items-center gap-5">
        <img src={hackspain} alt="HackSpain" className="h-10 w-auto object-contain" draggable={false} />
        <span className="text-faint">×</span>
        <img src={maisa} alt="Maisa" className="h-6 w-auto object-contain" draggable={false} />
      </div>
    </section>
  )
}

function NoteFigure({ n, label, className }: { n: number; label: string; className: string }) {
  return (
    <div>
      <p className={cn('u-figure text-[40px]', className)}>{n}</p>
      <p className="mt-1 font-mono text-[11px] text-muted">{label}</p>
    </div>
  )
}

function Spin() {
  return <LoaderCircle size={11} strokeWidth={1.8} className="shrink-0 animate-spin text-current" />
}
