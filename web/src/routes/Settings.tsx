import { Topbar } from '../components/shell/Topbar'
import { NestedCard, PageIntro } from '../components/shell/Well'
import { t } from '../i18n'

export function Settings() {
  return (
    <>
      <Topbar crumbs={[{ label: t('nav.settings') }]} />
      <div className="min-h-0 flex-1 overflow-y-auto px-8 pb-10 pt-4">
        <PageIntro
          kicker={t('settings.kicker')}
          title={t('settings.title')}
          description={t('settings.description')}
        />
        <div className="max-w-lg space-y-3">
          <NestedCard label={t('settings.runtime')}>
            <dl>
              <Row
                label={t('settings.language')}
                value={t('settings.languageValue')}
                hint={t('settings.languageHint')}
              />
              <Row label={t('settings.api')} value="mock · VITE_API_MODE" />
              <Row label={t('settings.erp')} value="http://127.0.0.1:8009" />
              <Row label={t('settings.cutoff')} value="18/09/2026" />
              <Row label={t('settings.vision')} value={t('settings.visionValue')} />
            </dl>
          </NestedCard>
          <p className="px-1 text-[12px] text-faint">
            La norma vive en cada proceso. Ábrela desde el proceso → {t('process.rules')}.
          </p>
        </div>
      </div>
    </>
  )
}

function Row({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="border-t border-hairline px-3.5 py-3 first:border-0">
      <div className="flex items-baseline justify-between gap-4 text-[13px]">
        <dt className="text-muted">{label}</dt>
        <dd className="font-mono text-ink">{value}</dd>
      </div>
      {hint ? <p className="mt-1 text-[12px] text-faint">{hint}</p> : null}
    </div>
  )
}
