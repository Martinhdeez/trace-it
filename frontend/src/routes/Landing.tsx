import { motion, useReducedMotion } from 'motion/react'
import { ArrowRight } from 'lucide-react'
import {
  Band,
  Colophon,
  Kicker,
  Masthead,
  PrimaryAction,
  Rise,
  SecondaryAction,
  SectionHead,
  Sheet,
} from '../components/landing/Chrome'
import { DecisionLoop } from '../components/landing/DecisionLoop'
import { Inbox } from '../components/landing/Inbox'
import { Versions } from '../components/landing/Versions'
import { paths } from '../lib/paths'

/**
 * Written for the person who answers for the payments, not for the one who
 * reads the code. Nothing on this page appears only after a scroll observer
 * fires: motion moves things that are already there.
 */
export function Landing() {
  return (
    <div className="bg-canvas">
      <Masthead />
      <main>
        <Opening />
        <HowItWorks />
        <Desk />
        <RuleVersions />
        <WhoDecides />
        <Closing />
      </main>
      <Colophon />
    </div>
  )
}

const ease = [0.23, 1, 0.32, 1] as const

function Opening() {
  const reduce = useReducedMotion()
  const enter = (delay: number) =>
    reduce
      ? {}
      : {
          initial: { opacity: 0, y: 12 },
          animate: { opacity: 1, y: 0 },
          transition: { duration: 0.6, delay, ease },
        }

  return (
    <section>
      <Sheet className="grid gap-x-12 gap-y-12 pb-16 pt-16 md:pt-20 lg:grid-cols-[minmax(0,1fr)_minmax(0,27rem)] lg:items-center">
        <div>
          <motion.div {...enter(0)}>
            <Kicker>Pago de facturas</Kicker>
          </motion.div>

          <motion.h1
            className="u-display mt-5 max-w-[18ch] text-[clamp(38px,4.8vw,62px)]"
            {...enter(0.06)}
          >
            Tú escribes las reglas. El programa decide las facturas.
          </motion.h1>

          <motion.p className="mt-6 max-w-[52ch] text-[16px] leading-7 text-muted" {...enter(0.14)}>
            Cada decisión guarda qué regla se aplicó, con qué dato y de dónde salió ese dato. Lo que
            no cuadra se queda en tu bandeja y no sale del banco.
          </motion.p>

          <motion.div className="mt-8 flex flex-wrap items-center gap-3" {...enter(0.2)}>
            <PrimaryAction to={paths.processes}>
              Abrir la consola
              <ArrowRight size={15} strokeWidth={2} />
            </PrimaryAction>
            <SecondaryAction href="#como-funciona">Cómo funciona</SecondaryAction>
          </motion.div>

          <motion.p className="mt-6 max-w-[46ch] text-[12.5px] leading-6 text-faint" {...enter(0.26)}>
            No cambia tu ERP ni tu Excel. Lee los PDF que ya te llegan y los cruza con los datos que
            ya tienes.
          </motion.p>
        </div>

        <motion.div
          initial={reduce ? false : { opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.16, ease }}
        >
          <DecisionLoop />
        </motion.div>
      </Sheet>
    </section>
  )
}

const STEPS = [
  {
    title: 'Escribes la regla en una frase',
    body: '«El total de la factura tiene que coincidir con el del pedido.» Sin fórmulas, sin nombres de campo y sin esperar a un informático.',
    aside: 'una frase por regla',
  },
  {
    title: 'Todas las facturas pasan por todas las reglas',
    body: 'En el mismo orden, siempre. Diez facturas o diez mil dan el mismo resultado, y el resultado se lee regla por regla.',
    aside: 'sin excepciones',
  },
  {
    title: 'Lo que no cuadra sube a tu bandeja',
    body: 'Con la decisión que propone, el motivo, y la regla que evitaría el próximo caso igual. Si aceptas la regla, ese caso ya no vuelve a subir.',
    aside: 'y la norma crece',
  },
]

function HowItWorks() {
  return (
    <Band id="como-funciona" tone="sheet">
      <Sheet className="py-16">
        <SectionHead
          kicker="Cómo funciona"
          title="Tres pasos tuyos. El resto está hecho cuando llegas."
          lead="El modelo escribe las comprobaciones y explica los casos raros. Aplicarlas es cosa del programa, que hace lo mismo cada vez."
        />

        <ol className="mt-10">
          {STEPS.map((step, index) => (
            <li key={step.title} className="border-t border-hairline last:border-b">
              <Rise delay={index * 0.05}>
                <div className="grid gap-x-8 gap-y-2 py-6 md:grid-cols-[3rem_minmax(0,24ch)_minmax(0,1fr)_9rem]">
                  <span className="font-mono text-[12px] tabular-nums text-faint">
                    {String(index + 1).padStart(2, '0')}
                  </span>
                  <h3 className="max-w-[22ch] text-[15px] font-medium tracking-[-0.02em]">
                    {step.title}
                  </h3>
                  <p className="max-w-[60ch] text-[14px] leading-6 text-muted">{step.body}</p>
                  <span className="font-mono text-[11px] text-faint md:text-right">
                    {step.aside}
                  </span>
                </div>
              </Rise>
            </li>
          ))}
        </ol>
      </Sheet>
    </Band>
  )
}

function Desk() {
  return (
    <Band id="bandeja">
      <Sheet className="py-16">
        <div className="grid gap-x-12 gap-y-10 lg:grid-cols-[minmax(0,1fr)_minmax(0,33rem)] lg:items-start">
          <div className="lg:sticky lg:top-24">
            <Kicker>Tu bandeja</Kicker>
            <h2 className="u-display mt-4 max-w-[20ch] text-[clamp(28px,3.4vw,40px)]">
              Solo revisas lo que el programa no puede cerrar.
            </h2>
            <p className="mt-5 max-w-[46ch] text-[15px] leading-7 text-muted">
              De cada caso ves lo que propone, por qué, y la regla que lo resolvería para siempre.
              Aceptas la regla o decides tú. En los dos casos la norma se queda con una regla más.
            </p>
          </div>

          <Rise>
            <Inbox />
          </Rise>
        </div>
      </Sheet>
    </Band>
  )
}

function RuleVersions() {
  return (
    <Band id="versiones" tone="sheet">
      <Sheet className="py-16">
        <SectionHead
          kicker="La norma cambia"
          title="Cuando cambia la norma, cambias de versión."
          lead="Cada cambio queda con su fecha, quién lo hizo y por qué. Antes de activarlo ves a cuántas decisiones pasadas afectaría, y puedes volver a la versión anterior."
        />

        <Rise className="mt-10">
          <Versions />
        </Rise>

        <p className="mt-8 max-w-[62ch] text-[15px] leading-7">
          Si una regla nueva dice que una factura de marzo no se debió pagar, te avisa y te deja la
          lista. No reescribe el pasado por su cuenta. Reclamar ese dinero, o dejarlo, lo decides
          tú.
        </p>
      </Sheet>
    </Band>
  )
}

function WhoDecides() {
  return (
    <Band>
      <Sheet className="py-16">
        <SectionHead
          kicker="Quién decide"
          title="El modelo no firma tus pagos."
          lead="El modelo escribe las comprobaciones y redacta las explicaciones. Quien las aplica es el programa, con las reglas que tú has aprobado."
        />

        <Rise className="mt-10">
          <div className="grid max-w-[62ch] gap-4 text-[15px] leading-7">
            <p>
              Cada documento se lee dos veces con lectores independientes. Si las dos lecturas no
              coinciden, el caso sube a tu bandeja en lugar de decidirse.
            </p>
            <p>
              Si mañana se cae el proveedor del modelo, las facturas se siguen decidiendo con las
              reglas que ya están escritas. Lo único que se para es escribir reglas nuevas.
            </p>
          </div>
        </Rise>
      </Sheet>
    </Band>
  )
}

function Closing() {
  return (
    <Band tone="sheet">
      <Sheet className="py-20">
        <h2 className="u-display max-w-[20ch] text-[clamp(32px,4vw,48px)]">
          Abre una factura y mira qué regla la decidió.
        </h2>
        <p className="mt-6 max-w-[52ch] text-[16px] leading-7 text-muted">
          Las 500 facturas de septiembre vienen cargadas. Escribe una regla nueva y comprueba, antes
          de activarla, a qué decisiones pasadas afectaría.
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <PrimaryAction to={paths.processes}>
            Abrir la consola
            <ArrowRight size={15} strokeWidth={2} />
          </PrimaryAction>
          <SecondaryAction to={paths.newProcess}>Empezar un proceso nuevo</SecondaryAction>
        </div>
      </Sheet>
    </Band>
  )
}
