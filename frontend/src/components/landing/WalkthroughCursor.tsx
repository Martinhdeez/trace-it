import { useEffect, useRef, type RefObject } from 'react'
import { motion, useMotionValue, useMotionValueEvent, type MotionValue } from 'motion/react'
import { FileText } from 'lucide-react'
import { t } from '../../i18n'

type Cue = {
  start: number
  arrive: number
  press: number
  end: number
  selector: string
  text?: string
  drag?: boolean
}

// Arrival precedes the action. The pause lets the viewer see what will be pressed.
const CUES: readonly (readonly Cue[])[] = [
  [{ start: 2900, arrive: 3510, press: 3780, end: 4220, selector: '[data-demo="send"] button' }],
  [
    {
      start: 400,
      arrive: 950,
      press: 1150,
      end: 1290,
      selector: '[data-demo="review"] li:nth-child(1) button:last-child',
    },
    {
      start: 1300,
      arrive: 1750,
      press: 1950,
      end: 2090,
      selector: '[data-demo="review"] li:nth-child(2) button:last-child',
    },
    {
      start: 2100,
      arrive: 2550,
      press: 2750,
      end: 3010,
      selector: '[data-demo="review"] li:nth-child(3) button:last-child',
    },
    { start: 3670, arrive: 4370, press: 4700, end: 4980, selector: '[data-demo="prepare"] button' },
  ],
  [],
  [
    {
      start: 1580,
      arrive: 2500,
      press: 2880,
      end: 3420,
      selector: '[data-demo="publish"] button:last-child',
    },
  ],
  [{ start: 180, arrive: 850, press: 1000, end: 1350, selector: '[data-demo="drop"]', drag: true }],
  [],
  [
    {
      start: 1490,
      arrive: 1990,
      press: 2200,
      end: 2600,
      selector: '[data-demo="trace"] button[aria-expanded]',
      text: 'trace.rules',
    },
    {
      start: 3990,
      arrive: 4390,
      press: 4600,
      end: 5020,
      selector: '[data-demo="trace"] button[aria-expanded]',
      text: 'trace.symbols',
    },
  ],
]

const clamp = (value: number) => Math.min(1, Math.max(0, value))
// A shared easing drives a shallow curve with no overshoot or change of direction.
const ease = (value: number) => value * value * value * (value * (value * 6 - 15) + 10)

type Point = { x: number; y: number }
type Track = { cue: Cue; from: Point; to: Point; target: HTMLElement; continuous: boolean }

export function WalkthroughCursor({
  frame,
  elapsed,
  chapter,
  reduce,
}: {
  frame: RefObject<HTMLDivElement | null>
  elapsed: MotionValue<number>
  chapter: number
  reduce: boolean
}) {
  const x = useMotionValue(0)
  const y = useMotionValue(0)
  const opacity = useMotionValue(0)
  const scale = useMotionValue(1)
  const tapX = useMotionValue(0)
  const tapY = useMotionValue(0)
  const pulseScale = useMotionValue(0.7)
  const pulseOpacity = useMotionValue(0)
  const glowScale = useMotionValue(0.8)
  const glowOpacity = useMotionValue(0)
  const lastTap = useRef(-Infinity)
  const fileOpacity = useMotionValue(0)
  const track = useRef<Track | null>(null)

  useMotionValueEvent(elapsed, 'change', (time) => {
    if (reduce) return
    // The ripple stays on the control while the cursor moves on to its next target.
    const tapTime = time - lastTap.current
    pulseScale.set(0.65 + 0.95 * ease(clamp(tapTime / 460)))
    pulseOpacity.set(0.32 * ease(clamp(tapTime / 45)) * (1 - ease(clamp((tapTime - 45) / 415))))
    glowScale.set(0.8 + 0.5 * ease(clamp(tapTime / 280)))
    glowOpacity.set(0.14 * ease(clamp(tapTime / 35)) * (1 - ease(clamp((tapTime - 35) / 245))))
    const cue = CUES[chapter].find((item) => time >= item.start && time <= item.end)
    if (!cue) {
      const previous = track.current
      const next = previous && CUES[chapter].find((item) => item.start > previous.cue.start)
      if (!previous || !next) opacity.set(0)
      track.current?.target.removeAttribute('data-demo-pressed')
      return
    }
    const root = frame.current
    if (!root) return
    if (track.current?.cue !== cue) {
      const target = [...root.querySelectorAll<HTMLElement>(cue.selector)].find(
        (element) => !cue.text || element.textContent?.includes(t(cue.text)),
      )
      if (!target) {
        opacity.set(0)
        return
      }
      const bounds = root.getBoundingClientRect()
      const rect = target.getBoundingClientRect()
      // Never clamp a hidden target to the edge and pretend the cursor hit it.
      if (!rect.width || rect.bottom > bounds.bottom - 8 || rect.top < bounds.top + 36) {
        opacity.set(0)
        return
      }
      const to = {
        x: rect.left - bounds.left + rect.width * (cue.text ? 0.92 : 0.5),
        y: rect.top - bounds.top + rect.height / 2,
      }
      const previous = track.current
      const nearby = previous !== null
      const from = nearby
        ? previous.to
        : { x: to.x - (cue.drag ? 90 : 52), y: to.y + (cue.drag ? -36 : 26) }
      previous?.target.removeAttribute('data-demo-pressed')
      track.current = { cue, from, to, target, continuous: Boolean(nearby) }
    }
    const current = track.current
    if (!current) return
    const progress = ease(clamp((time - cue.start) / (cue.arrive - cue.start)))
    const dx = current.to.x - current.from.x
    const dy = current.to.y - current.from.y
    const distance = Math.hypot(dx, dy)
    const bend = Math.min(8, distance * 0.045)
    const bow = 4 * progress * (1 - progress) * bend
    x.set(current.from.x + dx * progress + (distance ? dy / distance : 0) * bow - 4)
    y.set(current.from.y + dy * progress - (distance ? dx / distance : 0) * bow - 3)
    const next = CUES[chapter].find((item) => item.start > cue.start)
    const continuous = Boolean(next)
    opacity.set(
      Math.min(
        current.continuous ? 1 : ease(clamp((time - cue.start) / 260)),
        continuous ? 1 : ease(clamp((cue.end - time) / 340)),
      ),
    )
    const press = time - cue.press
    const down = press >= 0 && press < 130
    if (press >= 0 && lastTap.current !== cue.press) {
      lastTap.current = cue.press
      tapX.set(current.to.x)
      tapY.set(current.to.y)
    }
    scale.set(
      press < 0
        ? 1
        : press < 85
          ? 1 - 0.16 * ease(clamp(press / 85))
          : 0.84 + 0.16 * ease(clamp((press - 85) / 210)),
    )
    fileOpacity.set(cue.drag ? 1 - ease(clamp(press / 260)) : 0)
    current.target.toggleAttribute('data-demo-pressed', down)
  })

  useEffect(
    () => () => {
      track.current?.target.removeAttribute('data-demo-pressed')
    },
    [],
  )

  if (reduce) return null
  return (
    <>
      <motion.div
        aria-hidden
        className="walkthrough-tap pointer-events-none absolute left-0 top-0 z-20 hidden lg:block"
        style={{ x: tapX, y: tapY }}
      >
        <motion.span
          className="absolute -left-3 -top-3 size-6 rounded-full border border-ink"
          style={{ scale: pulseScale, opacity: pulseOpacity }}
        />
        <motion.span
          className="absolute -left-2 -top-2 size-4 rounded-full bg-ink"
          style={{ scale: glowScale, opacity: glowOpacity }}
        />
      </motion.div>
      <motion.div
        aria-hidden
        className="walkthrough-cursor pointer-events-none absolute left-0 top-0 z-20 hidden lg:block"
        style={{ x, y, opacity }}
      >
        <motion.svg
          width="22"
          height="24"
          viewBox="0 0 22 24"
          className="drop-shadow-sm"
          style={{ scale, transformOrigin: '4px 3px' }}
        >
          <path
            d="M4 3 19 11 12 13 9 20Z"
            fill="var(--color-ink)"
            stroke="var(--color-surface)"
            strokeWidth="1.5"
            strokeLinejoin="round"
          />
        </motion.svg>
        <motion.span
          className="absolute left-5 top-5 flex items-center gap-1.5 whitespace-nowrap rounded-lg bg-surface px-2 py-1.5 font-mono text-[10px] text-muted shadow-float ring-1 ring-line"
          style={{ opacity: fileOpacity }}
        >
          <FileText size={12} />6 PDF
        </motion.span>
      </motion.div>
    </>
  )
}
