import { useEffect, useRef, type ReactNode } from 'react'
import { motion } from 'motion/react'

const ease = [0.23, 1, 0.32, 1] as const

/** Open overlays, innermost last: Escape closes only the one on top. */
const stack: symbol[] = []

export function Overlay({
  onClose,
  children,
  align = 'center',
  size = 'md',
}: {
  onClose: () => void
  children: ReactNode
  align?: 'center' | 'right'
  size?: 'md' | 'lg' | 'xl'
}) {
  const close = useRef(onClose)
  useEffect(() => {
    close.current = onClose
  })
  useEffect(() => {
    const id = Symbol('overlay')
    stack.push(id)
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && stack.at(-1) === id) close.current()
    }
    window.addEventListener('keydown', onKey)
    return () => {
      window.removeEventListener('keydown', onKey)
      stack.splice(stack.indexOf(id), 1)
    }
  }, [])

  return (
    <div
      className={
        align === 'right'
          ? 'fixed inset-0 z-50 flex justify-end bg-scrim p-3'
          : 'fixed inset-0 z-50 grid place-items-center bg-scrim p-4'
      }
      onClick={onClose}
    >
      <motion.div
        initial={
          align === 'right'
            ? { x: 24, opacity: 0.6 }
            : { y: 8, opacity: 0, scale: 0.98 }
        }
        animate={{ x: 0, y: 0, opacity: 1, scale: 1 }}
        transition={{ duration: 0.22, ease }}
        className={
          align === 'right'
            ? size === 'xl'
              ? 'h-full w-full max-w-[1280px]'
              : size === 'lg'
              ? 'h-full w-full max-w-2xl'
              : 'h-full w-full max-w-md'
            : size === 'xl'
              ? 'h-[min(88dvh,860px)] min-w-0 w-full max-w-[1100px]'
              : size === 'lg'
                ? 'w-full max-w-3xl'
                : 'w-full max-w-lg'
        }
        onClick={(event) => event.stopPropagation()}
      >
        {children}
      </motion.div>
    </div>
  )
}
