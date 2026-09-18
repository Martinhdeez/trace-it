import { Download, Minus, Plus, RotateCw, Search } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import type { InstanceDetail, InvoiceDocument } from '../../api/types'
import { formatEuro } from '../../lib/format'

export function DocumentPane({ instance }: { instance: InstanceDetail | undefined }) {
  const [query, setQuery] = useState('')
  const [searchOpen, setSearchOpen] = useState(false)
  const [zoom, setZoom] = useState(1)
  const [rotation, setRotation] = useState(0)

  const bumpZoom = (delta: number) => {
    setZoom((value) => Math.min(2, Math.max(0.5, Math.round((value + delta) * 10) / 10)))
  }

  return (
    <section className="flex min-h-0 min-w-0 flex-1 flex-col px-2 pb-3">
      <div className="flex items-end justify-between gap-3 px-3 pb-3 pt-1">
        <div>
          <p className="text-[11px] text-muted">Documento</p>
          <h2 className="text-[20px] font-medium tracking-[-0.03em]">
            {instance?.fileId ?? 'Sin archivo'}
          </h2>
        </div>
        <div className="flex items-center gap-1 rounded-full bg-canvas px-1 py-1 ring-1 ring-black/[0.06]">
          <IconBtn
            label="Buscar en el documento"
            pressed={searchOpen}
            onClick={() => setSearchOpen((open) => !open)}
          >
            <Search size={15} strokeWidth={1.5} />
          </IconBtn>
          <IconBtn
            label="Rotar 90°"
            onClick={() => setRotation((value) => (value + 90) % 360)}
          >
            <RotateCw size={15} strokeWidth={1.5} />
          </IconBtn>
          <IconBtn label="Alejar" onClick={() => bumpZoom(-0.1)}>
            <Minus size={15} strokeWidth={1.5} />
          </IconBtn>
          <button
            type="button"
            onClick={() => {
              setZoom(1)
              setRotation(0)
            }}
            className="min-w-[3rem] px-1 font-mono text-[11px] text-ink"
            title="Restablecer"
          >
            {Math.round(zoom * 100)}%
          </button>
          <IconBtn label="Acercar" onClick={() => bumpZoom(0.1)}>
            <Plus size={15} strokeWidth={1.5} />
          </IconBtn>
          <IconBtn
            label="Descargar facsímil"
            onClick={() => instance && downloadFacsimile(instance)}
          >
            <Download size={15} strokeWidth={1.5} />
          </IconBtn>
        </div>
      </div>

      {searchOpen ? (
        <div className="px-3 pb-2">
          <input
            autoFocus
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="NIF, IBAN, pedido…"
            className="w-full rounded-full bg-canvas px-3 py-1.5 text-[13px] outline-none ring-1 ring-black/[0.06] placeholder:text-faint"
          />
        </div>
      ) : null}

      <div
        className="relative min-h-0 flex-1 overflow-auto rounded-[16px] bg-well ring-1 ring-black/[0.04]"
        onWheel={(event) => {
          if (!event.ctrlKey && !event.metaKey) return
          event.preventDefault()
          bumpZoom(event.deltaY > 0 ? -0.1 : 0.1)
        }}
      >
        <div className="flex min-h-full justify-center p-8">
          {!instance ? (
            <p className="self-center text-[13px] text-muted">Selecciona un archivo de la cola.</p>
          ) : instance.document ? (
            <div
              style={{
                width: 560,
                transform: `rotate(${rotation}deg) scale(${zoom})`,
                transformOrigin: 'top center',
              }}
            >
              <InvoicePaper doc={instance.document} query={query} />
            </div>
          ) : (
            <div className="self-center max-w-[420px] text-center">
              <p className="font-mono text-[12px]">{instance.fileId}</p>
              <p className="mt-2 text-[13px] text-muted">
                {instance.ocrNote ?? 'Sin texto extraíble. Esperando consenso OCR.'}
              </p>
            </div>
          )}
        </div>
      </div>

      {instance?.document ? (
        <div className="flex items-center justify-between px-3 pt-2 text-[12px] text-muted">
          <span className="font-mono">{instance.fileId.replace('.pdf', '')}</span>
          <span>
            p.{instance.document.page} · {instance.document.inputKind} · {instance.document.sizeKb} KB
          </span>
        </div>
      ) : null}
    </section>
  )
}

function InvoicePaper({ doc, query }: { doc: InvoiceDocument; query: string }) {
  const H = (text: string) => highlight(text, query)
  return (
    <article className="rounded-[12px] bg-paper px-9 py-8 text-ink shadow-[0_8px_30px_rgba(19,19,19,0.06)] ring-1 ring-black/[0.06]">
      <header className="flex items-start justify-between gap-6">
        <div>
          <h1 className="text-[22px] font-medium tracking-[-0.035em]">{H(doc.supplierName)}</h1>
          {doc.supplierActivity ? (
            <p className="mt-1 text-[12px] text-muted">{H(doc.supplierActivity)}</p>
          ) : null}
        </div>
        <div className="text-right text-[12px] text-muted">
          {doc.address.split('\n').map((line) => (
            <p key={line}>{H(line)}</p>
          ))}
          {doc.phone ? <p>{H(doc.phone)}</p> : null}
          {doc.email ? <p>{H(doc.email)}</p> : null}
        </div>
      </header>

      <div className="mt-7 grid grid-cols-2 gap-3">
        <Field label="NIF" value={doc.nif} query={query} />
        <div className="text-right text-[12px]">
          <p className="tracking-[0.08em] text-muted">FACTURA</p>
          <p className="mt-1">
            N.º {H(doc.invoiceNumber)}
            <br />
            Fecha: {H(doc.date)}
            <br />
            Cliente: {H(doc.clientName)}
            <br />
            NIF {H(doc.clientNif)}
          </p>
        </div>
        <Field label="IBAN" value={doc.iban} query={query} className="col-span-2" />
      </div>

      <div className="mt-5 flex flex-wrap items-center gap-x-5 gap-y-1 text-[13px]">
        <Field label="Pedido" value={doc.pedido} query={query} />
        {doc.albaran ? <span className="text-muted">Albarán: {H(doc.albaran)}</span> : null}
        {doc.paymentMethod ? (
          <span className="text-muted">Forma de pago: {H(doc.paymentMethod)}</span>
        ) : null}
      </div>

      <table className="mt-6 w-full text-[13px]">
        <thead>
          <tr className="border-b border-ink/12 text-left text-muted">
            <th className="pb-2 font-medium">Descripción</th>
            <th className="pb-2 text-right font-medium">Cant.</th>
            <th className="pb-2 text-right font-medium">Precio unit. (€)</th>
            <th className="pb-2 text-right font-medium">Base (€)</th>
          </tr>
        </thead>
        <tbody>
          {doc.lines.map((line) => (
            <tr key={line.description} className="border-b border-hairline">
              <td className="py-2">{H(line.description)}</td>
              <td className="py-2 text-right font-mono">{line.qty}</td>
              <td className="py-2 text-right font-mono">{formatEuro(line.unitPrice)}</td>
              <td className="py-2 text-right font-mono">{formatEuro(line.base)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="mt-4 ml-auto w-52 text-[13px]">
        <Row label="Base imponible" value={formatEuro(doc.base)} />
        <Row label={`IVA ${Math.round(doc.ivaRate * 100)}%`} value={formatEuro(doc.ivaAmount)} />
        <Row label="TOTAL (€)" value={formatEuro(doc.total)} strong />
      </div>

      <footer className="mt-10 flex items-end justify-between gap-4">
        {doc.conditions ? (
          <p className="whitespace-pre-line text-[12px] text-muted">{H(doc.conditions)}</p>
        ) : (
          <span />
        )}
        {doc.signature ? (
          <p className="whitespace-pre-line text-right font-[Georgia] text-[13px] italic text-[#2c3a78]">
            {H(doc.signature)}
          </p>
        ) : null}
      </footer>
    </article>
  )
}

function Field({
  label,
  value,
  query,
  className,
}: {
  label: string
  value: string
  query: string
  className?: string
}) {
  return (
    <p className={className}>
      <span className="text-[11px] font-medium tracking-[0.04em] text-pagar">{label} </span>
      <span className="font-mono text-[13px]">{highlight(value, query)}</span>
    </p>
  )
}

function Row({
  label,
  value,
  strong,
}: {
  label: string
  value: string
  strong?: boolean
}) {
  return (
    <div className={`flex justify-between py-0.5 ${strong ? 'border-t border-ink/20 pt-1.5 font-medium' : ''}`}>
      <span>{label}</span>
      <span className="font-mono">{value}</span>
    </div>
  )
}

function IconBtn({
  label,
  children,
  onClick,
  pressed,
}: {
  label: string
  children: ReactNode
  onClick?: () => void
  pressed?: boolean
}) {
  return (
    <button
      type="button"
      title={label}
      aria-pressed={pressed}
      onClick={onClick}
      className={`grid h-7 w-7 place-items-center rounded-full hover:bg-white hover:text-ink ${
        pressed ? 'bg-white text-ink shadow-[0_1px_2px_rgba(19,19,19,0.06)]' : ''
      }`}
    >
      {children}
    </button>
  )
}

function highlight(text: string, query: string): ReactNode {
  const q = query.trim()
  if (!q) return text
  const index = text.toLowerCase().indexOf(q.toLowerCase())
  if (index < 0) return text
  return (
    <>
      {text.slice(0, index)}
      <mark>{text.slice(index, index + q.length)}</mark>
      {highlight(text.slice(index + q.length), query)}
    </>
  )
}

function downloadFacsimile(instance: InstanceDetail) {
  const doc = instance.document
  const body = doc
    ? [
        doc.supplierName,
        doc.nif,
        doc.iban,
        `Factura ${doc.invoiceNumber} · ${doc.date}`,
        `Pedido ${doc.pedido}`,
        `Total ${formatEuro(doc.total)} €`,
        '',
        ...(doc.lines.map(
          (line) => `${line.description}\t${line.qty}\t${formatEuro(line.base)}`,
        ) ?? []),
      ].join('\n')
    : instance.ocrNote ?? instance.fileId

  const html = `<!doctype html><meta charset="utf-8"><title>${instance.fileId}</title>
<body style="font:14px/1.45 Geist,ui-sans-serif,sans-serif;max-width:40rem;margin:2rem auto;color:#131313">
<pre style="font:13px/1.5 'Geist Mono',ui-monospace,monospace;white-space:pre-wrap">${escapeHtml(body)}</pre>
</body>`
  const blob = new Blob([html], { type: 'text/html' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = instance.fileId.replace(/\.pdf$/i, '') + '.html'
  link.click()
  URL.revokeObjectURL(url)
}

function escapeHtml(value: string) {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
}
