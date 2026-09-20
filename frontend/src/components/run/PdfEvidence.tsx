import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'motion/react'
import { ChevronLeft, ChevronRight, Download, Minus, Plus, RotateCw, ScanText } from 'lucide-react'
import type { DocumentEvidence, DocumentLocations } from '../../api/contracts'
import { get, getBlob } from '../../api/http'
import { cn } from '../../lib/cn'

export function PdfEvidence({
  instanceId,
  name,
  evidence,
  initialSymbol,
}: {
  instanceId: number
  name: string
  evidence: DocumentEvidence
  initialSymbol?: string
}) {
  const [fieldName, setFieldName] = useState<string | null>(null)
  const [focusRequest, setFocusRequest] = useState(0)
  const [pageOverride, setPageOverride] = useState<number | null>(null)
  const [zoom, setZoom] = useState(1)
  const [rotation, setRotation] = useState(0)
  const [query, setQuery] = useState('')
  // The readings panel is a tool for digging, not the first thing to see: folded unless
  // the caller asked for a specific field.
  const [showFields, setShowFields] = useState(Boolean(initialSymbol))
  const [downloadError, setDownloadError] = useState('')
  const highlight = useRef<HTMLDivElement>(null)
  const scroller = useRef<HTMLDivElement>(null)
  const sheet = useRef<HTMLDivElement>(null)
  const zoomAnchor = useRef<{ x: number; y: number; clientX: number; clientY: number } | null>(null)
  const root = `/instances/${instanceId}`
  const locations = useQuery({
    queryKey: ['document-locations', instanceId, evidence.id],
    queryFn: async () => {
      const result = await get<DocumentLocations>(`${root}/document/locations`)
      if (result.extraction_id !== evidence.id || result.sha256 !== evidence.sha256) {
        throw new Error('The document reading changed. Reopen the document to load its latest evidence.')
      }
      return result
    },
    staleTime: Infinity,
  })
  const selectedField = fieldName ?? (initialSymbol
    ? locations.data?.symbol_fields[initialSymbol] ?? initialSymbol
    : null)
  const readings = selectedField ? (locations.data?.fields[selectedField] ?? []) : []
  const field = selectedField ? evidence.fields?.[selectedField] : undefined
  // Every reader's reading is drawn at once, text layer and scanner alike. The page to open
  // is the one of the best reading: the value that was kept, and one that has a box.
  const kept = field?.value ?? field?.proposed_value
  const source =
    readings.find((reading) => reading.value === kept && reading.boxes.length) ??
    readings.find((reading) => reading.boxes.length) ??
    readings.find((reading) => reading.value === kept) ??
    readings[0]
  const page = pageOverride ?? source?.page ?? 1
  const pageImage = useQuery({
    queryKey: ['document-page', instanceId, evidence.sha256, page],
    queryFn: () => getBlob(`${root}/document/pages/${page}`),
    staleTime: Infinity,
  })
  useEffect(() => {
    highlight.current?.scrollIntoView({
      block: 'center',
      inline: 'center',
      behavior: 'instant',
    })
  }, [source, focusRequest, pageImage.data, rotation, page])
  const dimensions = locations.data?.pages.find((item) => item.number === page)
  const width = (dimensions?.width ?? 595) * zoom
  const height = (dimensions?.height ?? 842) * zoom
  const sideways = rotation % 180 !== 0
  // The best reading first, so the view centres on it; two readers boxing the same spot
  // draw one box.
  const shown = [...(source ? [source] : []), ...readings.filter((reading) => reading !== source)]
    .filter((reading) => reading.page === page)
    .flatMap((reading) => reading.boxes.map((box) => ({ reading, box, key: box.join(',') })))
    .filter((item, index, all) => all.findIndex((other) => other.key === item.key) === index)

  function changeZoom(next: number, point?: { x: number; y: number }) {
    next = Math.max(0.5, Math.min(3, next))
    if (next === zoom) return
    if (scroller.current && sheet.current) {
      const panel = scroller.current.getBoundingClientRect()
      const paper = sheet.current.getBoundingClientRect()
      const clientX = point?.x ?? panel.left + panel.width / 2
      const clientY = point?.y ?? panel.top + panel.height / 2
      zoomAnchor.current = {
        x: (clientX - paper.left) / paper.width,
        y: (clientY - paper.top) / paper.height,
        clientX,
        clientY,
      }
    }
    setZoom(next)
  }

  useLayoutEffect(() => {
    const anchor = zoomAnchor.current
    if (anchor && sheet.current && scroller.current) {
      const paper = sheet.current.getBoundingClientRect()
      scroller.current.scrollLeft += paper.left + anchor.x * paper.width - anchor.clientX
      scroller.current.scrollTop += paper.top + anchor.y * paper.height - anchor.clientY
    }
    zoomAnchor.current = null
  }, [zoom])

  useEffect(() => {
    const panel = scroller.current
    if (!panel) return
    function wheel(event: WheelEvent) {
      // Trackpad pinch arrives as ctrl+wheel. Ordinary scrolling remains ordinary scrolling.
      if (!event.ctrlKey && !event.metaKey) return
      event.preventDefault()
      changeZoom(zoom * Math.exp(-event.deltaY * 0.005), { x: event.clientX, y: event.clientY })
    }
    panel.addEventListener('wheel', wheel, { passive: false })
    return () => panel.removeEventListener('wheel', wheel)
  }, [zoom])

  async function download() {
    setDownloadError('')
    try {
      const blob = await getBlob(`${root}/file`)
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = name
      link.click()
      setTimeout(() => URL.revokeObjectURL(url), 1000)
    } catch {
      setDownloadError('Could not download the original document. Please try again.')
    }
  }

  return (
    <section
      aria-label="Document reading evidence"
      className="flex h-full min-h-0 min-w-0 flex-1 flex-col"
    >
      <div className="flex flex-wrap items-center gap-2 border-b border-hairline px-3 py-2 text-[12px]">
        <button
          title={showFields ? 'Hide extracted fields' : 'Show extracted fields'}
          aria-label={showFields ? 'Hide extracted fields' : 'Show extracted fields'}
          aria-pressed={showFields}
          onClick={() => setShowFields((open) => !open)}
          className={cn(
            'flex items-center gap-1.5 rounded-full px-2.5 py-1 ring-1 transition-colors',
            showFields ? 'bg-ocr-soft text-ink ring-ocr' : 'text-muted ring-line hover:bg-canvas hover:text-ink',
          )}
        >
          <ScanText size={14} strokeWidth={1.75} />
          Fields
        </button>
        <button
          title="Previous page"
          aria-label="Previous page"
          disabled={page <= 1}
          onClick={() => setPageOverride(page - 1)}
          className="rounded p-1 hover:bg-canvas disabled:opacity-30"
        >
          <ChevronLeft size={16} />
        </button>
        <span aria-live="polite" className="font-mono">
          Page {page} / {locations.data?.pages.length ?? '…'}
        </span>
        <button
          title="Next page"
          aria-label="Next page"
          disabled={!locations.data || page >= locations.data.pages.length}
          onClick={() => setPageOverride(page + 1)}
          className="rounded p-1 hover:bg-canvas disabled:opacity-30"
        >
          <ChevronRight size={16} />
        </button>
        <div className="ml-auto flex items-center gap-2">
          <button
            aria-label="Zoom out"
            disabled={zoom <= 0.5}
            onClick={() => changeZoom(zoom - 0.25)}
          >
            <Minus size={16} />
          </button>
          <button
            title="Reset view"
            aria-label="Reset view"
            onClick={() => {
              setZoom(1)
              setRotation(0)
              setFocusRequest((value) => value + 1)
            }}
            className="w-12 font-mono"
          >
            {Math.round(zoom * 100)}%
          </button>
          <button
            aria-label="Zoom in"
            disabled={zoom >= 3}
            onClick={() => changeZoom(zoom + 0.25)}
          >
            <Plus size={16} />
          </button>
          <button aria-label="Rotate page" onClick={() => setRotation((rotation + 90) % 360)}>
            <RotateCw size={16} />
          </button>
          <button aria-label="Download original document" onClick={download}>
            <Download size={16} />
          </button>
        </div>
      </div>
      {downloadError && (
        <p role="alert" className="px-3 py-2 text-[12px]">
          {downloadError}
        </p>
      )}
      <div className="flex min-h-0 flex-1 flex-col lg:flex-row">
        <AnimatePresence initial={false}>
        {showFields ? (
        <motion.aside
          key="fields"
          aria-label="Extracted fields"
          initial={{ opacity: 0, width: 0 }}
          animate={{ opacity: 1, width: 'auto' }}
          exit={{ opacity: 0, width: 0 }}
          transition={{ duration: 0.28, ease: [0.23, 1, 0.32, 1] }}
          className="max-h-52 shrink-0 overflow-hidden border-b border-hairline lg:max-h-none lg:border-r lg:border-b-0"
        >
        <div className="h-full overflow-auto p-3 lg:w-56">
          <label className="mb-3 block text-[11px] text-muted">
            Find a field or value
            <input
              autoFocus
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search readings…"
              className="mt-1 w-full rounded-lg bg-canvas px-2 py-2 text-[12px] outline-offset-2"
            />
          </label>
          {locations.isPending && (
            <p role="status" className="mb-2 text-[11px] text-muted">
              Locating source text…
            </p>
          )}
          {locations.isError && (
            <p role="alert" className="mb-2 text-[11px]">
              {locations.error.message || 'Source locations could not be loaded.'}{' '}
              <button className="underline" onClick={() => locations.refetch()}>
                Retry
              </button>
            </p>
          )}
          {Object.entries(evidence.fields ?? {})
            .filter(([name, field]) =>
              `${name} ${field.value ?? field.proposed_value ?? ''}`
                .toLowerCase()
                .includes(query.toLowerCase()),
            )
            .map(([name, field]) => (
              <button
                key={name}
                aria-pressed={selectedField === name}
                onClick={() => {
                  setFieldName(name)
                  setFocusRequest((value) => value + 1)
                  setPageOverride(null)
                }}
                className={cn(
                  'mb-1 block w-full rounded-lg border p-2 text-left focus-visible:outline-2 focus-visible:outline-offset-2',
                  selectedField === name
                    ? 'border-ocr bg-ocr-soft'
                    : 'border-transparent hover:bg-canvas',
                )}
              >
                <span className="block break-words font-mono text-[10px] text-muted">{name}</span>
                <span className="mt-1 block break-words font-mono text-[12px]">
                  {field.value ?? field.proposed_value ?? 'No value'}
                </span>
                <span className="mt-1 block text-[10px] text-muted">
                  {field.verification ?? (field.value ? 'Extracted' : 'Missing')}
                  {field.value == null && field.proposed_value ? ' · proposal' : ''}
                </span>
              </button>
            ))}
        </div>
        </motion.aside>
        ) : null}
        </AnimatePresence>
        <div className="flex min-h-0 min-w-0 flex-1 flex-col">
          <div
            ref={scroller}
            className="min-h-0 flex-1 overflow-auto bg-canvas p-5"
            aria-label="Document page"
          >
            {pageImage.isError ? (
              <p role="alert">
                Could not load this document page.{' '}
                <button className="underline" onClick={() => pageImage.refetch()}>
                  Retry
                </button>
              </p>
            ) : !pageImage.data ? (
              <p role="status">Loading page…</p>
            ) : (
              <div
                ref={sheet}
                className="relative mx-auto shrink-0"
                style={{
                  width: sideways ? height : width,
                  height: sideways ? width : height,
                }}
              >
                <div
                  className="absolute left-1/2 top-1/2 bg-white shadow-float"
                  style={{
                    width,
                    height,
                    transform: `translate(-50%, -50%) rotate(${rotation}deg)`,
                  }}
                >
                  <OriginalPageImage blob={pageImage.data} alt={`${name}, page ${page}`} />
                  {shown.map(({ reading, box: [x0, y0, x1, y1], key }, index) => (
                    <div
                      key={key}
                      ref={index === 0 ? highlight : undefined}
                      data-testid="source-box"
                      title={`${selectedField}: ${reading.raw}`}
                      className={cn(
                        'pointer-events-none absolute bg-amber-300/20 outline-2 outline-offset-1',
                        reading.precision === 'region'
                          ? 'outline-dashed outline-amber-600'
                          : 'outline-solid outline-amber-500',
                      )}
                      style={{
                        left: `${x0 * 100}%`,
                        top: `${y0 * 100}%`,
                        width: `${(x1 - x0) * 100}%`,
                        height: `${(y1 - y0) * 100}%`,
                      }}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  )
}

function OriginalPageImage({ blob, alt }: { blob: Blob; alt: string }) {
  const image = useRef<HTMLImageElement>(null)
  useEffect(() => {
    const url = URL.createObjectURL(blob)
    if (image.current) image.current.src = url
    return () => URL.revokeObjectURL(url)
  }, [blob])
  return <img ref={image} alt={alt} draggable={false} className="block h-full w-full" />
}
