import { useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ChevronLeft, ChevronRight, Download, Minus, Plus, RotateCw } from 'lucide-react'
import type { DocumentEvidence, DocumentLocations } from '../../api/contracts'
import { get, getBlob } from '../../api/http'
import { cn } from '../../lib/cn'

const precisionLabel = {
  text: 'Exact text',
  ocr: 'OCR text',
  region: 'Approximate source region',
  page: 'Source page only; precise location unavailable',
  unavailable: 'Location unavailable',
}

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
  const [candidateOverride, setCandidate] = useState<number | null>(null)
  const [focusRequest, setFocusRequest] = useState(0)
  const [pageOverride, setPageOverride] = useState<number | null>(null)
  const [zoom, setZoom] = useState(1)
  const [rotation, setRotation] = useState(0)
  const [query, setQuery] = useState('')
  const [downloadError, setDownloadError] = useState('')
  const highlight = useRef<HTMLDivElement>(null)
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
  const candidate =
    candidateOverride ??
    Math.max(
      0,
      readings.findIndex((reading) => reading.value === (field?.value ?? field?.proposed_value)),
    )
  const source = readings[candidate]
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
  }, [source, focusRequest, pageImage.data, rotation, zoom, page])
  const dimensions = locations.data?.pages.find((item) => item.number === page)
  const width = (dimensions?.width ?? 595) * zoom
  const height = (dimensions?.height ?? 842) * zoom
  const sideways = rotation % 180 !== 0
  const shown = source?.page === page ? source : undefined

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
      setDownloadError('Could not download the original PDF. Please try again.')
    }
  }

  return (
    <section
      aria-label="PDF reading evidence"
      className="flex h-full min-h-0 min-w-0 flex-1 flex-col"
    >
      <div className="flex flex-wrap items-center gap-2 border-b border-hairline px-3 py-2 text-[12px]">
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
            onClick={() => setZoom(Math.max(0.5, zoom - 0.25))}
          >
            <Minus size={16} />
          </button>
          <button
            title="Reset view"
            aria-label="Reset view"
            onClick={() => {
              setZoom(1)
              setRotation(0)
            }}
            className="w-12 font-mono"
          >
            {Math.round(zoom * 100)}%
          </button>
          <button
            aria-label="Zoom in"
            disabled={zoom >= 3}
            onClick={() => setZoom(Math.min(3, zoom + 0.25))}
          >
            <Plus size={16} />
          </button>
          <button aria-label="Rotate page" onClick={() => setRotation((rotation + 90) % 360)}>
            <RotateCw size={16} />
          </button>
          <button aria-label="Download original PDF" onClick={download}>
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
        <aside
          aria-label="Extracted fields"
          className="max-h-52 shrink-0 overflow-auto border-b border-hairline p-3 lg:max-h-none lg:w-56 lg:border-r lg:border-b-0"
        >
          <label className="mb-3 block text-[11px] text-muted">
            Find a field or value
            <input
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
                  setCandidate(null)
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
        </aside>
        <div className="flex min-h-0 min-w-0 flex-1 flex-col">
          <div
            aria-live="polite"
            className="shrink-0 border-b border-hairline px-3 py-2 text-[11px] text-muted"
          >
            {selectedField ? (
              <>
                <span className="font-mono text-ink">{selectedField}</span>
                {source ? (
                  <>
                    <span>
                      {' '}
                      · {precisionLabel[source.precision]} · {source.method}
                    </span>
                    <p className="mt-1 break-words text-ink">“{source.raw}”</p>
                    {(locations.data?.fields[selectedField]?.length ?? 0) > 1 && (
                      <label className="mt-2 block">
                        Reading{' '}
                        <select
                          aria-label="Source reading"
                          value={candidate}
                          onChange={(event) => {
                            setCandidate(Number(event.target.value))
                            setPageOverride(null)
                          }}
                          className="ml-1 max-w-full rounded bg-canvas p-1"
                        >
                          {locations.data!.fields[selectedField].map((reading, index) => (
                            <option key={index} value={index}>
                              {index + 1} · {reading.method} · page {reading.page ?? '?'} ·{' '}
                              {reading.raw}
                            </option>
                          ))}
                        </select>
                      </label>
                    )}
                  </>
                ) : (
                  <span>
                    {' '}
                    ·{' '}
                    {locations.isPending
                      ? 'Locating…'
                      : 'No document location recorded for this field'}
                  </span>
                )}
              </>
            ) : (
              'Select a field to see where it was read in the original PDF.'
            )}
          </div>
          <div
            className="min-h-0 flex-1 overflow-auto bg-canvas p-5"
            aria-label="Original PDF page"
          >
            {pageImage.isError ? (
              <p role="alert">
                Could not load this PDF page.{' '}
                <button className="underline" onClick={() => pageImage.refetch()}>
                  Retry
                </button>
              </p>
            ) : !pageImage.data ? (
              <p role="status">Loading page…</p>
            ) : (
              <div
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
                  {shown?.boxes.map(([x0, y0, x1, y1], index) => (
                    <div
                      key={`${selectedField}-${candidate}-${index}`}
                      ref={index === 0 ? highlight : undefined}
                      data-testid="source-box"
                      title={`${selectedField}: ${shown.raw}`}
                      className={cn(
                        'pointer-events-none absolute bg-amber-300/20 outline-2 outline-offset-1',
                        shown.precision === 'region'
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
