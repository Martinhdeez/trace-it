import { useEffect, useState } from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import { RotateCcw } from 'lucide-react'
import { cn } from '../../lib/cn'

const ease = [0.23, 1, 0.32, 1] as const

type Check = {
  label: string
  fails?: boolean
  evidence?: { side: string; value: string; source: string }[]
}

/** Written the way Alberto would say them out loud, not the way the rule compiles. */
const CHECKS: Check[] = [
  { label: 'El proveedor está en tu maestro' },
  { label: 'La cuenta es la que tienes fichada' },
  { label: 'El pedido existe y es de este proveedor' },
  {
    label: 'El total coincide con el pedido',
    fails: true,
    evidence: [
      { side: 'En la factura', value: '6.953,04 €', source: 'línea «Total» del PDF' },
      { side: 'En el pedido', value: '7.100,00 €', source: 'Excel, hoja Pedidos_2026' },
    ],
  },
  { label: 'El IVA cuadra con la base' },
  { label: 'Nadie la ha pagado ya' },
]

const LAST = CHECKS.length + 1

export function DecisionLoop() {
  const reduce = useReducedMotion()
  const [step, setStep] = useState(0)
  const shown = reduce ? LAST : step

  useEffect(() => {
    if (reduce) return
    const hold = step === LAST ? 4200 : step === 0 ? 900 : 480
    const id = setTimeout(() => setStep((current) => (current >= LAST ? 0 : current + 1)), hold)
    return () => clearTimeout(id)
  }, [reduce, step])

  const decided = shown >= LAST

  return (
    <figure className="relative m-0">
      {/* Two sheets peeking out behind: it is one of five hundred. */}
      <div
        className="absolute inset-x-4 -top-2 h-5 rounded-t-[16px] bg-white ring-1 ring-black/[0.05]"
        aria-hidden
      />
      <div
        className="absolute inset-x-2 -top-1 h-5 rounded-t-[17px] bg-white ring-1 ring-black/[0.06]"
        aria-hidden
      />

      <div className="relative overflow-hidden rounded-[18px] bg-white shadow-[0_1px_2px_rgba(19,19,19,0.04),0_18px_50px_rgba(19,19,19,0.07)] ring-1 ring-black/[0.06]">
        <div className="relative flex items-center justify-between gap-3 border-b border-hairline px-4 py-2.5">
          <span className="font-mono text-[12px]">factura_5518.pdf</span>
          <span className="font-mono text-[11px] text-faint">Ofimática Cieza · 6.953,04 €</span>
          {!decided ? (
            <motion.span
              key={step}
              className="absolute inset-x-0 bottom-[-1px] h-[2px] origin-left bg-ink/20"
              initial={{ scaleX: shown / LAST }}
              animate={{ scaleX: (shown + 1) / LAST }}
              transition={{ duration: 0.45, ease }}
            />
          ) : null}
        </div>

        <ul className="px-4 py-1">
          {CHECKS.map((check, index) => {
            const revealed = shown > index
            const failed = revealed && check.fails

            return (
              <li key={check.label} className="border-b border-hairline py-2 last:border-0">
                <div className="flex items-center gap-2.5">
                  <Mark state={!revealed ? 'pending' : check.fails ? 'fail' : 'pass'} />
                  <span
                    className={cn(
                      'flex-1 text-[12.5px] transition-colors duration-300',
                      revealed ? 'text-ink' : 'text-faint',
                    )}
                  >
                    {check.label}
                  </span>
                  <span
                    className={cn(
                      'shrink-0 rounded-full px-1.5 py-0.5 font-mono text-[10px]',
                      failed ? 'bg-nopagar-soft text-nopagar' : 'text-faint',
                    )}
                  >
                    {revealed ? (failed ? 'no cuadra' : 'ok') : null}
                  </span>
                </div>

                <AnimatePresence initial={false}>
                  {failed && check.evidence ? (
                    <motion.div
                      initial={reduce ? false : { height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      transition={{ duration: 0.34, ease }}
                      className="overflow-hidden"
                    >
                      <div className="mt-2 grid gap-2 sm:grid-cols-2">
                        {check.evidence.map((item) => (
                          <div key={item.side} className="rounded-[12px] bg-nopagar-soft px-3 py-2">
                            <p className="text-[11px] text-muted">{item.side}</p>
                            <p className="mt-0.5 font-mono text-[13.5px] text-ink">{item.value}</p>
                            <p className="mt-0.5 text-[10.5px] text-faint">{item.source}</p>
                          </div>
                        ))}
                      </div>
                    </motion.div>
                  ) : null}
                </AnimatePresence>
              </li>
            )
          })}
        </ul>

        <div className="relative min-h-[128px] border-t border-hairline px-4 py-4">
          <AnimatePresence mode="wait">
            {decided ? (
              <motion.div
                key="decided"
                initial={reduce ? false : { opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.2 }}
              >
                <motion.p
                  className="u-display text-[30px] text-nopagar"
                  initial={reduce ? false : { y: 6, opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  transition={{ duration: 0.4, ease }}
                >
                  NO PAGAR
                </motion.p>
                <p className="mt-2.5 max-w-[42ch] text-[13px] leading-6 text-ink">
                  El total de la factura no coincide con el del pedido. Faltan 146,96 € por
                  explicar, así que no sale del banco.
                </p>
                <p className="mt-2 max-w-[42ch] text-[12.5px] leading-6 text-muted">
                  Ofimática Cieza queda avisada. Si llega el pedido corregido, la factura se vuelve
                  a decidir.
                </p>
              </motion.div>
            ) : (
              <motion.div
                key="working"
                initial={reduce ? false : { opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="flex h-full items-center"
              >
                <p className="text-[13px] text-muted">
                  Pasando la factura por las seis reglas de tu norma…
                </p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <div className="flex items-center justify-between gap-3 border-t border-hairline bg-canvas px-4 py-2.5">
          <span className="font-mono text-[10.5px] text-faint">
            norma v3 · 0,18 s · queda guardado el porqué
          </span>
          <button
            type="button"
            onClick={() => setStep(0)}
            className="inline-flex items-center gap-1.5 rounded-full px-2 py-1 text-[11.5px] text-muted hover:text-ink"
          >
            <RotateCcw size={11} strokeWidth={2} />
            Verlo otra vez
          </button>
        </div>
      </div>

      <figcaption className="mt-3 text-[12px] text-faint">
        Una factura del lote de septiembre.
      </figcaption>
    </figure>
  )
}

function Mark({ state }: { state: 'pending' | 'pass' | 'fail' }) {
  if (state === 'pending') {
    return <span className="h-3.5 w-3.5 shrink-0 rounded-full ring-1 ring-black/[0.08]" />
  }

  return (
    <span
      className={cn(
        'grid h-3.5 w-3.5 shrink-0 place-items-center rounded-full',
        state === 'fail' ? 'bg-nopagar text-white' : 'bg-pagar text-white',
      )}
    >
      <svg viewBox="0 0 12 12" className="h-2.5 w-2.5" fill="none">
        <motion.path
          d={state === 'fail' ? 'M3.4 3.4 L8.6 8.6 M8.6 3.4 L3.4 8.6' : 'M2.6 6.4 L4.9 8.7 L9.4 3.4'}
          stroke="currentColor"
          strokeWidth={1.8}
          strokeLinecap="round"
          initial={{ pathLength: 0 }}
          animate={{ pathLength: 1 }}
          transition={{ duration: 0.26, ease }}
        />
      </svg>
    </span>
  )
}
