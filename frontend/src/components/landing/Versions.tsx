import { useState } from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import { StatusBadge } from '../shell/StatusBadge'
import { cn } from '../../lib/cn'

const ease = [0.23, 1, 0.32, 1] as const

type Version = {
  id: string
  state: 'borrador' | 'activa' | 'anterior'
  date: string
  author: string
  motive: string
  changes: { sign: '+' | '~' | '−'; text: string }[]
  impact?: { same: number; changes: number; clashes: number }
  applied?: string
}

const VERSIONS: Version[] = [
  {
    id: 'v4',
    state: 'borrador',
    date: '19 sep',
    author: 'Alberto',
    motive: 'La norma nueva que mandó el banco el sábado.',
    changes: [
      { sign: '+', text: 'El recargo financiero no puede pasar del 2 % de la base.' },
      { sign: '+', text: 'Los pedidos de Guadaira los firma Sonia antes de pagar.' },
      { sign: '~', text: 'El total tiene que cuadrar al céntimo, sin margen.' },
    ],
    impact: { same: 463, changes: 37, clashes: 2 },
  },
  {
    id: 'v3',
    state: 'activa',
    date: '1 sep',
    author: 'Alberto',
    motive: 'Un proveedor mandó la misma factura dos veces y se pagó dos veces.',
    changes: [
      { sign: '+', text: 'Un pedido no se paga dos veces, aunque cambie el número de factura.' },
    ],
    applied: 'Con ella se han decidido las 500 facturas de septiembre.',
  },
  {
    id: 'v2',
    state: 'anterior',
    date: '12 ago',
    author: 'Sonia',
    motive: 'Las facturas simplificadas no traen línea de IVA y se escalaban todas.',
    changes: [{ sign: '~', text: 'Si la factura es simplificada, no se le exige IVA.' }],
    applied: 'Estuvo activa veinte días. 212 facturas decididas.',
  },
  {
    id: 'v1',
    state: 'anterior',
    date: '3 ago',
    author: 'Alberto',
    motive: 'Las seis comprobaciones de siempre, las que hacía a mano.',
    changes: [{ sign: '+', text: 'Proveedor, cuenta, pedido, total, IVA y que no esté pagada.' }],
    applied: 'La primera norma escrita.',
  },
]

export function Versions() {
  const reduce = useReducedMotion()
  const [selectedId, setSelectedId] = useState('v4')
  const selected = VERSIONS.find((version) => version.id === selectedId) ?? VERSIONS[0]

  return (
    <div className="overflow-hidden rounded-[18px] bg-white ring-1 ring-black/[0.06]">
      <div className="grid lg:grid-cols-[minmax(0,24rem)_minmax(0,1fr)]">
        <div className="flex flex-col bg-canvas lg:border-r lg:border-hairline">
          <ol>
            {VERSIONS.map((version) => {
              const active = version.id === selected.id

              return (
                <li key={version.id}>
                  <button
                    type="button"
                    onClick={() => setSelectedId(version.id)}
                    className={cn(
                      'relative w-full border-b border-hairline px-5 py-4 text-left transition-colors',
                      active ? 'bg-white' : 'hover:bg-white/60',
                    )}
                  >
                    {active ? (
                      <motion.span
                        layoutId="version-marker"
                        className="absolute inset-y-0 left-0 w-[2px] bg-ink"
                        transition={reduce ? { duration: 0 } : { duration: 0.3, ease }}
                      />
                    ) : null}

                    <div className="flex items-center gap-2.5">
                      <span className="font-mono text-[14px] tracking-[-0.03em]">{version.id}</span>
                      <StateTag state={version.state} />
                      <span className="ml-auto font-mono text-[11px] text-faint">
                        {version.date}
                      </span>
                    </div>
                    <p
                      className={cn(
                        'mt-2 text-[12.5px] leading-5 transition-colors',
                        active ? 'text-ink' : 'text-muted',
                      )}
                    >
                      {version.motive}
                    </p>
                    <p className="mt-1.5 font-mono text-[10.5px] text-faint">{version.author}</p>
                  </button>
                </li>
              )
            })}
          </ol>

          <p className="mt-auto px-5 py-5 text-[12px] leading-5 text-faint">
            Cuatro versiones desde agosto. No se borra ninguna, y cualquiera se puede volver a
            activar.
          </p>
        </div>

        <div>
          <AnimatePresence mode="wait">
            <motion.div
              key={selected.id}
              initial={reduce ? false : { opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={reduce ? undefined : { opacity: 0, y: -6 }}
              transition={{ duration: 0.26, ease }}
              className="p-6 md:p-7"
            >
              <p className="u-kicker">Qué cambia respecto a la anterior</p>
              <ul className="mt-4">
                {selected.changes.map((change) => (
                  <li
                    key={change.text}
                    className="flex gap-3 border-b border-hairline py-2.5 last:border-0"
                  >
                    <span className="mt-px w-3 shrink-0 font-mono text-[13px] text-faint">
                      {change.sign}
                    </span>
                    <span className="text-[13.5px] leading-6">{change.text}</span>
                  </li>
                ))}
              </ul>

              {selected.impact ? (
                <div className="mt-6 rounded-[14px] bg-canvas p-5">
                  <p className="u-kicker">Antes de activarla, esto es lo que pasaría</p>
                  <div className="mt-4 grid gap-5 sm:grid-cols-3">
                    <Impact value={selected.impact.same} label="decisiones se quedan igual" />
                    <Impact value={selected.impact.changes} label="cambiarían de resultado" />
                    <Impact
                      value={selected.impact.clashes}
                      label="chocan con algo que decidiste tú"
                      warn
                    />
                  </div>
                  <p className="mt-5 max-w-[54ch] text-[12.5px] leading-6 text-muted">
                    Esas dos las tienes que mirar. Mientras no las resuelvas, la v4 se queda en
                    borrador y las facturas siguen decidiéndose con la v3.
                  </p>
                  <div className="mt-5 flex flex-wrap gap-2">
                    <button
                      type="button"
                      className="rounded-full bg-ink px-3.5 py-1.5 text-[12px] font-medium text-white hover:bg-ink/90"
                    >
                      Resolver los 2 choques
                    </button>
                    <button
                      type="button"
                      className="rounded-full bg-white px-3.5 py-1.5 text-[12px] font-medium ring-1 ring-black/[0.06] hover:bg-well"
                    >
                      Ver las 37 facturas
                    </button>
                  </div>
                </div>
              ) : (
                <div className="mt-6 rounded-[14px] bg-canvas p-5">
                  <p className="u-kicker">Su rastro</p>
                  <p className="mt-3 max-w-[46ch] text-[14px] leading-7">{selected.applied}</p>
                  <p className="mt-3 max-w-[54ch] text-[12.5px] leading-6 text-muted">
                    Cada factura recuerda con qué versión se decidió. Cambiar de norma no reescribe
                    lo que ya pasó.
                  </p>
                  {selected.state === 'anterior' ? (
                    <button
                      type="button"
                      className="mt-5 rounded-full bg-white px-3.5 py-1.5 text-[12px] font-medium ring-1 ring-black/[0.06] hover:bg-well"
                    >
                      Volver a esta versión
                    </button>
                  ) : null}
                </div>
              )}
            </motion.div>
          </AnimatePresence>
        </div>
      </div>
    </div>
  )
}

function Impact({ value, label, warn }: { value: number; label: string; warn?: boolean }) {
  return (
    <div>
      <p className={cn('u-figure text-[30px]', warn && 'text-escalar')}>{value}</p>
      <p className="mt-2.5 max-w-[18ch] text-[12.5px] leading-5 text-muted">{label}</p>
    </div>
  )
}

function StateTag({ state }: { state: Version['state'] }) {
  if (state === 'activa') return <StatusBadge value="activa">en uso</StatusBadge>
  if (state === 'borrador') return <StatusBadge value="borrador">borrador</StatusBadge>
  return <StatusBadge value="retirada">anterior</StatusBadge>
}
