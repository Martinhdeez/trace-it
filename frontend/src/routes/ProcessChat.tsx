import { Link, Navigate, useParams } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import { keys } from '../api/queries'
import { ProcessDraftChat } from '../components/process/ProcessDraftChat'
import { ProcessScreen } from '../components/process/ProcessScreen'
import { Button } from '../components/shell/Controls'
import { paths } from '../lib/paths'
import { useSession } from '../state/session'

/** The primary authoring screen. The manual definition editor remains available as a fallback. */
export function ProcessChat() {
  const processId = Number(useParams().processId)
  const { isManager } = useSession()
  const process = useQuery({
    queryKey: keys.process(processId),
    queryFn: () => api.getProcess(processId),
  })

  if (!isManager) return <Navigate to={paths.definition(processId)} replace />

  return (
    <ProcessScreen
      processId={processId}
      crumbs={[
        { label: 'Procesos', to: paths.processes },
        { label: process.data?.name ?? '…', to: paths.process(processId) },
        { label: 'Definición' },
      ]}
      actions={
        <Link to={paths.definition(processId)}>
          <Button tone="ghost">Editar a mano</Button>
        </Link>
      }
    >
      <ProcessDraftChat processId={processId} processName={process.data?.name} />
    </ProcessScreen>
  )
}
