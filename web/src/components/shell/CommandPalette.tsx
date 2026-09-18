import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import { api } from '../../api/client'
import { useAppState } from '../../state/app'
import { Overlay } from './Overlay'
import { t } from '../../i18n'
import { paths } from '../../lib/paths'

type Hit = {
  id: string
  label: string
  hint: string
  to?: string
}

export function CommandPalette() {
  const { paletteOpen, setPaletteOpen } = useAppState()
  const [query, setQuery] = useState('')
  const [active, setActive] = useState(0)
  const navigate = useNavigate()

  const processes = useQuery({ queryKey: ['processes'], queryFn: () => api.listProcesses() })
  const runs = useQuery({ queryKey: ['runs-all'], queryFn: () => api.listAllRuns() })

  const hits = useMemo(() => {
    const list: Hit[] = [
      { id: 'review', label: t('nav.review'), hint: t('review.title'), to: paths.review },
      { id: 'runs', label: t('nav.runs'), hint: t('process.history'), to: paths.runs },
      { id: 'nuevo', label: t('nav.newProcess'), hint: t('newProcess.sources'), to: paths.processNew },
      { id: 'settings', label: t('nav.settings'), hint: t('settings.runtime'), to: paths.settings },
      ...(processes.data ?? []).map((item) => ({
        id: item.id,
        label: item.name,
        hint: t('palette.process'),
        to: paths.process(item.id),
      })),
      ...(runs.data ?? []).map((item) => ({
        id: item.id,
        label: item.label,
        hint: `${t('palette.run')} · ${item.normaVersion}`,
        to: paths.run(item.processId, item.id),
      })),
    ]
    const q = query.trim().toLowerCase()
    if (!q) return list.slice(0, 12)
    return list.filter(
      (hit) =>
        hit.label.toLowerCase().includes(q) || hit.hint.toLowerCase().includes(q),
    )
  }, [query, processes.data, runs.data])

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
    if (hit.to) navigate(hit.to)
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
          placeholder={t('palette.placeholder')}
          className="w-full border-b border-hairline bg-transparent px-4 py-3 text-[15px] outline-none placeholder:text-faint"
        />
        <ul className="max-h-80 overflow-y-auto py-1">
          {hits.length === 0 ? (
            <li className="px-4 py-3 text-[13px] text-muted">{t('palette.empty')}</li>
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
