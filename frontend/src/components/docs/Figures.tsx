import type { ReactNode } from 'react'
import { cn } from '../../lib/cn'

export function Figure({ slug }: { slug: string }) {
  switch (slug) {
    case 'motor':
      return <Motor />
    case 'tester':
      return <Tester />
    case 'packs':
      return <Packs />
    case 'historia':
      return <Historia />
    case 'resiliencia':
      return <Resiliencia />
    default:
      return null
  }
}

function Frame({ children, caption }: { children: ReactNode; caption: string }) {
  return (
    <figure className="m-0">
      <div className="overflow-hidden rounded-[18px] bg-white shadow-[0_1px_2px_rgba(19,19,19,0.04),0_18px_50px_rgba(19,19,19,0.07)] ring-1 ring-black/[0.06]">
        {children}
      </div>
      <figcaption className="mt-3 text-[12px] text-faint">{caption}</figcaption>
    </figure>
  )
}

function Motor() {
  return (
    <Frame caption="El modelo rodea al motor. No entra.">
      <div className="grid md:grid-cols-[1fr_4.5rem_1fr]">
        <div className="border-b border-hairline p-5 md:border-b-0 md:border-r">
          <p className="font-mono text-[11px] text-faint">el modelo</p>
          <p className="mt-1 text-[15px] font-medium tracking-[-0.02em]">Escribe, lee, explica</p>
          <ul className="mt-4 flex flex-col gap-2">
            {['Compila la regla a Python', 'Lee el PDF una vez', 'Explica el caso raro', 'Propone a la persona'].map(
              (item) => (
                <li
                  key={item}
                  className="rounded-[12px] bg-canvas px-3 py-2 text-[13px] text-muted"
                >
                  {item}
                </li>
              ),
            )}
          </ul>
          <p className="mt-4 font-mono text-[11px] text-faint">una vez, y se guarda</p>
        </div>

        <div className="flex items-center justify-center border-b border-hairline bg-canvas py-4 md:border-b-0 md:border-x md:border-hairline">
          <p className="rotate-0 font-mono text-[10px] tracking-[0.18em] text-faint uppercase md:rotate-90 md:whitespace-nowrap">
            no cruza
          </p>
        </div>

        <div className="p-5">
          <p className="font-mono text-[11px] text-faint">el motor</p>
          <p className="mt-1 text-[15px] font-medium tracking-[-0.02em]">Decide</p>
          <div className="mt-4 rounded-[12px] bg-ink px-3 py-3 text-white">
            <p className="font-mono text-[11px] text-white/50">evaluate(instance, sources, others)</p>
            <p className="mt-1 font-mono text-[13px]">{'{ fires, reason }'}</p>
          </div>
          <ol className="mt-3 flex flex-col gap-1.5 font-mono text-[12px]">
            <li className="flex items-center justify-between rounded-[10px] bg-escalar-soft px-3 py-1.5 text-escalar">
              ESCALAR <span>3</span>
            </li>
            <li className="flex items-center justify-between rounded-[10px] bg-nopagar-soft px-3 py-1.5 text-nopagar">
              NO_PAGAR <span>2</span>
            </li>
            <li className="flex items-center justify-between rounded-[10px] bg-pagar-soft px-3 py-1.5 text-pagar">
              PAGAR <span>1</span>
            </li>
          </ol>
          <p className="mt-4 font-mono text-[11px] text-faint">0 tokens · mismo resultado mañana</p>
        </div>
      </div>
    </Frame>
  )
}

function Tester() {
  const tests = [
    { name: 'pedido existe', fires: false },
    { name: 'pedido de otro nif', fires: true },
    { name: 'sin pedido', fires: true },
    { name: 'pedido vacío', fires: true },
    { name: 'mismo proveedor', fires: false },
    { name: 'importe distinto', fires: false },
  ]

  return (
    <Frame caption="El tester escribe los tests sin ver el código. El coder no escribe tests.">
      <div className="border-b border-hairline bg-canvas px-5 py-3">
        <p className="font-mono text-[11px] text-faint">texto de la regla</p>
        <p className="mt-1 text-[14px] tracking-[-0.02em]">
          El pedido tiene que existir y ser de este proveedor.
        </p>
      </div>
      <div className="grid md:grid-cols-2">
        <div className="border-b border-hairline p-5 md:border-b-0 md:border-r">
          <p className="font-mono text-[11px] text-faint">tester · no ve código</p>
          <ul className="mt-3 flex flex-col gap-1.5">
            {tests.map((test) => (
              <li key={test.name} className="flex items-center justify-between text-[12.5px]">
                <span>{test.name}</span>
                <span
                  className={cn(
                    'font-mono text-[10px]',
                    test.fires ? 'text-nopagar' : 'text-pagar',
                  )}
                >
                  {test.fires ? 'fires' : 'quiet'}
                </span>
              </li>
            ))}
          </ul>
        </div>
        <div className="p-5">
          <p className="font-mono text-[11px] text-faint">coder · itera contra los tests</p>
          <pre className="mt-3 overflow-x-auto rounded-[12px] bg-canvas px-3 py-3 font-mono text-[11px] leading-5 text-ink">
            {`def evaluate(instance, sources, others):
    order = lookup(sources, instance)
    if not order:
        return fire("no hay pedido")
    if order.nif != instance.nif:
        return fire("otro nif")
    return quiet()`}
          </pre>
        </div>
      </div>
      <div className="grid gap-px bg-hairline sm:grid-cols-3">
        <div className="bg-white px-5 py-3">
          <p className="font-mono text-[10px] text-faint">sandbox</p>
          <p className="mt-1 text-[13px]">6/6 tests</p>
        </div>
        <div className="bg-white px-5 py-3">
          <p className="font-mono text-[10px] text-faint">impacto</p>
          <p className="mt-1 text-[13px]">cambia 27 / 500</p>
        </div>
        <div className="bg-escalar-soft px-5 py-3">
          <p className="font-mono text-[10px] text-escalar">puerta</p>
          <p className="mt-1 text-[13px] text-escalar">se queda en borrador</p>
        </div>
      </div>
    </Frame>
  )
}

function Packs() {
  return (
    <Frame caption="Dos packs. Un motor. NIF y PAGAR no viven en el código.">
      <div className="grid gap-px bg-hairline lg:grid-cols-[1fr_1fr_minmax(0,16rem)]">
        <PackCard
          file="invoice-payment"
          live
          lines={[
            'ESCALAR 3  requires_human',
            'NO_PAGAR 2',
            'PAGAR 1  default',
            '12 símbolos · 16 reglas',
          ]}
        />
        <PackCard
          file="travel-expenses"
          lines={['ESCALATE 3  requires_human', 'REJECT 2', 'APPROVE 1  default', '3 símbolos · 2 reglas']}
        />
        <div className="bg-ink p-5 text-white">
          <p className="font-mono text-[11px] text-white/45">el núcleo</p>
          <p className="mt-2 text-[15px] font-medium tracking-[-0.02em]">
            evaluate, prioridad, bandeja.
          </p>
          <p className="mt-4 text-[13px] leading-6 text-white/70">
            No sabe qué es un NIF. No sabe qué es PAGAR. Corre el pack que le cargues.
          </p>
        </div>
      </div>
    </Frame>
  )
}

function PackCard({
  file,
  lines,
  live,
}: {
  file: string
  lines: string[]
  live?: boolean
}) {
  return (
    <div className="bg-white p-5">
      <div className="flex items-center justify-between gap-3">
        <p className="font-mono text-[12px]">{file}</p>
        {live ? (
          <span className="rounded-full bg-pagar-soft px-2 py-0.5 font-mono text-[10px] text-pagar">
            lote 1
          </span>
        ) : (
          <span className="font-mono text-[10px] text-faint">mismo loader</span>
        )}
      </div>
      <ul className="mt-4 flex flex-col gap-1.5 font-mono text-[12px] text-muted">
        {lines.map((line) => (
          <li key={line}>{line}</li>
        ))}
      </ul>
    </div>
  )
}

function Historia() {
  const rows = [
    { when: '19 sep', file: 'factura_5518', verdict: 'ESCALAR', note: 'v4 diría NO_PAGAR', finding: true },
    { when: '18 sep', file: 'factura_1936', verdict: 'NO_PAGAR', note: 'reglas v3' },
    { when: '12 sep', file: 'factura_4475', verdict: 'PAGAR', note: 'reglas v3' },
    { when: '1 sep', file: 'scan_001', verdict: 'ESCALAR', note: 'MISSING_DATA' },
  ]

  return (
    <Frame caption="Las filas nuevas se añaden. Las viejas se quedan. Un hallazgo es un aviso.">
      <div className="border-b border-hairline px-5 py-3">
        <p className="font-mono text-[11px] text-faint">decisiones · append-only</p>
      </div>
      <ul>
        {rows.map((row) => (
          <li
            key={row.file}
            className={cn(
              'grid grid-cols-[4.5rem_minmax(0,1fr)_7.5rem] items-baseline gap-3 border-b border-hairline px-5 py-3 last:border-0',
              row.finding && 'bg-escalar-soft/60',
            )}
          >
            <span className="font-mono text-[11px] text-faint">{row.when}</span>
            <span>
              <span className="text-[13px]">{row.file}</span>
              <span className="mt-0.5 block text-[12px] text-muted">{row.note}</span>
            </span>
            <Verdict name={row.verdict} />
          </li>
        ))}
      </ul>
      <div className="border-t border-hairline bg-canvas px-5 py-3 text-[12.5px] leading-6 text-muted">
        El hallazgo no edita la fila de marzo. Te deja la lista. Reclamar, o no, lo decides tú.
      </div>
    </Frame>
  )
}

function Verdict({ name }: { name: string }) {
  const tone =
    name === 'PAGAR' ? 'text-pagar' : name === 'NO_PAGAR' ? 'text-nopagar' : 'text-escalar'
  return <span className={cn('text-right font-mono text-[11px]', tone)}>{name}</span>
}

function Resiliencia() {
  const rows = [
    {
      fails: 'El modelo se cae',
      happens: 'Las reglas activas siguen. La nueva se queda en borrador.',
      never: 'PAGAR inventado',
    },
    {
      fails: 'El código de una regla peta',
      happens: 'ESCALAR con RULE_ERROR y el motivo.',
      never: 'PAGAR por omisión',
    },
    {
      fails: 'El ERP suelta 429',
      happens: 'Reintenta, honra Retry-After, guarda un snapshot. ORA-00600 igual.',
      never: 'Decidir en vivo',
    },
  ]

  return (
    <Frame caption="Tres fallos que el tribunal va a preguntar. Ninguno se convierte en un pago.">
      <div className="hidden grid-cols-[minmax(0,12rem)_minmax(0,1fr)_minmax(0,13rem)] border-b border-hairline px-5 py-2.5 font-mono text-[10px] text-faint sm:grid">
        <span>si falla</span>
        <span>qué hacemos</span>
        <span className="text-right">qué no pasa</span>
      </div>
      <ul>
        {rows.map((row) => (
          <li
            key={row.fails}
            className="grid gap-2 border-b border-hairline px-5 py-4 last:border-0 sm:grid-cols-[minmax(0,12rem)_minmax(0,1fr)_minmax(0,13rem)] sm:items-baseline"
          >
            <p className="text-[13px] font-medium tracking-[-0.02em]">{row.fails}</p>
            <p className="text-[13px] leading-6 text-muted">{row.happens}</p>
            <p className="font-mono text-[11px] text-nopagar sm:text-right">{row.never}</p>
          </li>
        ))}
      </ul>
    </Frame>
  )
}
