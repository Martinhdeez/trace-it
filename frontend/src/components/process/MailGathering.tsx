import { useState } from 'react'
import { Link } from 'react-router'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { mailApi, type GatheringSettings } from '../../api/mail'
import { paths } from '../../lib/paths'
import { useSession } from '../../state/session'
import { Button, Field, Select } from '../shell/Controls'
import { ErrorNotice } from '../shell/Notice'
import { NestedCard } from '../shell/Well'

const labels: Record<string, string> = {
  uninitialized: 'Pendiente de inicializar', active: 'Preparado para recibir',
  halted: 'Detenido: requiere intervención', discovered: 'Detectado', importing: 'Importando',
  imported: 'Importado', evaluating: 'Evaluando', completed: 'Completado',
  partial: 'Resultado parcial', duplicate: 'Duplicado', ignored: 'Sin PDF',
  retry_wait: 'Pendiente de reintento', failed: 'Fallo técnico',
}

export function MailGathering({ processId }: { processId: number }) {
  const { isManager } = useSession()
  const settings = useQuery({
    queryKey: ['mail-gathering', processId], queryFn: () => mailApi.gathering(processId),
  })
  const overview = useQuery({
    queryKey: ['mail-overview', processId], queryFn: () => mailApi.overview(processId),
    refetchInterval: 15_000,
  })
  const account = overview.data?.account
  return <section className="mt-6" aria-label="Recepción de correo">
    <NestedCard label="Recepción de correo">
      <div className="space-y-4 p-4">
        <p className="text-sm text-muted">
          Los PDF recibidos en el buzón asignado se importan y evalúan en este proceso.
          Guardar esta asignación no activa la conexión al correo.
        </p>
        {settings.data && <GatheringForm key={settings.data.email ?? 'none'}
          processId={processId} initial={settings.data} disabled={!isManager} />}
        {(settings.error || overview.error) && <ErrorNotice error={settings.error ?? overview.error} />}
        <div className="border-t border-hairline pt-3 text-sm">
          <p>Integración: <strong>{account ? labels[account.state] ?? account.state : 'No instalada'}</strong></p>
          <p className="mt-1 text-muted">Última consulta correcta: {account?.last_poll_at
            ? new Date(account.last_poll_at).toLocaleString() : 'Todavía no se ha consultado el buzón'}</p>
          {account?.error && <p role="status" className="mt-2">Incidencia técnica: {account.error}</p>}
        </div>
        {!!overview.data?.messages.length && <div className="space-y-3">
          <h3 className="text-sm font-medium">Correos recientes</h3>
          {overview.data.messages.map(message => <article key={message.id}
            className="rounded-lg border border-hairline p-3 text-sm">
            <div className="flex flex-wrap justify-between gap-2">
              <strong className="break-all">{String(message.envelope?.subject || 'Sin asunto')}</strong>
              <span>{labels[message.state] ?? message.state}</span>
            </div>
            <p className="mt-1 break-all text-muted">{String(message.envelope?.sender || 'Remitente no disponible')}</p>
            <details className="mt-2 text-xs text-muted"><summary>Procedencia del correo</summary>
              <p className="mt-1 break-all">{account?.username} · {account?.folder} · UIDVALIDITY {message.uidvalidity} · UID {message.uid}</p>
              <p className="break-all">Message-ID: {String(message.envelope?.message_id || 'No disponible')}</p>
              <p>Recibido: {String(message.envelope?.internal_date || message.created_at)}</p>
            </details>
            {message.error && <p className="mt-2">Incidencia: {message.error}</p>}
            <ul className="mt-2 space-y-2">{message.attachments.map(part => <li key={part.id} className="border-t border-hairline pt-2">
              <p className="break-all">{part.original_name} <span className="text-muted">· {labels[part.state] ?? part.state}</span></p>
              {part.error && <p className="text-xs">Incidencia: {part.error === 'manual_pending_conflict'
                ? 'Coincide con un documento manual pendiente; requiere revisión.' : part.error}</p>}
              <div className="mt-1 flex flex-wrap gap-3 text-xs">
                {part.instance_id && <Link className="underline" to={paths.instance(processId, part.instance_id)}>Documento #{part.instance_id}</Link>}
                {part.execution_id && <Link className="underline" to={paths.instances(processId, part.execution_id)}>Ejecución #{part.execution_id}</Link>}
                {part.decision_id && part.instance_id && <Link className="underline" to={paths.instance(processId, part.instance_id)}>{part.decision ?? 'Decisión'} · #{part.decision_id}</Link>}
              </div>
            </li>)}</ul>
          </article>)}
        </div>}
      </div>
    </NestedCard>
  </section>
}

function GatheringForm({ processId, initial, disabled }: {
  processId: number; initial: GatheringSettings; disabled: boolean
}) {
  const client = useQueryClient()
  const [email, setEmail] = useState(initial.email ?? '')
  const save = useMutation({
    mutationFn: () => mailApi.saveGathering(processId, { email: email ? 'migration-test@j-aautomation.com' : null }),
    onSuccess: () => { void client.invalidateQueries({ queryKey: ['mail-gathering', processId] }) },
  })
  return <form className="space-y-3" onSubmit={event => { event.preventDefault(); save.mutate() }}>
    <Field label="Correo de recepción (gathering)">
      <Select aria-label="Correo de recepción (gathering)" value={email}
        disabled={disabled || save.isPending} onChange={event => setEmail(event.target.value)}>
        <option value="">Sin correo asignado</option>
        <option value="migration-test@j-aautomation.com">migration-test@j-aautomation.com</option>
      </Select>
    </Field>
    {!disabled && <Button type="submit" disabled={save.isPending}>Guardar correo</Button>}
    {save.isError && <ErrorNotice error={save.error} />}
    {save.isSuccess && <p role="status" className="text-sm">Correo guardado. La activación del buzón se realiza por separado.</p>}
  </form>
}
