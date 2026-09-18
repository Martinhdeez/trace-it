import { useState } from 'react'
import { useNavigate } from 'react-router'
import { Topbar } from '../components/shell/Topbar'
import { NestedCard, PageIntro } from '../components/shell/Well'
import { t } from '../i18n'
import { paths, PROCESS } from '../lib/paths'

export function NuevoProceso() {
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')

  return (
    <>
      <Topbar crumbs={[{ label: t('nav.processes'), to: paths.home }, { label: t('nav.newProcess') }]} />
      <form
        className="min-h-0 flex-1 overflow-y-auto px-8 pb-10 pt-4"
        onSubmit={(event) => {
          event.preventDefault()
          navigate(paths.process(PROCESS.reconcilePayments))
        }}
      >
        <PageIntro
          kicker={t('newProcess.kicker')}
          title={t('newProcess.title')}
          description={t('newProcess.description')}
        />

        <div className="max-w-lg space-y-3">
          <NestedCard label="proceso">
            <div className="space-y-4 px-3.5 py-3">
              <label className="block text-[12px] font-medium text-ink">
                {t('newProcess.name')}
                <input
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  className="mt-1 w-full rounded-[10px] bg-canvas px-3 py-2 text-[13px] outline-none ring-1 ring-black/[0.06]"
                  placeholder={t('processes.reconcile-payments.name')}
                />
              </label>
              <label className="block text-[12px] font-medium text-ink">
                {t('newProcess.what')}
                <textarea
                  value={description}
                  onChange={(event) => setDescription(event.target.value)}
                  rows={3}
                  className="mt-1 w-full rounded-[10px] bg-canvas px-3 py-2 text-[13px] outline-none ring-1 ring-black/[0.06]"
                  placeholder={t('processes.reconcile-payments.description')}
                />
              </label>
            </div>
          </NestedCard>

          <NestedCard label={t('newProcess.sources')}>
            <div className="space-y-2 px-3.5 py-3">
              <Drop label="PDFs del lote" hint="500-sombras-de-alberto/facturas" />
              <Drop label="Excel de Alberto" hint="FINAL_v7_DEFINITIVO_ahorasi.xlsx" />
              <Drop label="Conector ERP" hint="http://127.0.0.1:8009" />
            </div>
          </NestedCard>

          <div className="flex gap-2 pt-2">
            <button
              type="submit"
              className="rounded-full bg-ink px-4 py-2 text-[13px] font-medium text-white"
            >
              {t('newProcess.create')}
            </button>
            <button
              type="button"
              onClick={() => navigate(-1)}
              className="rounded-full px-4 py-2 text-[13px] text-muted hover:text-ink"
            >
              {t('newProcess.cancel')}
            </button>
          </div>
        </div>
      </form>
    </>
  )
}

function Drop({ label, hint }: { label: string; hint: string }) {
  return (
    <div className="rounded-[12px] bg-well px-3 py-3 ring-1 ring-black/[0.04]">
      <p className="text-[13px] text-ink">{label}</p>
      <p className="text-[11px] text-muted">{hint}</p>
    </div>
  )
}
