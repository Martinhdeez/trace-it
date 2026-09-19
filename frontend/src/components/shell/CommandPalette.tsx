import { useEffect, useMemo, useState } from 'react'
import { useLocation, useNavigate } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import { api } from '../../api/client'
import { keys } from '../../api/queries'
import { useAppState } from '../../state/app'
import { Overlay } from './Overlay'
import { paths, processFromPath } from '../../lib/paths'

type Hit = {
  id: string
  label: string
  hint: string
  to: string
}

export function CommandPalette() {
  const { paletteOpen, setPaletteOpen } = useAppState()
  const [query, setQuery] = useState('')
  const [active, setActive] = useState(0)
  const navigate = useNavigate()
  const location = useLocation()
  const processId = processFromPath(location.pathname)

  const processes = useQuery({
    queryKey: keys.processes,
    queryFn: () => api.listProcesses(),
    enabled: paletteOpen,
  })
  const instances = useQuery({
    queryKey: keys.instances(processId ?? 0),
    queryFn: () => api.listInstances(processId!),
    enabled: paletteOpen && Boolean(processId),
  })

  const hits = useMemo(() => {
    const list: Hit[] = [
      { id: 'processes', label: 'Procesos', hint: 'todos', to: paths.processes },
      { id: 'new', label: 'Nuevo proceso', hint: 'crear o importar', to: paths.newProcess },
      { id: 'settings', label: 'Ajustes', hint: 'usuario y modelos', to: paths.settings },
      ...(processes.data ?? []).map((process) => ({
        id: `p-${process.id}`,
        label: process.nombre,
        hint: 'proceso',
        to: paths.process(process.id),
      })),
    ]
    if (processId) {
      list.push(
        { id: 'inst', label: 'Instancias', hint: 'consola', to: paths.instances(processId) },
        { id: 'queue', label: 'Cola', hint: 'esperando a una persona', to: paths.queue(processId) },
        { id: 'rules', label: 'Reglas', hint: 'la norma', to: paths.rules(processId) },
        { id: 'audit', label: 'Auditoría', hint: 'hallazgos', to: paths.audit(processId) },
        { id: 'sources', label: 'Fuentes', hint: 'ingesta', to: paths.sources(processId) },
      )
    }

    const q = query.trim().toLowerCase()
    if (!q) return list.slice(0, 12)

    // Instances only enter the list once you type: there are 500 of them.
    const documents = !processId
      ? []
      : (instances.data ?? [])
          .filter((item) => item.nombre.toLowerCase().includes(q))
          .slice(0, 8)
          .map((item) => ({
            id: `i-${item.id}`,
            label: item.nombre,
            hint: item.decision ?? item.estado,
            to: paths.instance(processId, item.id),
          }))

    return [
      ...list.filter(
        (hit) => hit.label.toLowerCase().includes(q) || hit.hint.toLowerCase().includes(q),
      ),
      ...documents,
    ]
  }, [query, processes.data, instances.data, processId])

  useEffect(() => {
    setActive(0)
  }, [query, paletteOpen])

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        setPaletteOpen(!paletteOpen)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [paletteOpen, setPaletteOpen])

  if (!paletteOpen) return null

  const go = (hit: Hit) => {
    setPaletteOpen(false)
    setQuery('')
    navigate(hit.to)
  }

  return (
    <Overlay onClose={() => setPaletteOpen(false)}>
      <div className="overflow-hidden rounded-[16px] bg-white shadow-[0_16px_50px_rgba(19,19,19,0.12)] ring-1 ring-black/[0.06]">
        <input
          autoFocus
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'ArrowDown') {
              event.preventDefault()
              setActive((index) => Math.min(index + 1, hits.length - 1))
            }
            if (event.key === 'ArrowUp') {
              event.preventDefault()
              setActive((index) => Math.max(index - 1, 0))
            }
            if (event.key === 'Enter' && hits[active]) go(hits[active])
          }}
          placeholder="Proceso, pantalla, archivo…"
          className="w-full border-b border-hairline bg-transparent px-4 py-3 text-[15px] outline-none placeholder:text-faint"
        />
        <ul className="max-h-80 overflow-y-auto py-1">
          {hits.length === 0 ? (
            <li className="px-4 py-3 text-[13px] text-muted">Nada con ese nombre.</li>
          ) : (
            hits.map((hit, index) => (
              <li key={hit.id}>
                <button
                  type="button"
                  onMouseEnter={() => setActive(index)}
                  onClick={() => go(hit)}
                  className={`flex w-full items-baseline justify-between px-4 py-2 text-left text-[14px] ${
                    index === active ? 'bg-canvas' : ''
                  }`}
                >
                  <span className="text-ink">{hit.label}</span>
                  <span className="font-mono text-[11px] text-faint">{hit.hint}</span>
                </button>
              </li>
            ))
          )}
        </ul>
      </div>
    </Overlay>
  )
}
