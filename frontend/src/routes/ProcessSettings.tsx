import { useQuery } from '@tanstack/react-query'
import { useParams } from 'react-router'
import { api } from '../api/client'
import { keys } from '../api/queries'
import { ProcessExecutionSettings } from '../components/process/ExecutionSettings'
import { ProcessScreen } from '../components/process/ProcessScreen'
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
      <div className="min-h-0 flex-1 overflow-y-auto px-8 pb-10 pt-4">
        <header className="mb-6">
          <p className="text-[13px] text-muted">Ajustes del proceso</p>
          <h1 className="mt-1 text-[32px] font-medium leading-[1.1] tracking-[-0.045em]">
            Modelos y esfuerzo de ejecución
          </h1>
          <p className="mt-2 max-w-2xl text-[14.5px] leading-6 text-muted">
            Elige un perfil o ajusta OCR, modelos, reintentos y revisión. Los cambios se
            guardan en un borrador y se aplican al publicar.
          </p>
        </header>
        <div className="max-w-3xl">
          <ProcessExecutionSettings processId={processId} />
        </div>
      </div>
    </ProcessScreen>
  )
}
