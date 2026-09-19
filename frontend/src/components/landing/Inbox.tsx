import { useState } from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import { StatusBadge } from '../shell/StatusBadge'
import { cn } from '../../lib/cn'

const ease = [0.23, 1, 0.32, 1] as const

type Case = {
  file: string
  who: string
  amount: string
  why: string
  proposal: string
  tone: 'RECHAZAR' | 'ESCALAR' | 'APROBAR'
  reasoning: string
  rule: string
}

const CASES: Case[] = [
  {
    file: 'factura_0412.pdf',
    who: 'Talleres Guadaira',
    amount: '12.874,40 €',
    why: 'El pedido que cita la factura no aparece en el Excel.',
    proposal: 'No pagar',
    tone: 'RECHAZAR',
    reasoning:
      'El pedido PO-2026-0018 no existe en la hoja de pedidos y el proveedor tampoco lo tiene en el ERP. Sin pedido no hay nada con lo que comparar el importe.',
    rule: 'Si el pedido de la factura no está en el Excel, no se paga.',
  },
  {
    file: 'scan_017.pdf',
    who: 'Ofimática Cieza',
    amount: '2.310,00 €',
    why: 'Es un escaneo y los dos lectores no leen el mismo importe.',
    proposal: 'Escalar',
    tone: 'ESCALAR',
    reasoning:
      'Un lector ve 2.310,00 € y el otro 2.810,00 €. Con un dato en duda no se decide: el papel tiene una mancha justo encima de la cifra.',
    rule: 'Si dos lecturas del mismo importe no coinciden, lo mira una persona.',
  },
  {
    file: 'copia_2026_0518.pdf',
    who: 'Suministros Almanzora',
    amount: '890,15 €',
    why: 'Dice «copia» y el original ya se pagó en mayo.',
    proposal: 'No pagar',
    tone: 'RECHAZAR',
    reasoning: 'El pedido PO-2026-0301 está como PAGADA en el ERP desde el 18 de mayo.',
    rule: 'Un pedido ya pagado en el ERP no se vuelve a pagar, aunque cambie el número de factura.',
  },
  {
    file: 'FA-2291_limpieza.pdf',
    who: 'Limpiezas Serrano',
    amount: '1.452,00 €',
    why: 'Factura simplificada sin línea de IVA.',
    proposal: 'Pagar',
    tone: 'APROBAR',
    reasoning:
      'El total coincide con el pedido y el proveedor es de los de siempre. La norma pide IVA, pero en una simplificada no viene, y no hay que inventarlo.',
    rule: 'Si la factura es simplificada, no se le exige línea de IVA.',
  },
]

export function Inbox() {
  const reduce = useReducedMotion()
  const [openIndex, setOpenIndex] = useState(0)

  return (
    <div className="overflow-hidden rounded-[18px] bg-white ring-1 ring-black/[0.06]">
      <div className="flex items-center justify-between border-b border-hairline px-5 py-3">
        <span className="text-[13px] font-medium">Tu bandeja</span>
        <span className="font-mono text-[11px] text-faint">
          4 de 500 · el resto ya está decidido
        </span>
      </div>

      <ul>
        {CASES.map((item, index) => {
          const open = index === openIndex

          return (
            <li key={item.file} className="border-b border-hairline last:border-0">
              <button
                type="button"
                onClick={() => setOpenIndex(open ? -1 : index)}
                className={cn(
                  'flex w-full items-center gap-3 px-5 py-3 text-left transition-colors',
                  open ? 'bg-canvas' : 'hover:bg-canvas/70',
                )}
              >
                <span className="font-mono text-[12px]">{item.file}</span>
                <span className="truncate text-[12.5px] text-muted">{item.who}</span>
                <span className="ml-auto shrink-0 font-mono text-[12px] tabular-nums">
                  {item.amount}
                </span>
              </button>

              <AnimatePresence initial={false}>
                {open ? (
                  <motion.div
                    initial={reduce ? false : { height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={reduce ? undefined : { height: 0, opacity: 0 }}
                    transition={{ duration: 0.3, ease }}
                    className="overflow-hidden bg-canvas"
                  >
                    <div className="border-t border-hairline px-5 py-4">
                      <p className="text-[13px] leading-6">
                        <span className="text-muted">Por qué te llega: </span>
                        {item.why}
                      </p>

                      <div className="mt-3 rounded-[14px] bg-white p-4 ring-1 ring-black/[0.06]">
                        <div className="flex items-center gap-2.5">
                          <p className="u-kicker">Lo que propone</p>
                          <StatusBadge value={item.tone}>{item.proposal}</StatusBadge>
                        </div>
                        <p className="mt-2.5 max-w-[56ch] text-[12.5px] leading-6 text-muted">
                          {item.reasoning}
                        </p>
                        <p className="mt-3 max-w-[56ch] rounded-[10px] bg-canvas px-3 py-2 text-[12.5px] leading-6">
                          Regla para que no vuelva a subir: «{item.rule}»
                        </p>
                      </div>

                      <div className="mt-3 flex flex-wrap gap-2">
                        <span className="rounded-full bg-ink px-3.5 py-1.5 text-[12px] font-medium text-white">
                          Acepto y añade la regla
                        </span>
                        <span className="rounded-full bg-white px-3.5 py-1.5 text-[12px] font-medium ring-1 ring-black/[0.06]">
                          Decido yo
                        </span>
                      </div>
                    </div>
                  </motion.div>
                ) : null}
              </AnimatePresence>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
