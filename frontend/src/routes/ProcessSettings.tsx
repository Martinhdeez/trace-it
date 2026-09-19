import { useQuery } from '@tanstack/react-query'
import { useParams, useSearchParams } from 'react-router'
import { api } from '../api/client'
import { keys } from '../api/queries'
import { ProcessExecutionSettings } from '../components/process/ExecutionSettings'
import { ProcessScreen } from '../components/process/ProcessScreen'
import { MailSettings } from '../components/process/MailSettings'
import { Segmented } from '../components/shell/Controls'
import { Empty } from '../components/shell/Notice'
import { SettingsSection } from '../components/shell/SettingsSection'
import { paths } from '../lib/paths'
import { useSession } from '../state/session'

const TABS = ['correo', 'modelos'] as const
type Tab = (typeof TABS)[number]

export function ProcessSettings() {
  const processId = Number(useParams().processId)
  const { isManager } = useSession()
  const process = useQuery({
    queryKey: keys.process(processId),
    queryFn: () => api.getProcess(processId),
  })
  const [params, setParams] = useSearchParams()
  const requested = params.get('tab') as Tab | null
  const tab: Tab = requested && TABS.includes(requested) ? requested : 'correo'

  return (
    <ProcessScreen
      processId={processId}
      crumbs={[
        { label: 'Procesos', to: paths.processes },
        { label: process.data?.name ?? '…', to: paths.process(processId) },
        { label: 'Ajustes' },
      ]}
    >
      <div className="min-h-0 flex-1 overflow-y-auto px-6 pb-10 pt-4">
        <div className="max-w-3xl">
          <Segmented<Tab>
            value={tab}
            onChange={(next) => setParams(next === 'correo' ? {} : { tab: next }, { replace: true })}
            options={[
              { value: 'correo', label: 'Correo' },
              { value: 'modelos', label: 'Modelos' },
            ]}
          />
          <div className="mt-2 divide-y divide-rule">
            {tab === 'correo' ? (
              <SettingsSection
                title="Correo"
                description="El buzón que alimenta el proceso y los últimos correos con el destino de cada PDF."
              >
                <MailSettings processId={processId} />
              </SettingsSection>
            ) : null}
            {tab === 'modelos' ? (
              <SettingsSection
                title="Modelos y ejecución"
                description="Presets y esfuerzo de los agentes. Los cambios se aplican al publicar."
              >
                {isManager ? (
                  <ProcessExecutionSettings processId={processId} />
                ) : (
                  <Empty>Solo los managers pueden tocar los modelos.</Empty>
                )}
              </SettingsSection>
            ) : null}
          </div>
        </div>
      </div>
    </ProcessScreen>
  )
}
