import { useState } from 'react'
import { Link } from 'react-router'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { mailApi, type GatheringSettings } from '../../api/mail'
import { paths } from '../../lib/paths'
import { useSession } from '../../state/session'
import { Button, Field, Select } from '../shell/Controls'
import { ErrorNotice } from '../shell/Notice'
import { NestedCard } from '../shell/Well'
import { MailConnection } from './MailStatus'
import { mailKeys } from '../../api/mail'

export function MailGathering({ processId }: { processId: number }) {
  const { isManager } = useSession()
  const settings = useQuery({
    queryKey: ['mail-gathering', processId], queryFn: () => mailApi.gathering(processId),
  })
  const overview = useQuery({
    queryKey: mailKeys.overview(processId), queryFn: () => mailApi.overview(processId),
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
        <div className="border-t border-hairline pt-3"><MailConnection account={account} /></div>
        <Link className="inline-block text-sm underline" to={paths.reception(processId)}>Ver correos, adjuntos y resultados en Recepción</Link>
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
