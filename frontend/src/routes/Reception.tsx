import { useParams } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import { keys } from '../api/queries'
import { paths } from '../lib/paths'
import { ProcessScreen } from '../components/process/ProcessScreen'
import { MailReception } from '../components/process/MailReception'

export function Reception() {
  const processId = Number(useParams().processId)
  const process = useQuery({ queryKey: keys.process(processId), queryFn: () => api.getProcess(processId) })
  return <ProcessScreen processId={processId} crumbs={[{ label: 'Procesos', to: paths.processes }, { label: process.data?.name ?? '…', to: paths.process(processId) }, { label: 'Recepción' }]}>
    <div className="min-h-0 flex-1 overflow-y-auto px-4 py-6 sm:px-8"><div className="mx-auto max-w-5xl">
      <header className="mb-6"><h1 className="text-3xl font-medium tracking-tight">Recepción</h1><p className="mt-2 text-sm text-muted">Sigue cada correo desde sus adjuntos hasta la decisión.</p></header>
      <MailReception key={processId} processId={processId} />
    </div></div>
  </ProcessScreen>
}
