import { useEffect, type ReactNode } from 'react'
import { motion } from 'motion/react'

const ease = [0.23, 1, 0.32, 1] as const

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
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div
      className={
        align === 'right'
          ? 'fixed inset-0 z-50 flex justify-end bg-ink/20 p-3'
          : 'fixed inset-0 z-50 grid place-items-center bg-ink/20 p-4'
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
            ? 'h-full w-full max-w-md'
            : size === 'xl'
              ? 'h-[min(88dvh,860px)] w-full max-w-[1100px]'
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
