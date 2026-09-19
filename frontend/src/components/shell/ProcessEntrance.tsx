import { useEffect, useState, type ReactNode } from 'react'
import { useLocation } from 'react-router'
import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import mark from '../../assets/trace-mark-clear.png'
import { t } from '../../i18n'
import { paths } from '../../lib/paths'

/** A fresh visit starts the pitch; returning from a process keeps the console open. */
export function ProcessEntrance({ children }: { children: ReactNode }) {
  const { pathname } = useLocation()
  const [step, setStep] = useState(() => pathname.replace(/\/$/, '') === paths.processes ? 0 : 2)
  const reduceMotion = useReducedMotion()
  const presenting = step < 2 && pathname.replace(/\/$/, '') === paths.processes

  useEffect(() => {
    if (!presenting) return
    const onKey = (event: KeyboardEvent) => {
      if (event.altKey || event.ctrlKey || event.metaKey) return
      if (!['ArrowRight', 'Enter', ' '].includes(event.key)) return
      event.preventDefault()
      if (!event.repeat) setStep((current) => Math.min(current + 1, 2))
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [presenting])

  return (
    <AnimatePresence initial={false} mode="wait">
      {presenting ? (
        <motion.button
          key="entrance"
          type="button"
          aria-label={t(step === 0 ? 'pitch.showLogo' : 'pitch.openProcesses')}
          onClick={() => setStep((current) => Math.min(current + 1, 2))}
          exit={{ opacity: 0 }}
          transition={{ duration: reduceMotion ? 0 : 0.25 }}
          className="fixed inset-0 z-[100] flex h-dvh w-full cursor-pointer items-center justify-center bg-white p-6 text-[#131313] active:scale-100 focus-visible:-outline-offset-4"
        >
          {step === 1 ? (
            <motion.span
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: reduceMotion ? 0 : 0.4 }}
              className="flex items-center gap-4 sm:gap-6"
            >
              <img src={mark} alt="" draggable={false} className="h-16 w-16 shrink-0 select-none object-contain sm:h-28 sm:w-28" />
              <span className="text-[40px] font-medium leading-none tracking-[-0.05em] sm:text-[72px]">
                trace<span className="text-[#a3a29c]">[.]</span>it
              </span>
            </motion.span>
          ) : null}
        </motion.button>
      ) : (
        <motion.div
          key="console"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: reduceMotion ? 0 : 0.3 }}
        >
          {children}
        </motion.div>
      )}
    </AnimatePresence>
  )
}
