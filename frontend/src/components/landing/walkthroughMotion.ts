import { useState } from 'react'
import { useMotionValueEvent, useTransform, type MotionValue } from 'motion/react'

/** React only renders when a visible state changes, never on each animation frame. */
function useDiscreteValue(value: MotionValue<number>) {
  const [current, setCurrent] = useState(() => value.get())
  useMotionValueEvent(value, 'change', setCurrent)
  return current
}

export function useBeat(clock: MotionValue<number>, interval: number, limit: number, offset = 0) {
  return useDiscreteValue(
    useTransform(clock, (time) =>
      Math.min(limit, Math.max(0, Math.floor((time - offset) / interval))),
    ),
  )
}

export function useStep(clock: MotionValue<number>, times: readonly number[]) {
  return useDiscreteValue(useTransform(clock, (time) => times.filter((at) => time >= at).length))
}
