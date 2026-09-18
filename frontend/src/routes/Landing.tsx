import type { ReactNode } from 'react'
import { Link } from 'react-router'
import { motion, useReducedMotion } from 'motion/react'
import { ArrowRight } from 'lucide-react'
import mark from '../assets/trace-mark.png'
import { cn } from '../lib/cn'
import { paths } from '../lib/paths'

const ease = [0.23, 1, 0.32, 1] as const

export function Landing() {
  return (
    <div className="bg-canvas">
      <Header />
      <main>
        <Opening />
        <Chain />
        <TwoAgents />
        <Figures />
        <NotAboutInvoices />
        <Closing />
      </main>
      <Footer />
    </div>
  )
}

function Header() {
  return (
    <header className="sticky top-0 z-30 border-b border-hairline bg-canvas/85 backdrop-blur-md">
      <div className="mx-auto flex h-14 max-w-[1080px] items-center justify-between px-6">
        <Link to={paths.landing} className="flex items-center gap-2">
          <img src={mark} alt="" className="h-6 w-6 rounded-[6px] object-cover" draggable={false} />
          <span className="text-[14px] font-medium tracking-[-0.03em]">
            trace<span className="text-faint">[.]</span>it
          </span>
        </Link>
        <nav className="flex items-center gap-1 text-[13px]">
          <a href="#cadena" className="rounded-full px-3 py-1.5 text-muted hover:text-ink">
            Cómo decide
          </a>
          <a href="#norma" className="rounded-full px-3 py-1.5 text-muted hover:text-ink">
            La norma
          </a>
          <a href="#procesos" className="rounded-full px-3 py-1.5 text-muted hover:text-ink">
            Otros procesos
          </a>
          <Link
            to={paths.processes}
            className="ml-2 inline-flex items-center gap-1.5 rounded-full bg-ink px-3.5 py-1.5 text-[13px] font-medium text-white hover:bg-ink/90"
          >
            Abrir la consola
            <ArrowRight size={13} strokeWidth={2} />
          </Link>
        </nav>
      </div>
    </header>
  )
}

function Reveal({ children, delay = 0 }: { children: ReactNode; delay?: number }) {
  const reduce = useReducedMotion()
  if (reduce) return <>{children}</>
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-60px' }}
      transition={{ duration: 0.5, ease, delay }}
    >
      {children}
    </motion.div>
  )
}

function Opening() {
  return (
    <section className="mx-auto max-w-[1080px] px-6 pb-14 pt-20">
      <div className="grid gap-10 lg:grid-cols-[minmax(0,1fr)_380px] lg:items-end">
        <div>
          <p className="font-mono text-[11px] tracking-[0.14em] text-faint">
            PROCESOS DE DECISIÓN
          </p>
          <h1 className="mt-4 max-w-[19ch] text-[54px] font-medium leading-[0.98] tracking-[-0.05em] sm:text-[68px]">
            Cada decisión trae su porqué al lado.
          </h1>
          <p className="mt-6 max-w-[54ch] text-[16px] leading-7 text-muted">
            Escribes la norma en castellano. Dos agentes la compilan por separado a funciones de
            Python y se cruzan los tests. A partir de ahí decide el código, nunca un modelo. Queda
            registrado qué regla saltó, con qué dato, sacado de dónde y con qué versión de la
            norma.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-3">
            <Link
              to={paths.processes}
              className="inline-flex items-center gap-2 rounded-full bg-ink px-5 py-2.5 text-[14px] font-medium text-white hover:bg-ink/90"
            >
              Abrir la consola
              <ArrowRight size={15} strokeWidth={2} />
            </Link>
            <a
              href="#cadena"
              className="inline-flex items-center rounded-full bg-white px-5 py-2.5 text-[14px] text-ink ring-1 ring-black/[0.07] hover:bg-well"
            >
              Ver una decisión entera
            </a>
          </div>
        </div>

        <Reveal delay={0.1}>
          <DecisionCard />
        </Reveal>
      </div>
    </section>
  )
}

/**
 * The same thing the console shows on the right of an instance, rendered here
 * with real data from lote 1. A product shot made of DOM, not a picture.
 */
function DecisionCard() {
  const rules = [
    { text: 'NIF del emisor en el maestro', fires: false },
    { text: 'IBAN igual al del maestro', fires: false },
    { text: 'El pedido existe y es suyo', fires: false },
    { text: 'Total = importe del pedido ±0,01', fires: true, reason: 'IMPORTE_DISTINTO' },
    { text: 'Base + IVA = total ±0,01', fires: false },
    { text: 'El ERP dice PAGADA', fires: false },
  ]

  return (
    <div className="overflow-hidden rounded-[18px] bg-white shadow-[0_1px_2px_rgba(19,19,19,0.04),0_18px_50px_rgba(19,19,19,0.07)] ring-1 ring-black/[0.06]">
      <div className="flex items-center justify-between border-b border-hairline px-4 py-2.5">
        <span className="font-mono text-[12px]">factura_5518.pdf</span>
        <span className="font-mono text-[10px] text-faint">184 ms</span>
      </div>

      <div className="px-4 py-4">
        <p className="font-mono text-[11px] text-muted">IMPORTE_DISTINTO</p>
        <p className="mt-1.5 text-[30px] font-medium leading-none tracking-[-0.045em] text-nopagar">
          NO PAGAR
        </p>
        <p className="mt-2 font-mono text-[11px] text-faint">motor · 7f3c9a21e480</p>
      </div>

      <ul className="border-t border-hairline">
        {rules.map((rule) => (
          <li
            key={rule.text}
            className="flex items-baseline justify-between gap-3 border-b border-hairline px-4 py-[7px] last:border-0"
          >
            <span className="min-w-0 truncate text-[12px] text-ink">{rule.text}</span>
            <span
              className={cn(
                'shrink-0 rounded-full px-1.5 py-0.5 font-mono text-[10px]',
                rule.fires ? 'bg-nopagar-soft text-nopagar' : 'text-faint',
              )}
            >
              {rule.fires ? 'salta' : 'ok'}
            </span>
          </li>
        ))}
      </ul>

      <div className="border-t border-hairline bg-[#161615] px-4 py-3 font-mono text-[11px] leading-5">
        <span className="text-[#8cb4ff]">"total"</span>
        <span className="text-[#d4d0c8]">: </span>
        <span className="text-[#e08b7a]">6953.04</span>
        <span className="text-[#73726c]">  factura, texto</span>
        <br />
        <span className="text-[#8cb4ff]">"importe_total"</span>
        <span className="text-[#d4d0c8]">: </span>
        <span className="text-[#e08b7a]">7100.00</span>
        <span className="text-[#73726c]">  pedidos, Excel</span>
      </div>
    </div>
  )
}

const STEPS = [
  {
    title: 'Entra un documento',
    detail:
      'Se guarda tal cual y se identifica por el hash de su contenido. El mismo fichero dos veces no se procesa dos veces.',
    note: 'sha256',
  },
  {
    title: 'Dos extracciones, no una',
    detail:
      'Dos modelos de proveedores distintos leen los símbolos por su cuenta. Si no coinciden, la instancia se queda en REVISION y nadie decide con un dato sin verificar.',
    note: 'extractor_1 · extractor_2',
  },
  {
    title: 'Decide el código',
    detail:
      'Se ejecutan todas las reglas activas, nadie elige cuáles. Si no salta ninguna, sale la decisión por defecto. Si saltan varias, gana la de mayor prioridad.',
    note: 'sin LLM',
  },
  {
    title: 'Lo que no cierra, a una persona',
    detail:
      'Las salidas marcadas como «requiere persona» van a una cola. El asistente propone decisión, razonamiento y la regla que cerraría los casos parecidos. Decide el responsable.',
    note: 'cola',
  },
  {
    title: 'La norma cambia sin romper el pasado',
    detail:
      'Antes de activar una regla se reejecuta sobre los símbolos guardados de todas las decisiones. Si contradice algo que decidió una persona, no entra.',
    note: 'auditoría',
  },
]

function Chain() {
  return (
    <section id="cadena" className="border-y border-hairline bg-shell">
      <div className="mx-auto max-w-[1080px] px-6 py-16">
        <SectionHead
          kicker="LA CADENA"
          title="Del PDF a la línea del JSONL, paso a paso"
          lead="Cinco pasos. Cada uno deja un evento con su latencia, sus reintentos y su coste, así que se puede seguir una factura concreta de principio a fin."
        />

        <ol className="mt-10">
          {STEPS.map((step, index) => (
            <li key={step.title} className="border-t border-hairline last:border-b">
              <Reveal delay={index * 0.04}>
                <div className="grid gap-x-6 gap-y-1 py-5 sm:grid-cols-[3rem_minmax(0,22ch)_minmax(0,1fr)_8rem]">
                  <span className="font-mono text-[12px] tabular-nums text-faint">
                    {String(index + 1).padStart(2, '0')}
                  </span>
                  <h3 className="text-[15px] font-medium tracking-[-0.02em]">{step.title}</h3>
                  <p className="text-[14px] leading-6 text-muted">{step.detail}</p>
                  <span className="font-mono text-[11px] text-faint sm:text-right">
                    {step.note}
                  </span>
                </div>
              </Reveal>
            </li>
          ))}
        </ol>
      </div>
    </section>
  )
}

const CODE_A = `def evaluar(instancia, fuentes, otras):
    pedido = buscar(fuentes["pedidos"],
                    instancia["pedido"])
    if pedido is None:
        return {"salta": False, "motivo": "OK"}
    diferencia = abs(
        centimos(instancia["total"])
        - centimos(pedido["importe_total"]))
    return {"salta": diferencia > 1,
            "motivo": "IMPORTE_DISTINTO"}`

const CODE_B = `def evaluar(instancia, fuentes, otras):
    clave = norm(instancia.get("pedido"))
    fila = next((p for p in fuentes["pedidos"]
                 if norm(p["pedido"]) == clave), None)
    if fila is None or instancia.get("total") is None:
        return {"salta": False, "motivo": "OK"}
    a = Decimal(str(instancia["total"]))
    b = Decimal(str(fila["importe_total"]))
    salta = abs(a - b) > Decimal("0.01")
    return {"salta": salta, "motivo": "IMPORTE_DISTINTO"}`

function TwoAgents() {
  return (
    <section id="norma" className="mx-auto max-w-[1080px] px-6 py-16">
      <SectionHead
        kicker="LA NORMA"
        title="Una regla en una frase. Dos códigos que tienen que estar de acuerdo."
        lead="Cada agente ve el texto de la regla y nada más: ni el código del otro, ni sus tests. Después todos los tests pasan por los dos códigos, y los dos corren el histórico entero. Si discrepan una sola vez, la regla se queda en borrador."
      />

      <div className="mt-8 overflow-hidden rounded-[18px] bg-white ring-1 ring-black/[0.06]">
        <div className="border-b border-hairline px-5 py-4">
          <p className="font-mono text-[11px] tracking-[0.12em] text-faint">REGLA · REQUISITO</p>
          <p className="mt-1.5 text-[16px] tracking-[-0.02em]">
            El total de la factura coincide con el importe del pedido, con 0,01 € de margen.
          </p>
        </div>

        <div className="grid divide-y divide-hairline md:grid-cols-2 md:divide-x md:divide-y-0">
          <CodePane role="compilador_a" model="anthropic/claude-opus-5" code={CODE_A} />
          <CodePane role="compilador_b" model="openai/gpt-5" code={CODE_B} />
        </div>

        <div className="flex flex-wrap items-center gap-x-6 gap-y-2 border-t border-hairline px-5 py-3.5">
          <Check label="12 / 12 tests cruzados" />
          <Check label="500 / 500 instancias del histórico" />
          <Check label="Lista para que el responsable la active" />
        </div>
      </div>
    </section>
  )
}

function CodePane({ role, model, code }: { role: string; model: string; code: string }) {
  return (
    <div>
      <div className="flex items-baseline justify-between px-5 pb-2 pt-4">
        <span className="font-mono text-[11px] text-ink">{role}</span>
        <span className="font-mono text-[10.5px] text-faint">{model}</span>
      </div>
      <pre className="overflow-x-auto px-5 pb-5 font-mono text-[11.5px] leading-[1.65] text-ink/85">
        {code}
      </pre>
    </div>
  )
}

function Check({ label }: { label: string }) {
  return (
    <span className="flex items-center gap-1.5 text-[12.5px] text-muted">
      <span className="grid h-4 w-4 place-items-center rounded-full bg-pagar-soft text-[9px] text-pagar">
        ✓
      </span>
      {label}
    </span>
  )
}

const FIGURES = [
  { value: '500', label: 'facturas del lote 1', note: '471 con texto, 29 escaneadas' },
  { value: '16', label: 'reglas de la norma v3', note: 'ninguna escrita a mano en el código' },
  { value: '0', label: 'llamadas a un modelo al decidir', note: 'el LLM nunca está en el camino' },
  { value: '2', label: 'lecturas de cada documento', note: 'si no coinciden, no se decide' },
]

function Figures() {
  return (
    <section className="border-y border-hairline bg-shell">
      <div className="mx-auto grid max-w-[1080px] gap-y-8 px-6 py-14 sm:grid-cols-2 lg:grid-cols-4">
        {FIGURES.map((figure) => (
          <div key={figure.label}>
            <p className="font-mono text-[40px] leading-none tracking-[-0.05em] tabular-nums">
              {figure.value}
            </p>
            <p className="mt-2.5 max-w-[22ch] text-[13.5px] leading-5 text-ink">{figure.label}</p>
            <p className="mt-1 max-w-[24ch] text-[12px] leading-5 text-faint">{figure.note}</p>
          </div>
        ))}
      </div>
    </section>
  )
}

const PACK_INVOICES = `{
  "nombre": "Pago de facturas",
  "tipos_decision": [
    {"nombre": "ESCALAR",  "prioridad": 3,
     "requiere_persona": true},
    {"nombre": "NO_PAGAR", "prioridad": 2},
    {"nombre": "PAGAR",    "prioridad": 1,
     "por_defecto": true}
  ],
  "simbolos": [
    {"nombre": "nif_emisor", "tipo": "texto"},
    {"nombre": "iban",       "tipo": "texto"},
    {"nombre": "total",      "tipo": "numero"}
  ]
}`

const PACK_EXPENSES = `{
  "nombre": "Gastos de viaje",
  "tipos_decision": [
    {"nombre": "REVISAR",  "prioridad": 3,
     "requiere_persona": true},
    {"nombre": "RECHAZAR", "prioridad": 2},
    {"nombre": "APROBAR",  "prioridad": 1,
     "por_defecto": true}
  ],
  "simbolos": [
    {"nombre": "empleado",     "tipo": "texto"},
    {"nombre": "importe",      "tipo": "numero"},
    {"nombre": "tiene_ticket", "tipo": "booleano"}
  ]
}`

function NotAboutInvoices() {
  return (
    <section id="procesos" className="mx-auto max-w-[1080px] px-6 py-16">
      <SectionHead
        kicker="OTROS PROCESOS"
        title="El código no sabe qué es una factura"
        lead="PAGAR y ESCALAR no están escritos en ninguna parte del programa. Un proceso son unos tipos de decisión, unos símbolos y unas reglas, y todo eso es un fichero JSON. Cambiar de problema es cambiar de fichero."
      />

      <div className="mt-8 grid gap-3 md:grid-cols-2">
        <Pack title="pago-facturas.json" body={PACK_INVOICES} note="El reto de Alberto." />
        <Pack
          title="gastos-viaje.json"
          body={PACK_EXPENSES}
          note="Otro problema, el mismo motor, cero líneas de código nuevas."
        />
      </div>
    </section>
  )
}

function Pack({ title, body, note }: { title: string; body: string; note: string }) {
  return (
    <div className="overflow-hidden rounded-[18px] bg-white ring-1 ring-black/[0.06]">
      <div className="border-b border-hairline px-4 py-2.5">
        <span className="font-mono text-[11.5px]">{title}</span>
      </div>
      <pre className="overflow-x-auto px-4 py-3.5 font-mono text-[11.5px] leading-[1.6] text-ink/85">
        {body}
      </pre>
      <p className="border-t border-hairline px-4 py-2.5 text-[12px] text-muted">{note}</p>
    </div>
  )
}

function Closing() {
  return (
    <section className="border-t border-hairline bg-shell">
      <div className="mx-auto max-w-[1080px] px-6 py-20">
        <h2 className="max-w-[20ch] text-[40px] font-medium leading-[1.02] tracking-[-0.045em]">
          Abre una factura y pregúntale por qué.
        </h2>
        <p className="mt-4 max-w-[52ch] text-[15px] leading-7 text-muted">
          La consola trae el lote 1 cargado. Puedes seguir una decisión hasta el símbolo que la
          causó, escribir una regla nueva y ver, antes de activarla, cuántas decisiones pasadas
          cambiaría.
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link
            to={paths.processes}
            className="inline-flex items-center gap-2 rounded-full bg-ink px-5 py-2.5 text-[14px] font-medium text-white hover:bg-ink/90"
          >
            Abrir la consola
            <ArrowRight size={15} strokeWidth={2} />
          </Link>
          <Link
            to={paths.newProcess}
            className="inline-flex items-center rounded-full bg-white px-5 py-2.5 text-[14px] text-ink ring-1 ring-black/[0.07] hover:bg-well"
          >
            Importar un proceso
          </Link>
        </div>
      </div>
    </section>
  )
}

function SectionHead({
  kicker,
  title,
  lead,
}: {
  kicker: string
  title: string
  lead: string
}) {
  return (
    <Reveal>
      <div className="max-w-[62ch]">
        <p className="font-mono text-[11px] tracking-[0.14em] text-faint">{kicker}</p>
        <h2 className="mt-3 text-[32px] font-medium leading-[1.06] tracking-[-0.04em]">{title}</h2>
        <p className="mt-3 text-[15px] leading-7 text-muted">{lead}</p>
      </div>
    </Reveal>
  )
}

function Footer() {
  return (
    <footer className="border-t border-hairline">
      <div className="mx-auto flex max-w-[1080px] flex-wrap items-center justify-between gap-3 px-6 py-8 text-[12px] text-faint">
        <span>
          trace<span className="text-faint">[.]</span>it · HackSpain 26, reto 500 Sombras de Alberto
        </span>
        <span className="font-mono">FastAPI · PostgreSQL · React</span>
      </div>
    </footer>
  )
}
