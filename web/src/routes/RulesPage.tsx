import { Link, useParams } from 'react-router'
import { Topbar } from '../components/shell/Topbar'
import { NestedCard, PageIntro } from '../components/shell/Well'
import { rulesFor } from '../data/versions'
import { t } from '../i18n'
import { paths } from '../lib/paths'
import { useAppState } from '../state/app'
import { cn } from '../lib/cn'

export function RulesPage() {
  const { processId = '' } = useParams()
  const { versionFor, setVersion } = useAppState()
  const versions = rulesFor(processId)
  const active = versionFor(processId)
  const copy = {
    name: t(`processes.${processId}.name`),
  }

  return (
    <>
      <Topbar
        crumbs={[
          { label: t('nav.processes'), to: paths.home },
          { label: copy.name, to: paths.process(processId) },
          { label: t('rules.title') },
        ]}
      />
      <div className="min-h-0 flex-1 overflow-y-auto px-8 pb-10 pt-4">
        <PageIntro kicker={t('rules.kicker')} title={t('rules.title')} description={copy.name} />
        <div className="max-w-xl space-y-3">
          {versions.map((version) => {
            const selected = version.id === active
            return (
              <NestedCard
                key={version.id}
                label={version.id}
                action={
                  <span className="font-mono text-[11px] text-muted">
                    {version.status === 'activa' ? t('rules.active') : t('rules.draft')}
                  </span>
                }
              >
                <button
                  type="button"
                  onClick={() => setVersion(processId, version.id)}
                  className={cn('w-full px-3.5 py-3 text-left', selected && 'bg-well')}
                >
                  <p className="text-[16px] font-medium">{version.label}</p>
                  <p className="mt-1 text-[13px] text-muted">{version.notes}</p>
                  <ul className="mt-3 space-y-1.5">
                    {version.clauses.map((clause) => (
                      <li key={clause} className="text-[13px] text-muted">
                        {clause}
                      </li>
                    ))}
                  </ul>
                </button>
              </NestedCard>
            )
          })}
          <Link to={paths.process(processId)} className="inline-block text-[13px] text-muted hover:text-ink">
            ← {copy.name}
          </Link>
        </div>
      </div>
    </>
  )
}
