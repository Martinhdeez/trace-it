import { useQuery } from '@tanstack/react-query'
import { useParams } from 'react-router'
import { api } from '../api/client'
import { keys } from '../api/queries'
import { ProcessExecutionSettings } from '../components/process/ExecutionSettings'
import { ProcessScreen } from '../components/process/ProcessScreen'
import { MailSettings } from '../components/process/MailSettings'
import { paths } from '../lib/paths'

export function ProcessSettings() {
  const processId = Number(useParams().processId)
  const process = useQuery({
    queryKey: keys.process(processId),
    queryFn: () => api.getProcess(processId),
  })

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
          <MailSettings processId={processId} />
          <ProcessExecutionSettings processId={processId} />
        </div>
      </div>
    </ProcessScreen>
  )
}
