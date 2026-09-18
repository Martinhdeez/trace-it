import { useLocation } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import { api } from '../../api/client'
import { processVersionDiffs, rulesFor } from '../../data/versions'
import { useAppState } from '../../state/app'
import { Overlay } from './Overlay'
import { cn } from '../../lib/cn'
import { t } from '../../i18n'
import { processIdFromPath } from '../../lib/paths'
import { PROCESS } from '../../lib/paths'

export function VersionPanel() {
  const location = useLocation()
  const processId = processIdFromPath(location.pathname) ?? PROCESS.reconcilePayments
  const { versionFor, setVersion, versionsOpen, setVersionsOpen } = useAppState()
  const versionId = versionFor(processId)
  const versions = rulesFor(processId)
  const instances = useQuery({
    queryKey: ['instances-latest', processId],
    queryFn: async () => {
      const runs = await api.listRuns(processId)
      if (!runs[0]) return []
      return api.listInstances(runs[0].id)
    },
    enabled: versionsOpen,
  })

  if (!versionsOpen) return null

  return (
    <Overlay align="right" onClose={() => setVersionsOpen(false)}>
      <aside className="flex h-full flex-col overflow-hidden rounded-[20px] bg-white shadow-[0_16px_50px_rgba(19,19,19,0.12)] ring-1 ring-black/[0.06]">
        <header className="flex items-center justify-between px-5 py-4">
          <div>
            <p className="text-[13px] text-muted">{t('rules.kicker')}</p>
            <h2 className="text-[20px] font-medium tracking-[-0.03em]">{t('rules.title')}</h2>
          </div>
          <button
            type="button"
            onClick={() => setVersionsOpen(false)}
            className="rounded-full px-2.5 py-1 text-[13px] text-muted hover:bg-canvas hover:text-ink"
          >
            {t('rules.close')}
          </button>
        </header>

        <div className="min-h-0 flex-1 overflow-y-auto px-4 pb-5">
          <ol className="flex flex-col gap-3">
            {versions.map((version) => {
              const selected = version.id === versionId
              const diffs = processVersionDiffs[processId]?.[version.id] ?? []
              return (
                <li key={version.id}>
                  <button
                    type="button"
                    onClick={() => setVersion(processId, version.id)}
                    className={cn(
                      'w-full rounded-[16px] px-4 py-3 text-left ring-1',
                      selected
                        ? 'bg-well ring-black/[0.06]'
                        : 'bg-white ring-black/[0.06] hover:bg-canvas',
                    )}
                  >
                    <span className="flex items-baseline justify-between">
                      <span className="text-[15px] font-medium">{version.label}</span>
                      <span className="font-mono text-[11px] text-muted">
                        {version.status === 'activa' ? t('rules.active') : t('rules.draft')}
                      </span>
                    </span>
                    <span className="mt-1 block text-[12px] text-muted">{version.notes}</span>
                    <span className="mt-1 block font-mono text-[11px] text-faint">{version.date}</span>
                  </button>
                  {selected ? (
                    <ul className="mt-3 space-y-1.5 px-2">
                      {version.clauses.map((clause) => (
                        <li key={clause} className="text-[13px] text-muted">
                          {clause}
                        </li>
                      ))}
                    </ul>
                  ) : null}
                  {selected && diffs.length > 0 ? (
                    <div className="mt-4 overflow-hidden rounded-[16px] ring-1 ring-black/[0.06]">
                      <div className="flex items-center justify-between px-3 py-1.5">
                        <span className="font-mono text-[11px] text-faint">
                          {t('rules.impact')}
                        </span>
                        <span className="text-[11px] text-muted">
                          {diffs.length} {t('rules.decisions')}
                        </span>
                      </div>
                      <ul className="bg-well px-3 py-2">
                        {diffs.map((diff) => (
                          <li
                            key={diff.instanceId}
                            className="flex items-baseline justify-between gap-3 py-1 font-mono text-[12px]"
                          >
                            <span>{diff.fileId}</span>
                            <span className="text-muted">
                              {diff.from} → {diff.to}
                            </span>
                          </li>
                        ))}
                      </ul>
                      <p className="px-3 py-2 text-[12px] text-faint">
                        {instances.data
                          ? `Sobre ${instances.data.length} instancias del lote visible.`
                          : null}
                      </p>
                    </div>
                  ) : null}
                </li>
              )
            })}
          </ol>
        </div>
      </aside>
    </Overlay>
  )
}
